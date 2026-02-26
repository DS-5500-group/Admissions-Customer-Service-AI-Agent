
import mysql.connector as mysql
from dotenv import load_dotenv
import os
from baml_client.sync_client import b
from fastapi import FastAPI, Form
from fastapi.responses import Response

load_dotenv()
app = FastAPI()

@app.post("/university-info/")
def get_universityInfo(question: str = Form(...)) -> str:
    conn = mysql.connect(
    user= os.getenv("DB_USERNAME"),
    password = os.getenv("DB_PASSWORD"),
    database = os.getenv("DB_NAME"),
    host = os.getenv("DB_HOST"),
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

