
import mysql.connector as mysql
from dotenv import load_dotenv
import os
from baml_client.sync_client import b
from fastapi import FastAPI, Form
from fastapi.responses import Response

load_dotenv()
app = FastAPI()

LOG_FILE = "log.txt"


def get_universityInfo(question: str) -> str:
    
    #LOCAL OPTION for DB connection 
    # conn = mysql.connect(
    #     host = os.getenv("DB_HOST"),
    #     user= os.getenv("DB_USERNAME"),
    #     password = os.getenv("DB_PASSWORD"),
    #     database = os.getenv("DB_NAME"),
    #     port = 3306 
    # )

    conn = mysql.connect(
    host="34.56.124.244", # capstonedb2 
    port = 3306, # default MySQL port
    user= os.getenv("DB_USERNAME"),
    password = os.getenv("DB_PASSWORD"),
    database = os.getenv("DB_NAME"),
    charset="utf8mb4" 
    )

    conn.set_charset_collation("utf8mb4", "utf8mb4_0900_ai_ci")
    cursor = conn.cursor()


    parsed = b.ParseQuery(question)
    parsed_dict = parsed.category.model_dump()
    # print("Pydantic Object:", parsed_dict)
    # print("parsing option 1 (get Group by itself): ", list(parsed_dict.keys())[0])
    # print("parsing option 2 (gets total from serialized PyDantic): ", list(parsed_dict.values())[0])
    groupName = list(parsed_dict.keys())[0]
    subgroup = list(parsed_dict.values())[0].split('.')[-1]
    
    if subgroup == "SAT" or subgroup == "ACT": # FIX THIS, temporary for now
        subgroup = "SAT/ACT"
    key = groupName + "_" + subgroup

    #print(f"Constructed key for DB query: {key}")

    cursor.execute("SELECT Information_Text FROM informationdatabase WHERE Category_Key = %s;", (key,))

    Information = []

    for results in cursor:
        Information.append(results[0])
    
    #print(f"Retrieved Information from DB: {Information}")

    cursor.close()
    conn.close()

    stringVariable = "\n".join(Information)

    answer = b.AnswerQuery(question, stringVariable)
    with open(LOG_FILE, 'a') as f:
        f.write(f"Question: {question}\n")
        f.write(f"Key constructed for DB query: {key}\n")
        f.write(f"Retrieved Information from DB: {Information}\n")
        f.write(f"LLM response: {answer}\n\n")
    
    return answer

if __name__ == "__main__":
    load_dotenv()

    
    with open(LOG_FILE, 'w') as f:
        f.write("=== Experiments For DB Retrieval ON CLOUD DB===\n")

    question = "What GPA does Northeastern require for admissions?"
    questions = [
        "What is the general ranking of Northeastern University?",
        "How does Northeastern's CS program rank nationally?",
        "How much is the cost of tuition?",
        "How much does on-campus housing cost?",
        "What is the address of the Boston campus?",
        "What are the employment outcomes for Northeastern graduates?",
        "When are the due dates for Early Decision applications?",
        "What is the application fee?",
        "Is the SAT required for domestic applicants?",
        "Is the SAT required for international applicants?",
        #"What GPA does Northeastern require for admissions?",
        "What GPA does Northeastern require for international admissions?",
        #"What is the contact information for the admissions office?",
        "If admitted students need support, what type of services can they contact?"
    ]
    for q in questions:
        answer = get_universityInfo(q)



    #answer = get_universityInfo(question)
