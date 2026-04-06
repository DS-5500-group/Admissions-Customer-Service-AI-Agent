import os
from dotenv import load_dotenv
import requests
import asyncio
from dataclasses import dataclass, field


import pandas as pd
import resend
# from baml_client.sync_client import b
from baml_client.async_client import b 
from baml_client.types import ClassifiedQuestion
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response
from twilio.twiml.voice_response import VoiceResponse, Connect, ConversationRelay, Dial
from twilio.rest import Client as TwilioClient

load_dotenv() # only for local 

resend.api_key = os.getenv("RESEND_API_KEY")
#print(f"Resend API: Key is: {resend.api_key}.")

web_app = FastAPI(title="Admissions Agent")
# callSid = ""
# caller_phone = ""
# stream_sid = "" # probably not needed now

@dataclass
class CallState:
    transcript: list = field(default_factory=list)
    ending_state: bool = False
    language: str = "English"
    email : str = ""
    caller_number: str = ""
    call_sid: str = ""

# async_lock = asyncio.Lock() #  supposedly to ensure only one LLM response at a time (see below), not sure if need
db = pd.read_csv("DB_Full_Collection.csv")
language_code_mapping = {
    "English": "en-US",
    "Spanish": "es-ES",
    "Chinese": "zh"
}

language_greeting = {
    "English": "What question can I help you with?",
    "Spanish": "¿Qué pregunta puedo ayudarte con?",
    "Chinese": "有什么问题我可以帮助你吗?",
}

language_email_prompt = {
    "English": "Would you like to receive an email transcript of this conversation at the end of the call? Please respond with 'yes' if you would like to receive an email.",
    "Spanish": "¿Desea recibir una transcripción por correo electrónico de esta conversación al final de la llamada? Por favor responda con 'yes' si desea recibir un correo electrónico.",
    "Chinese": "您想在通话结束时收到这次对话的电子邮件记录吗？请回答“yes”，如果您想收到电子邮件。"
}

language_email_confirmation_prompt = {
    "English": "Great! What is your email address?",
    "Spanish": "¡Genial! ¿Cuál es tu dirección de correo electrónico?",
    "Chinese": "太好了！你的电子邮箱地址是什么？"
}

agent_line = {
    "English": "I will transfer you to a human agent. Please stay on the line.",
    "Spanish": "Te transferiré a un agente humano. Por favor, mantente en la línea.",
    "Chinese": "我将把你转接给人工客服。请保持通话。"
}

def query_university_context(parsed: ClassifiedQuestion) -> str:
    

    #### OLD: USED structure where GROUP and SUBGROUP were forced to have 
    #         correct pair from BAML class/enum instead of enforced in prompt

    # baml_parsed = b.ParseQuery(question)
    # parsed_dict = baml_parsed.category.model_dump()
    # print("Pydantic Object:", parsed_dict)
    # print("parsing option 1 (get Group by itself): ", list(parsed_dict.keys())[0])
    # print("parsing option 2 (gets total from serialized PyDantic): ", list(parsed_dict.values())[0])
    # groupName = list(parsed_dict.keys())[0]
    # subgroup = list(parsed_dict.values())[0].split('.')[-1]

    predicted_key = parsed.group + "_" + parsed.subgroup
    try:
        context = db.loc[db["Lookup_Key"]==predicted_key, "Information Text"].item() # .item() should return the single entry, "scalor" value
        return context, predicted_key
    except ValueError: # 0 or multiple matches for when Lookup_Key==predicted_key, .item() only allows for single row
        return "", predicted_key

