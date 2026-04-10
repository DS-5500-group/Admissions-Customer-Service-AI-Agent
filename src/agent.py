import os
from dotenv import load_dotenv
import requests
import asyncio
from dataclasses import dataclass, field
import time
from typing import Set, Dict


import pandas as pd
import resend
# from baml_client.sync_client import b
from baml_client.async_client import b 
from baml_client.types import ClassifiedInput
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response
from twilio.twiml.voice_response import VoiceResponse, Connect, ConversationRelay, Dial
from twilio.rest import Client as TwilioClient

load_dotenv() # only for local 

resend.api_key = os.getenv("RESEND_API_KEY")
#print(f"Resend API: Key is: {resend.api_key}.")

web_app = FastAPI(title="Admissions Agent")


@dataclass
class CallState:
    transcript: list = field(default_factory=list)
    ending_state: bool = False
    grab_email_state: str = ""
    language: str = "English"
    email : str = ""
    caller_number: str = ""
    call_sid: str = ""

# Valid Group -> Subgroup mappings based on BAML definition
VALID_GROUP_SUBGROUPS: Dict[str, Set[str]] = {
    "Dining_food": {
        "Dining_Halls", "Retail_Dining", "Allergy_Info", 
        "Plan_Options_And_Cost", "Contact_Info"
    },
    "Housing": {
        "Housing_Cost", "Layout_Info", "Off_Campus", 
        "Moving_Information", "Contact_Info"
    },
    "Student_Amenities_Activities": {
        "Gym", "Student_Activities_Fees", "Clubs", "Game_Rooms", 
        "Volunteering", "Transportation", "Greek_Life", "Study_Space", "Contact_Info"
    },
    "Safety": {
        "RedEye_Night_Shuttle", "Security_App", "Campus_Escort", 
        "Card_Entry", "Crime_Statistics", "Contact_Info"
    },
    "Athletics": {
        "Varsity_Sports", "Intramural", "Signature_Events", "Contact_Info"
    },
    "Admission_Application": {
        "Decision_Types_Outcomes", "Dates_Deadlines", "Portal_Info", 
        "Application_Materials", "Financial_Aid", "Estimated_Cost", 
        "Tours", "Acceptance_Criteria_Stats", "Contact_Info", 
        "AP_Credit_Lookup", "Enrollment", "Transfer_Applicants", 
        "Orientation", "Honors_Program"
    },
    "Ranking_GeneralStats": {
        "Overall_School_Ranking", "Extracurriculars", "Majors", 
        "Demographics", "Career_Outcomes"
    },
    "Student_Support": {
        "Contact_Info", "Resources_Overview", "Confidential_Resources", 
        "National_Resources", "Policies"
    },
    "Experiential_Learning": {
        "Coop_Process", "Coop_Salary", "Coop_Overview", 
        "Research", "NU_View", "Experiential_Projects"
    },
    "No_Matching_Group": {"NoSubgroup"},
    "NotApplicable": {"NotApplicable"},
}

# latest DB (on our Teams EXCEL)
db = pd.read_csv("DB.csv") 

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

def is_valid_pairing(group: str, subgroup: str) -> bool:
    if group not in VALID_GROUP_SUBGROUPS:
        return False
    return subgroup in VALID_GROUP_SUBGROUPS[group]

def query_university_context(parsed: ClassifiedInput) -> str:
    

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


async def end_call(call: CallState, websocket: WebSocket):
    print(f"Reached Final End Call message...Call ending")
    # Maybe better to have specialized end call BAML function. 
    transcript_str = "\n".join(f"{entry['speaker']}: {entry['text']}" for entry in call.transcript)
    goodbye_message = await b.AnswerQuery(question="Say a goodbye message to end the call", context="", transcript=transcript_str, language=call.language)

    await websocket.send_json({"type": "text", "token": goodbye_message, "last": True})
    call.transcript.append({"speaker": "Agent", "text":goodbye_message})
    await asyncio.sleep(10)
    await websocket.send_json({"type": "end"})

