import os
from dotenv import load_dotenv
import requests
import asyncio
import mysql.connector as mysql

#from baml_client.sync_client import b
from baml_client.async_client import b # using async, there is option for both
from baml_client.types import ClassifiedQuestion
from fastapi import FastAPI, WebSocket, Request, Response
from twilio.twiml.voice_response import VoiceResponse, Connect, ConversationRelay

load_dotenv()

web_app = FastAPI(title="Admissions Agent")
callSid = ""
caller_phone = ""
stream_sid = "" # not sure if needed now

async_lock = asyncio.Lock() # to ensure only one LLM response at a time, can be removed if we want to allow multiple simultaneous conversations (but would need to ensure LLM can handle that)

def retrieve_context_from_db(baml_parsed: ClassifiedQuestion) -> str:
    
    # initialize DB connection , should maybe be done once at start as an init function. Could be optimized
    conn = mysql.connect(
        host="localhost",
        user="root", #Make sure to replace this with your actual username or use environment variables for security
        password="Xtermin8", #Make sure to replace this with your actual password or use environment variables for security
        database="capstonedb2" #Name of the database after the sql file is run
    )
    cursor = conn.cursor()

    parsed_dict = baml_parsed.category.model_dump()
    # print("Pydantic Object:", parsed_dict)
    # print("parsing option 1 (get Group by itself): ", list(parsed_dict.keys())[0])
    # print("parsing option 2 (gets total from serialized PyDantic): ", list(parsed_dict.values())[0])
    groupName = list(parsed_dict.keys())[0]
    subgroup = list(parsed_dict.values())[0].split('.')[-1]
    
    if subgroup == "SAT" or subgroup == "ACT": # FIX THIS, temporary for now
        subgroup = "SAT/ACT"
    key = groupName + "_" + subgroup

    cursor.execute("SELECT Information_Text FROM informationdatabase WHERE Category_Key = %s;", (key,))

    Information = []

    for results in cursor:
        Information.append(results[0])

    cursor.close()
    conn.close()

    fullContext = "\n".join(Information) 
    return fullContext   

async def process_question(question: str) -> str:
    parsed = await b.ParseQuery(question)
    context = retrieve_context_from_db(parsed) # need to make async later, it is blocking other all other requests (if we simulate multi user)
    answer = await b.AnswerQuery(question, context)
    return answer

@web_app.get("/")
async def root():
    return {"status": "ok", "service": "Admissions Agent Northeastern"}

@web_app.post("/webhook")
async def twillio_webhook(request: Request):
     
    form_data = await request.form()
    callSid = str(form_data["CallSid"])
    caller_number= str(form_data["From"])

    response = VoiceResponse()
    response.say("Welcome to the Northeastern University AI Admission Chat Service.")

    connect = Connect()
    base_url = "<URL HERE>"
    websocket_url = f"{base_url}/ws/{caller_number}"

    conversation_relay = ConversationRelay(url = websocket_url) 
    connect.append(conversation_relay)
    response.append(connect)

    return Response(content=str(response), media_type="application/xml")

@web_app.websocket("/ws/{caller_number}")
async def websocket_endpoint(websocket: WebSocket, caller_number: str):

    await websocket.accept()
    print(f"WebSocket connected for call: {caller_number}")

    # wait for start condition 
    while True:
        msg = await websocket.receive_json()
        if msg.get("event") != "start":
            await asyncio.sleep(0.01)
            continue
        stream_sid = msg["streamSid"]
        break

    utterance_buffer = ""  # Declare outside loop

    while True:
        msg = await websocket.receive_json()
        
        if msg.get("type") == "prompt":
            text = msg.get("voicePrompt", "")   # or msg.get("text", "")  # Check Twilio's actual field name
            is_prompt_end = msg.get("last", False) # or msg.get("promptEnd", False)

            if not is_prompt_end:
                utterance_buffer = text  # Store partial (Twilio sends cumulative text)
                continue 

            final_question = utterance_buffer  # Or utterance_buffer if Twilio sends incrementally
            utterance_buffer = ""  # Reset for next utterance

            async with async_lock:
                # Here you would send final_question to your LLM, get a response, and then send that response back to the caller using Twilio's API.
                print(f"Received complete question: {final_question} from call: {caller_number}")
                answer = await process_question(final_question)

                print(f"Sent answer: {answer} to call: {caller_number}")
                await websocket.send_json({"event": "answer", "text": answer})
               
        
        if msg.get("event") == "stop":
            print(f"WebSocket stream stopped for call: {caller_number}")
            break