async def transfer_to_human(user_input: str, call: CallState, websocket: WebSocket):
    print(f"Transfer_To_Human intention has been found!")
    await websocket.send_json({"type": "text", "token": agent_line.get(call.language, agent_line["English"]), "last": True})
    await asyncio.sleep(3)
    twilio_client = TwilioClient(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
    instructions = f'<Response><Dial>{os.getenv("FORWARDING_PHONE_NUMBER")}</Dial></Response>'
    twilio_client.calls(call.call_sid).update(twiml=instructions) #Command to transfer call to the provided phone number
    call.ending_state = True


async def end_call(user_input: str , call: CallState, websocket: WebSocket):
    print(f"End_Call intention has been found.")
    # Maybe better to actually include transcript to have a more personalized end message?
    # Maybe better to have specialized end call BAML function. 
    goodbye_message = await b.AnswerQuery(question="Say a goodbye message to end the call", context="", transcript=call.transcript, language=call.language)

    await websocket.send_json({"type": "text", "token": goodbye_message, "last": True})
    call.transcript.append({"speaker": "User", "text":user_input})
    call.transcript.append({"speaker": "Agent", "text":goodbye_message})
    await asyncio.sleep(2)
    await websocket.send_json({"type": "end"})
    call.ending_state = True

async def end_call_set_condition(user_input: str, call: CallState, websocket: WebSocket):
    print("\nEnd_Call intention has been found (SET CONDITION VERSION).")
    call.ending_state = True
    call.transcript.append({"speaker": "User", "text":user_input})
    email = call.email
    if not call.email: #If email is not already set, the program will ask one last time before ending the call.
        await websocket.send_json({"type": "language", "transcriptionLanguage": "en-US", "ttsLanguage": language_code_mapping[call.language]})
        await websocket.send_json({"type": "text", "token": language_email_prompt.get(call.language, language_email_prompt["English"]), "last": True})
        while True:
            msg = await websocket.receive_json()
            if msg.get('type') != 'prompt':
                continue
            if not msg.get('last', False):
                continue
            responseObtained = msg.get("voicePrompt", "")
            if "yes" in responseObtained.lower():
                await websocket.send_json({"type": "text", "token": language_email_confirmation_prompt.get(call.language, language_email_confirmation_prompt["English"]), "last": True})
                while True:
                    emailAddress = await websocket.receive_json()
                    if emailAddress.get('type') != 'prompt':
                        continue
                    if not emailAddress.get('last', False):
                        continue
                    parsed_email = (await b.EmailRetrieval(emailAddress.get("voicePrompt", ""))).lower()
                    if parsed_email == "unable to parse email":
                        await websocket.send_json({"type": "text", "token": "Sorry, I couldn't get the email address. Please try again.", "last": True})
                        continue
                    call.email = parsed_email
                    email = parsed_email
                    break
                await websocket.send_json({"type": "language", "transcriptionLanguage": language_code_mapping[call.language], "ttsLanguage": language_code_mapping[call.language]})

            else:
                await websocket.send_json({"type": "text", "token": "No problem! Email will not be set", "last": True})
            break

    if email: #Notification of email being sent.

        try:
            await email_transcript(call, call.language, websocket)
            await websocket.send_json({"type": "text", "token": "Email has been sent!", "last": True})
        except Exception as e:
            print(f"Email send error: {type(e).__name__}: {e}")
            await websocket.send_json({"type": "text", "token": "Sorry, there was an error sending the email.", "last": True})

    goodbye_message = await b.AnswerQuery("Say goodbye and end the call.", "", "", language=call.language)
    await websocket.send_json({"type": "text", "token": goodbye_message, "last": True})
    await asyncio.sleep(10)
    await websocket.send_json({"type": "end"})

async def email_transcript(call: CallState, language: str, websocket: WebSocket):
    if call.transcript is None or len(call.transcript) == 0:
        print("No conversation history to email.")
        return
    else:
        print(f"Emailing conversation for caller: {call.email}")
        # document = ""
        # for entry in conversation_history:
        #     document += f" - {entry}\n"
        transcript_str = "\n".join(f"{entry['speaker']}: {entry['text']}" for entry in call.transcript)
        email_content = f"Conversation history for caller {call.email} (Language: {language}):\n\n{transcript_str}"
        
        await asyncio.to_thread(resend.Emails.send,{
            "from": "onboarding@resend.dev",
            "to": [call.email],
            "subject": f"Conversation Transcript for Caller {call.email}",
            "text": email_content
        })

async def process_input_states(user_input: str, call: CallState, websocket: WebSocket):
    
    try:
        # Build redable string transcript from list of dicts
        if len(call.transcript) > 5:
            recent_transcript = call.transcript[-5:]
            transcript_str = "\n".join(f"{entry['speaker']}: {entry['text']}" for entry in recent_transcript)

        else: 
            transcript_str = "\n".join(f"{entry['speaker']}: {entry['text']}" for entry in call.transcript)
        
        # START state, will decide next action/state
        parsed = await b.ClassifyInput(user_input, transcript_str) #can't just pass transcript 
        
        if parsed.overall_classification == "Out_Of_Scope":
            print("\nOUT OF SCOPE INPUT DETECTED")
            out_scope_msg = "Sorry, I can only respond to Northeastern University related inquiries, ask something else."
            await websocket.send_json({"type": "text", "token": out_scope_msg, "last": True})
            call.transcript.append({"speaker": "User", "text":user_input})
            call.transcript.append({"speaker": "Agent", "text":out_scope_msg})
        
        elif parsed.overall_classification == "Transfer_To_Human":
            await transfer_to_human(user_input, call, websocket)
        
        elif parsed.overall_classification == "End_Call":  
            #### Want to change back later: ask email and store it at some other part of the program, maybe begining or maybe anytime.         
            #await end_call(user_input, call, websocket) 
            await end_call_set_condition(user_input, call, websocket) 
        elif parsed.confidence <= 0.5 or parsed.group == "UnAnswerable": # agent initiates clarification
            
            await websocket.send_json({"type": "text", "token": parsed.clarification, "last": True})
            call.transcript.append({"speaker": "User", "text":user_input})
            call.transcript.append({"speaker": "Agent", "text":parsed.clarification})

        else: # Normal reply STATE

            context, predicted_key = query_university_context(parsed) # happens fast, dont worry about async
            print(f"The asked question was: {user_input}")
            print(f"The Predicted Key was: {predicted_key}")
            if context == "":
                # should never happen, understand how this happens. 
                answer =  "Unable to process question since I failed to retrieve context. Please clarify or ask a different question" 
            else:
                answer = await b.AnswerQuery(user_input, context, transcript_str, language=call.language)
            
            await websocket.send_json({"type": "text", "token": answer, "last": True})
            call.transcript.append({"speaker": "User", "text":user_input})
            call.transcript.append({"speaker": "Agent", "text":answer})
    
    except asyncio.CancelledError:
        print("Either interrupt or somehow second task created")
        raise # raise caught when "await task" after doing "task.cancel()"" 

# async def interruptible_process(question,l, websocket): 
#     answer =  await asyncio.to_thread(process_question, question, l)
#     print(f"LLM answer w/ context: {answer}")
#     await websocket.send_json({"type": "text", "token": answer, "last": True}) 

async def cancel_task_if_running(task: asyncio.Task | None) -> None:
    if task and not task.done():
        task.cancel()       # Only requests cancellation - doesn't wait
        try:
            await task      # Wait for task to actually finish cancelling
        except asyncio.CancelledError:
            pass            # Expected - task was cancelled


@web_app.get("/")
async def root():
    return {"status": "ok", "service": "Admissions Agent Northeastern"}

@web_app.post("/webhook")
async def twillio_webhook(request: Request):
     
    form_data = await request.form()
    callSid = str(form_data["CallSid"])
    caller_number= str(form_data["From"]).lstrip("+")

    response = VoiceResponse()
    response.say("Welcome to the Northeastern University AI Admission Chat Service.")

    connect = Connect()
    base_url = os.getenv("BASE_URL", "https://uncriticisably-quavery-louvenia.ngrok-free.dev")
    websocket_url = f"{base_url.replace('https://', 'wss://')}/ws/{caller_number}/{callSid}"
    conversation_relay = ConversationRelay(url = websocket_url, language = "en-US", interruptible = True)
    conversation_relay.language(
        code="es-ES",
        tts_provider="google",
        voice="es-ES-Standard-A",
        transcription_provider="google",
        speech_model="long"
    ) 
    conversation_relay.language(
        code="zh",
        tts_provider="ElevenLabs",
        voice="ZL9dtgFhmkTzAHUUtQL8", 
        transcription_provider="deepgram",
        speech_model="nova-2")
    

    connect.append(conversation_relay)
    response.append(connect)

    return Response(content=str(response), media_type="application/xml")

@web_app.websocket("/ws/{caller_number}/{callSid}")
async def websocket_endpoint(websocket: WebSocket, caller_number: str, callSid: str):

    await websocket.accept()
    print(f"WebSocket connected for call: {caller_number}")

    msg = await websocket.receive_json()
    
    callSession = CallState()
    callSession.caller_number = f"+{caller_number}" #need in order to call the transfer function
    callSession.call_sid = callSid
    if msg.get("type") == "setup":
        print(f"ConversationRelay connected, call from {msg.get('from')}")
        callSession.transcript.append({"speaker": "Agent", "text": "What is your preferred language—English, Spanish, or Chinese?"})
        await websocket.send_json({"type": "text", "token": "What is your preferred language—English, Spanish, or Chinese?", "last": True})
        
        while True: 
            #Language Set Up for AI Agent
            msg = await websocket.receive_json()
            if msg.get('type') != 'prompt':
                continue
            if not msg.get('last', False):
                continue
            
            userResponse = msg.get("voicePrompt","English")
            callSession.transcript.append({"speaker": "User", "text": userResponse})
            callSession.language = await b.LanguageDetection(userResponse)
            
            if callSession.language not in language_code_mapping:
                await websocket.send_json({"type": "text", "token": "Sorry, I didn't detect a supported language. Defaulting to English.", "last": True})
                callSession.language = "English"
                #continue
            
            language_code = language_code_mapping[callSession.language]
            print(f"Detected language: {callSession.language} (code: {language_code}) from user response: {userResponse}")
            break
        await websocket.send_json({"type": "text","token": "Would you like to receive an email transcript of this conversation at the end of the call? Please respond with 'yes' or 'no'.", "last": True})
        while True:
            msg = await websocket.receive_json()
            if msg.get('type') != 'prompt':
                continue
            if not msg.get('last', False):
                continue
            UserResponses = msg.get("voicePrompt","")
            if "yes" in UserResponses.lower():
                await websocket.send_json({"type": "text", "token": "Great! What is your email address?", "last": True})
                while True:
                    emailAddress = await websocket.receive_json()
                    if emailAddress.get('type') != 'prompt':
                        continue
                    if not emailAddress.get('last', False):
                        continue
                    parsed_email = (await b.EmailRetrieval(emailAddress.get("voicePrompt", ""))).lower()
                    if parsed_email == "unable to parse email":
                        await websocket.send_json({"type": "text", "token": "Sorry, I couldn't get the email address. Please try again.", "last": True})
                        continue
                    callSession.email = parsed_email
                    await websocket.send_json({"type": "text", "token": "Email has been set.", "last": True})
                    break
            else:
                await websocket.send_json({"type": "text", "token": "No problem! Email will not be set", "last": True})
                break
            await websocket.send_json({"type": "text", "token": "I have the email address set as " + callSession.email + ". Please confirm using 'yes' or 'no'.", "last": True})
            while True:
                confirmationMsg = await websocket.receive_json()
                if confirmationMsg.get('type') != 'prompt':
                    continue
                if not confirmationMsg.get('last', False):
                    continue
                confirmationResponse = confirmationMsg.get("voicePrompt","")
                if "yes" in confirmationResponse.lower():
                    await websocket.send_json({"type": "text", "token": "Great! I am happy the email is correct.", "last": True})
                    break
                if "no" in confirmationResponse.lower():
                    await websocket.send_json({"type": "text", "token": "Okay, let's try getting the email address again. What is your email address?", "last": True})
                    while True:
                        emailAddress = await websocket.receive_json()
                        if emailAddress.get('type') != 'prompt':
                            continue
                        if not emailAddress.get('last', False):
                            continue
                        parsed_email = (await b.EmailRetrieval(emailAddress.get("voicePrompt", ""))).lower()
                        if parsed_email == "unable to parse email":
                            await websocket.send_json({"type": "text", "token": "Sorry, I couldn't get the email address. Please try again.", "last": True})
                            continue
                        callSession.email = parsed_email
                        await websocket.send_json({"type": "text", "token": "Email I have now is " + callSession.email + ". Please confirm by saying 'confirm'", "last": True})
                        while True:
                            confirmationMsg = await websocket.receive_json()
                            if confirmationMsg.get('type') != 'prompt':
                                continue
                            if not confirmationMsg.get('last', False):
                                continue
                            confirmationResponse = confirmationMsg.get("voicePrompt","")
                            if "confirm" in confirmationResponse.lower():
                                await websocket.send_json({"type": "text", "token": "Great! I am happy the email is correct.", "last": True})
                                break
                            else:
                                await websocket.send_json({"type": "text", "token": "Okay, We will proceed without an email address. There will be another opportunity to provide it at the end of the call", "last": True})
                                callSession.email = ""
                                break
                        break
                break
            break
        await websocket.send_json({"type": "language", "transcriptionLanguage": language_code, "ttsLanguage": language_code})
        await asyncio.sleep(3) 
        await websocket.send_json({"type": "text", "token": language_greeting[callSession.language], "last": True})
        callSession.transcript.append({"speaker": "Agent", "text": language_greeting[callSession.language]})     
        await websocket.send_json({"type": "config", "interruptible": True}) 
    try:
        current_task = None
        while True: # main call loop
            # if not callSession.ending_state:
            if callSession.ending_state:
                break

            msg = await websocket.receive_json()

            if msg.get("type") == "interrupt": # ignore interrupt in ending state
                # cancel created Current task (should only ever be one)
                await cancel_task_if_running(current_task)
                current_task = None 
                # maybe update state here 
                continue 
            
            if msg.get("type") == "prompt":
                if not msg.get("last", False): # last: True when have full user message
                    continue  # ignore partials

                full_input = msg.get("voicePrompt", "") # only adding to transcript after get response to avoid double passing user questions   
                print(f"The current user input is '{full_input}'. (Before passing to parse function")

                
                await cancel_task_if_running(current_task) # do not want second task already running before creating another

                current_task = asyncio.create_task(process_input_states(full_input, callSession, websocket))
                await current_task
                if callSession.ending_state:
                    break


    except WebSocketDisconnect:
        print("Caller hung up — WebSocket closed")

# For local dev: won't exe on Cloud
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("agent:web_app", host="0.0.0.0", port=8000, reload=True)



               



