# Admissions-Customer-Service-AI-Agent

## Setup

1. Obtain an OpenAI API key and place it in a .env file located in /src
- OPENAI_API_KEY=\<key>
2. Setup a python virtual environment 
3. ```pip install -r requirements.txt```
4. Install the BAML VScode extension for convenience: 
    - Saving the BAML files in /baml_src will automatically build a new BAML Client code in /src/baml_client
    - Otherwise will need to run command:
    - ```baml-cli generate```

### Explanation of Architecture/files 
1. /baml_src/clients.baml  
These are the options for LLM api clients to use: OpenAI, Claude, Gemini, etc.   
2. /baml_src/generators.baml  
When you run ```baml-cli generate```, this BAML code will generate the Baml Client code based on the options specified.  
3. /baml_src/app_functions.baml  
These are our user defined BAML classes, and subsequent parsing functions.  
4. /baml_src/resume.baml  
This is just a tutorial file for experimentation, should be deleted later.  

