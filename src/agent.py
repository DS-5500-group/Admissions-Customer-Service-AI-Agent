import os
from dotenv import load_dotenv
import requests
import asyncio
import pandas as pd

from baml_client.sync_client import b
# from baml_client.async_client import b # using async, there is option for both
from baml_client.types import ClassifiedQuestion
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response
from twilio.twiml.voice_response import VoiceResponse, Connect, ConversationRelay

load_dotenv()

web_app = FastAPI(title="Admissions Agent")
callSid = ""
caller_phone = ""
stream_sid = "" # probably not needed now

# async_lock = asyncio.Lock() #  supposedly to ensure only one LLM response at a time (see below), not sure if need
db = pd.read_csv("DB Full Collection.csv")

def query_university_context(question: str) -> str:
    

    #### OLD: USED structure where GROUP and SUBGROUP were forced to have 
    #         correct pair from BAML class/enum instead of enforced in prompt

    # baml_parsed = b.ParseQuery(question)
    # parsed_dict = baml_parsed.category.model_dump()
    # print("Pydantic Object:", parsed_dict)
    # print("parsing option 1 (get Group by itself): ", list(parsed_dict.keys())[0])
    # print("parsing option 2 (gets total from serialized PyDantic): ", list(parsed_dict.values())[0])
    # groupName = list(parsed_dict.keys())[0]
    # subgroup = list(parsed_dict.values())[0].split('.')[-1]

    parsed = b.ParseQuery(question) # sync version for now (check import at top)

    predicted_key = parsed.group + "_" + parsed.subgroup
    try:
        context = db.loc[db["Lookup_Key"]==predicted_key, "Information Text"].item() # .item() should return the single entry, "scalor" value
        return context, predicted_key
    except ValueError: # 0 or multiple matches for when Lookup_Key==predicted_key, .item() only allows for single row
        return "", predicted_key
    
# maybe need to make async later, it may blocking all other requests (if we simulate multi user)
def process_question(question: str, language: str) -> str:
    
    context, predicted_key = query_university_context(question) # prob would also need to make async
    print(f"The asked question was: {question}")
    print(f"The Predicted Key was: {predicted_key}")
    if context == "":
        return "Unable to process question since I am unable to retrieve context"
    answer = b.AnswerQuery(question, context, language=language)
    return answer

async def interruptible_process(question,l, websocket): 
    answer =  await asyncio.to_thread(process_question, question, l)
    print(f"LLM answer w/ context: {answer}")
    await websocket.send_json({"type": "text", "token": answer, "last": True}) 

@web_app.get("/")
async def root():
    return {"status": "ok", "service": "Admissions Agent Northeastern"}

@web_app.post("/webhook")
async def twillio_webhook(request: Request):
     
    form_data = await request.form()
    #callSid = str(form_data["CallSid"])  #not needed for now
    caller_number= str(form_data["From"]).lstrip("+") # get rid of + char in front of phone numbers 

    response = VoiceResponse()
    response.say("Welcome to the Northeastern University AI Admission Chat Service.")

    connect = Connect()
    base_url = "https://uncriticisably-quavery-louvenia.ngrok-free.dev"
    base_url = base_url.replace('https://', 'wss://')
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
    # while True:
    #     msg = await websocket.receive_json()
    #     if msg.get("event") != "start":     # (MEDIA-STREAM TWILIO MODE), also this loop is more robust than below
    #         await asyncio.sleep(0.01)
    #         continue
    #     stream_sid = msg["streamSid"]
    #     break

    msg = await websocket.receive_json()
    if msg.get("type") == "setup":
        print(f"ConversationRelay connected, call from {msg.get('from')}")
        await websocket.send_json({"type": "text", "token": "What language do you prefer? Please respond in either English, Spanish, or Mandarin.", "last": True})
    try:
        while True: 
            #Language Set Up for AI Agent
            msg = await websocket.receive_json()
            if msg.get('type') == 'prompt':
                if msg.get('last', False):
                    language_code_mapping = {
                        "English": "en-US",
                        "Mandarin": "zh-CN"}
                    userResponse = msg.get('voicePrompt', 'English')
                    language = b.LanguageDetection(userResponse)
                    language_code = language_code_mapping.get(language, "en-US")
                    await websocket.send_json({"type": "config", "transcriptionLanguage": language_code, "ttsLanguage": language_code}) 
                    print(f"Language set to {language} based on user response: {userResponse}")
                    break
        current = None
        while True: # main call loop
            msg = await websocket.receive_json()
            
            if msg.get("type") == "prompt":

                if not msg.get("last", False): # last: True when have full user message
                    continue  # ignore partials

                if current:
                    current.cancel()
                    await websocket.send_json({"type": "clear"})
                
                #### SHOULDN"T NEED TO BUILD UP PARTIAL, CONVERSATION RELAY IS CUMULATIVE
                # text = msg.get("voicePrompt", "")   
                # is_prompt_end = msg.get("last", False) 

                # if not is_prompt_end:
                #     utterance_buffer = text  # Store partial (Twilio sends cumulative text)
                #     continue 

                # final_question = utterance_buffer  # Or utterance_buffer if Twilio sends incrementally
                # utterance_buffer = ""  # Reset for next utterance

                final_question = msg.get("voicePrompt", "")
                print(f"The 'final question' buffered is {final_question}. (Before passing to parse function")

                parsedInfo = b.ParseQuery(final_question)
                print(f"Parsed info from BAML: Group - {parsedInfo.group}")
                if parsedInfo.group == "End_Call":
                    print(f"End_Call intention has been found, ending call for {caller_number})")
                    goodbye_message = b.AnswerQuery("Say goodbye and end the call", "", language=language)
                    await websocket.send_json({"type": "text", "token": goodbye_message, "last": True})
                    await asyncio.sleep(7)
                    await websocket.send_json({"type": "end"})
                    break
                current = asyncio.create_task(interruptible_process(final_question, language, websocket))
                
                #### POTENTIALLY async version of code: KEY: note sure if an async.Lock() is really necessary here

                # async with async_lock:
                #     print(f"Received complete question: {final_question} from call: {caller_number}")
                #     answer = await process_question(final_question)

                #     print(f"Sent answer: {answer} to call: {caller_number}")
                #     await websocket.send_json({"event": "answer", "text": answer})

    except WebSocketDisconnect:
        print("Caller hung up — WebSocket closed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("agent:web_app", host="0.0.0.0", port=8000, reload=True)



               



