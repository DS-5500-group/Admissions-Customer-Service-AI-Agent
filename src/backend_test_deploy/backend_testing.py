
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import os

import mysql.connector as mysql
from fastapi import FastAPI, Form
from fastapi.responses import Response

from baml_client.sync_client import b
from google.cloud import storage

load_dotenv()
back_app = FastAPI()


def query_university_context(question: str) -> tuple[str, str]:
    
    #LOCAL OPTION for DB connection 
    # conn = mysql.connect(
    #     host = os.getenv("DB_HOST"),
    #     user= os.getenv("DB_USERNAME"),
    #     password = os.getenv("DB_PASSWORD"),
    #     database = os.getenv("DB_NAME"),
    #     port = 3306 
    # )

    # DB is retired, but this was used before
    conn = mysql.connect(
    unix_socket="/cloudsql/ds5500-487815:us-central1:capstonedb2", # for Cloud Run, use the unix socket path
    #host="34.56.124.244", # capstonedb2 instance on GCP
    #port = 3306, # default MySQL port
    user="root", 
    password="", # password actually needed
    database="capstonedb2",
    charset="utf8mb4" # maybe dont need
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

    contextString = "\n".join(Information)
    return contextString, key


@back_app.get("/")
def root():
    return {"status": "ok", "service": "Backend Testing for Admissions Agent: Is working. "}

@back_app.post("/single-query-response")
def single_query_response(question: str = Form(...)):
    context, _ = query_university_context(question)
    answer = b.AnswerQuery(question, context)
    return Response(content=answer, media_type="text/plain")

@back_app.post("/run-multiple-queries-test")
def run_multiple_queries_test():
    now_et = datetime.now(ZoneInfo("America/New_York"))
    LOG_FILE = f"/tmp/multiple_queries_test_{now_et.strftime('%Y%m%d_%H%M%S')}.txt"


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

    test_count = len(questions)
    fail_count = 0

    with open(LOG_FILE, 'w') as f:
        f.write("=== Experiments For DB Retrieval ON CLOUD RUN===\n")

    for q in questions:
        context, key = query_university_context(q)
        if context == "":
            fail_count += 1
        
        answer = b.AnswerQuery(q, context)
        with open(LOG_FILE, 'a') as f:
            f.write(f"Question: {q}\n")
            f.write(f"Context retrieved from DB: {context}\n")
            f.write(f"Key used: {key}\n")
            f.write(f"LLM response: {answer}\n\n")

        # write to GCP bucket
    client = storage.Client()
    bucket = client.bucket("agent-app-metadata")
    blob = bucket.blob(os.path.basename(LOG_FILE))
    blob.upload_from_filename(LOG_FILE)

    summary = f"Test completed. Total questions: {test_count}, Failed retrievals: {fail_count}."
    return Response(content=summary, media_type="text/plain")

