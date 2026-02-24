
import mysql.connector as mysql
from dotenv import load_dotenv
import os
from baml_client.sync_client import b
from flask import Flask, app, request, jsonify

load_dotenv()
app = Flask(__name__)

def get_universityInfo(question: str) -> str:
# Connect to the database
#My database was set up in mysql workbench
    conn = mysql.connect(
    user= os.getenv('DB_username'),
    password = os.getenv('DB_password'),
    database = os.getenv('DB_name'),
    host = os.getenv('DB_host'),
    port = 3306)    

    cursor = conn.cursor()


    parsed = b.ParseQuery(question)
    parsed_dict = parsed.category.model_dump()
    print("Pydantic Object:", parsed_dict)
    print("parsing option 1 (get Group by itself): ", list(parsed_dict.keys())[0])
    print("parsing option 2 (gets total from serialized PyDantic): ", list(parsed_dict.values())[0])
    groupName = list(parsed_dict.keys())[0]
    subgroup = list(parsed_dict.values())[0].split('.')[-1]

    cursor.execute("SELECT Information_Text FROM informationdatabase WHERE Sub_Category = %s;", (subgroup,))

    Information = []

    for results in cursor:
        Information.append(results[0])

    cursor.close()
    conn.close()

    stringVariable = "\n".join(Information)

    answer = b.AnswerQuery(question, stringVariable)
    return answer





@app.route('/informationObtained', methods=['POST'])
def get_information():
    data = request.get_json()
    question = data.get('question')
    answer = get_universityInfo(question)
    return jsonify({'answer': answer})