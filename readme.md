# Northeastern Admissions-Customer-Service AI Agent
### Using Our System:
If you simply want to demo the system without running the code yourself, please contact me for the demo phone number.  
## Local Development Setup:

#### Prerequisites:  
- Create a Twilio account and choose a phone number (free trial will cover cost)
- Install and have an ngrok account setup and ready to crate a local URL.  
- Setup a 'Resend' email sending service, obtain API key
- Obtain an OpenAI API key
- Install the BAML VScode extension for convenience

#### Execution Steps:

1. Clone the repo
2. Place the two API keys (OpenAI and Resend) into a .env file located in /src
- OPENAI_API_KEY=\<key>
- RESEND_API_KEY=\<key>
3. Setup a python virtual environment 
4. Install dependencies:  
  ```pip install -r requirements.txt```
5. If first time using ngrok, authenticate:  
   ```ngrok config add-authtoken YOUR_TOKEN```
6. Setup and startup the local ngrok URL:  
  ```ngrok http 8000```
7. Copy the ngrok URL into Twilio at: Develop-> Phone Numbers -> Manage -> Active numbers -> Click on your number.
  Paste in box next to "A call comes in WebHook".  
  **Note:** You will need to add "/webhook" to the end of your ngrok URL: \<your url>/webhook
8. Run the application:  
  ```python agent.py```
9. Make a call to your phone number

## Cloud Development Setup:  

#### Prerequisites: 
- Create a Google Cloud Provider (GCP) account and download locally the Gcloud terminal SDK.
- On GCP create a new Project
- Within the Project enable the following services: Artifact Registry, Cloud Run, Google Cloud Storage
- Create a new Artifact Registry Repo.
- Create a Twilio account and choose a phone number (free trial will cover cost) 
- Setup a 'Resend' email sending service, obtain API key
- Obtain an OpenAI API key

#### Execution Steps:
1. Clone the repo
2. Send the files to GCP for building a Docker image:  
```gcloud builds submit --tag us-central1-docker.pkg.dev/<YOUR PROJECT ID>/<YOUR ARTIFACT REG. REPO>/agent:latest```
3. If succesful, deploy the image as a GCP Cloud Run:  
**Note:** If on Mac or Linux, replace the backticks below with forward slashes to create multi-line terminal prompts.  
```
gcloud run deploy agent `  
  --image us-central1-docker.pkg.dev/<YOUR PROJECT ID>/<YOUR ARTIFACT REG. REPO>/agent:latest `  
  --region us-central1 `  
  --allow-unauthenticated `  
  --set-env-vars="OPENAI_API_KEY=<YOUR KEY>" `  
  --set-env-vars="RESEND_API_KEY=<YOUR KEY>" `
  --timeout=3600  
```
**Note:** For first time deployment, the Cloud Run URL is not created yet so you will need to run: 
```
gcloud run services update agent `  
  --update-env-vars="BASE_URL=<YOUR CLOUD RUN URL>"
```
**In all future deployments:**  
```
gcloud run deploy agent `  
  --image us-central1-docker.pkg.dev/<YOUR PROJECT ID>/<YOUR ARTIFACT REG. REPO>/agent:latest `  
  --region us-central1 `  
  --allow-unauthenticated `  
  --set-env-vars="OPENAI_API_KEY=<YOUR KEY>" `  
  --set-env-vars="RESEND_API_KEY=<YOUR KEY>" `
  --set-env-vars="BASE_URL=<YOUR CLOUD RUN URL>" `  
  --timeout=3600  
```
4. Copy the Cloud Run URL to your Twilio account:
Navigate to: Develop-> Phone Numbers -> Manage -> Active numbers -> Click on your number.
Paste in box next to "A call comes in WebHook".  
**Note:** You will need to add "/webhook" to the end of your Cloud-Run URL: \<your url>/webhook
5. Make a call to your phone number





### Explanation of BAML files
1. /baml_src/clients.baml  
These are the options for LLM api clients to use: Custom client option (can define fall back models and other options), or default OpenAI, Claude, Gemini, etc.   
2. /baml_src/generators.baml  
When you run ```baml-cli generate```, this BAML code will generate the Baml Client code based on the options specified.  
3. /baml_src/app_functions.baml  
These are our user defined BAML classes, and subsequent parsing functions.  
4. /baml_src/resume.baml  
This is just a tutorial file for experimentation, should be deleted later.  

