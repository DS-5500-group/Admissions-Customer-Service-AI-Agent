from fastapi import FastAPI, Form
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse, Gather, Redirect



app = FastAPI()
@app.post("/")
def InitialResponse():
    respond = VoiceResponse()
    gather = Gather(input='speech', speech_timeout='auto', action='/echo', method = 'POST')
    gather.say("This is the echo test on GCP.")
    respond.append(gather)
    # if there is no user response detected (gather will listen)
    respond.say("I did not hear, try again.")
    respond.redirect("/", method='POST')
    return Response(content=str(respond), media_type="text/xml")

    # Fast API by default returns everything as JSON, below would not work
    # return str(respond)

@app.post("/echo")
def echo(SpeechResult: str = Form(...)): 
    print(f"Received speech: {SpeechResult}")
    answer = VoiceResponse()
    answer.say(f"You said: {SpeechResult}") # SpeechResult is specific key in the POST Body Form 

    gather = Gather(input='speech', speech_timeout='auto', action='/echo', method = 'POST')
    gather.say("Do you want to try again?")
    answer.append(gather)
    return Response(content=str(answer), media_type="text/xml")


# FOR LOCAL DEV
# if __name__ == "__main__":
#     app.run(port=5000)

