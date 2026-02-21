from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse, Gather
import openai
import os
import string
openai.api_key = os.getenv("OPENAI_API_KEY")


app = Flask(__name__)

@app.route("/", methods = ['GET','POST'])
def Response():
    respond = VoiceResponse()
    gather = Gather(input='speech', speech_timeout='auto', action='/bothumaninteraction', method = 'POST')
    gather.say("Welcome to the Northeastern University AI Admission Service. Do you have any questions?")   
    respond.append(gather)
    respond.say("Sorry, I didn't get that. Please try again.")
    return str(respond)


# #Back and Forth conversation between the user and the bot
@app.route("/bothumaninteraction", methods = ['POST'])
def conversation():
    userStatement = request.form.get('SpeechResult', '').lower()
    wordDivided = userStatement.split()
    for i in range(len(wordDivided)):
        wordDivided[i] = wordDivided[i].strip(string.punctuation)
    if any(word in ["no", 'not','nope','none'] for word in wordDivided):
        answer = VoiceResponse()
        answer.say("Thank you for using the Northeastern University AI Admission Service Goodbye!")
        answer.hangup()
        return str(answer)
    AIresponse = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "An assistant for Northeastern University Admissions. Answer the user's questions about the university and the admissions process."},
            #Integrate the database here for more accurate responses
            {"role": "user", "content": userStatement}
        ]
    ).choices[0].message.content

    answer = VoiceResponse()
    answer.say(AIresponse)
    answer.pause(length=3)
    gather = Gather(input='speech', speech_timeout='auto', action='/bothumaninteraction', method = 'POST')
    gather.say("Do you have any more questions?")
    answer.append(gather)
    

    return str(answer)




if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