async def handle_email_end_state(user_input: str, call: CallState, websocket: WebSocket):
    if call.grab_email_state == "Initial":
        if "yes" in user_input.lower():
            await websocket.send_json({"type": "text", "token": language_email_confirmation_prompt.get(call.language, language_email_confirmation_prompt["English"]), "last": True})
            call.grab_email_state = "ParseEmail"
        else:
            await websocket.send_json({"type": "text", "token": "No problem! Email will not be sent", "last": True})
            await end_call(call, websocket)
    elif call.grab_email_state == "ParseEmail":
        parsed_email = (await b.EmailRetrieval(user_input)).strip().lower()
        if parsed_email == "unable to parse email":
            await websocket.send_json({"type": "text", "token": "Sorry, I couldn't get the email address. Please try again.", "last": True})
        else:
            call.email = parsed_email
            await websocket.send_json({"type": "language", "transcriptionLanguage": language_code_mapping[call.language], "ttsLanguage": language_code_mapping[call.language]})
            try:
                await email_transcript(call, call.language, websocket)
                await websocket.send_json({"type": "text", "token": "Ok, I sent you an email of this call transcript!", "last": True})
            except Exception as e:
                print(f"Email send error: {type(e).__name__}: {e}")
                await websocket.send_json({"type": "text", "token": "Sorry, there was an error sending the email.", "last": True})

            await end_call(call, websocket)
    

async def end_call_set_condition(user_input: str, call: CallState, websocket: WebSocket):
    await websocket.send_json({"type": "config", "interruptible": False})
    call.ending_state = True
    call.transcript.append({"speaker": "User", "text":user_input})

    if call.email:
        try:
            await email_transcript(call, call.language, websocket)
            await websocket.send_json({"type": "text", "token": "Ok, I sent you an email of this call transcript!", "last": True})
        except Exception as e:
            print(f"Email send error: {type(e).__name__}: {e}")
            await websocket.send_json({"type": "text", "token": "Sorry, there was an error sending the email.", "last": True})

        await end_call(call, websocket)
    else:
        call.grab_email_state = "Initial"
        await websocket.send_json({"type": "language", "transcriptionLanguage": "en-US", "ttsLanguage": language_code_mapping[call.language]})
        # ask if they want to receive email, handle in main loop
        await websocket.send_json({"type": "text", "token": language_email_prompt.get(call.language, language_email_prompt["English"]), "last": True})

'''
async def end_call_set_condition_old(user_input: str, call: CallState, websocket: WebSocket):
    await websocket.send_json({"type": "config", "interruptible": False})
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
                await websocket.send_json({"type": "text", "token": "No problem! Email will not be sent", "last": True})
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
'''
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


async def stream_answer_to_twilio(question, context, transcript, language, websocket):
    print("INSIDE STREAMING SECTION")
    start = time.perf_counter()
    stream = b.stream.AnswerQuery(question, context, transcript, language)
    
    First = True 
    previous = ""
    async for partial in stream: # partial builds cummulative response
        if partial is None:
            continue
        if partial and First:
            time_first_token = time.perf_counter() - start
            print(f"\nTIME TO FIRST TOKEN: {time_first_token}")
            First = False
            
        new_text = partial[len(previous):]  # extract only the new text
        if new_text:
            
            await websocket.send_json({
                "type": "text",
                "token": new_text,
                "last": False
            })
        previous = partial
    
    # need to get final because the last partial is not guranteed to be the last part of response
    final = await stream.get_final_response()
    remaining = final[len(previous):]
    
    await websocket.send_json({
        "type": "text",
        "token": remaining,  # could be "", that's fine
        "last": True
    })
    #print(f"Time (seconds) to respond fully: {time.perf_counter() - start}")
    return final  

async def process_input_states(user_input: str, call: CallState, websocket: WebSocket):
    
    try: 
        # Build redable string transcript from list of dicts
        if len(call.transcript) > 5:
            recent_transcript = call.transcript[-5:]
            transcript_str = "\n".join(f"{entry['speaker']}: {entry['text']}" for entry in recent_transcript)

        else: 
            transcript_str = "\n".join(f"{entry['speaker']}: {entry['text']}" for entry in call.transcript)
        
        # START state, will decide next action/state
        start = time.perf_counter()
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
        elif not is_valid_pairing(parsed.group.value, parsed.subgroup.value):
            # assumes that the Group will always be valid
            if parsed.group == "NotApplicable" or parsed.group == "No_Matching_Group":
                response = "I didn't hear, try asking again or a differnet question."
            else:
                # should be a string where if "_" in parsed.group is replaced with an "or" string
                clean_group = parsed.group.value.replace("_", " or ")
                if parsed.group.value == "Student_Amenities_Activities":
                    clean_group = "Student Amenities or Activities"
                # should be a string where the set of strings are converted to a single string: comma seperating subgroups and "_" replaced with " "
                clean_subgroup_list = ", ".join(sub.replace("_", " ") for sub in VALID_GROUP_SUBGROUPS[parsed.group.value])
            
            response = (
                f"It seems you are asking about {clean_group}. "
                f"I can respond to questions related to {clean_subgroup_list}."
            )
            await websocket.send_json({"type": "text", "token": response, "last": True})
            call.transcript.append({"speaker": "User", "text":user_input})
            call.transcript.append({"speaker": "Agent", "text":response})
        elif parsed.confidence <= 0.5 or parsed.clarification: # agent initiates clarification
            
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
                
                answer = await stream_answer_to_twilio(user_input, context, transcript_str, language=call.language, websocket=websocket)
                #answer = await b.AnswerQuery(user_input, context, transcript_str, language=call.language)
                response_time = time.perf_counter() - start
                print(f"\nRESPONSE TIME TOTAL FROM IN-OUT (STREAM) IS: {response_time}")
            # await websocket.send_json({"type": "text", "token": answer, "last": True})
            call.transcript.append({"speaker": "User", "text":user_input})
            call.transcript.append({"speaker": "Agent", "text":answer})
    
    except asyncio.CancelledError:
        print("Either interrupt or somehow second task created")
        raise # raise caught when "await task" after doing "task.cancel()"" 

    except Exception as e:
        # some needed protection 
        print(f"Error processing input: {e}")
        await websocket.send_json({
            "type": "text",
            "token": "I'm sorry, I had trouble with that. Could you try again?",
            "last": True
        })

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
    base_url = os.getenv("BASE_URL", "https://prominently-acidimetrical-season.ngrok-free.dev") #"https://uncriticisably-quavery-louvenia.ngrok-free.dev"
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
        await websocket.send_json({"type": "config", "interruptible": False})
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
            callSession.language = (await b.LanguageDetection(userResponse)).strip()
            
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
                    #parsed_email = (await b.EmailRetrieval(emailAddress.get("voicePrompt", ""))).lower()
                    parsed_email = (await b.EmailRetrieval(emailAddress.get("voicePrompt", ""))).strip().lower()
                    if parsed_email == "unable to parse email":
                        await websocket.send_json({"type": "text", "token": "Sorry, I couldn't get the email address. Please try again.", "last": True})
                        continue
                    callSession.email = parsed_email
                    await websocket.send_json({"type": "text", "token": "Email has been set.", "last": True})
                    break
            else:
                await websocket.send_json({"type": "text", "token": "No problem! Email will not be sent", "last": True})
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

            msg = await websocket.receive_json()

            if msg.get("type") == "interrupt": # ignore interrupt in ending state
                
                if callSession.ending_state: # maybe change this 
                    continue
                # cancel created Current task (should only ever be one)
                await cancel_task_if_running(current_task)
                current_task = None 
                # maybe update state here 
                continue 
            
            if msg.get("type") == "prompt":
                if not msg.get("last", False): # last: True when have full user message
                    continue  # ignore partials

                full_input = msg.get("voicePrompt", "") # only adding to transcript after get response to avoid double passing user questions   
                print(f"The current user input is '{full_input}'. (Before passing to parse function or Handling End-State)")

                if callSession.ending_state:
                    await handle_email_end_state(full_input, callSession, websocket)
                else:

                    await cancel_task_if_running(current_task) # do not want second task already running before creating another
                    current_task = asyncio.create_task(process_input_states(full_input, callSession, websocket))
                    # await current_task # this is blocking event loop 

    except WebSocketDisconnect:
        print("Caller hung up — WebSocket closed")

# For local dev: won't exe on Cloud
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("agent:web_app", host="0.0.0.0", port=8000, reload=True)



               



