from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import pandas as pd


# from fastapi import FastAPI, Form
# from fastapi.responses import Response

from baml_client.sync_client import b
# from google.cloud import storage

load_dotenv()

db = pd.read_csv("DB Full Collection.csv")

def query_university_context(question: str) -> tuple[str, str]:
    


    parsed = b.ParseQuery(question)
    #### OLD METHOD:
    # parsed_dict = parsed.category.model_dump()
    # print("Pydantic Object:", parsed_dict)
    # print("parsing option 1 (get Group by itself): ", list(parsed_dict.keys())[0])
    # print("parsing option 2 (gets total from serialized PyDantic): ", list(parsed_dict.values())[0])
    # groupName = list(parsed_dict.keys())[0]
    # subgroup = list(parsed_dict.values())[0].split('.')[-1]

    predicted_key = parsed.group + "_" + parsed.subgroup
    #context = db[db["Lookup_Key"]==predicted_key]["Information Text"].values[0]
    try:
        context = db.loc[db["Lookup_Key"]==predicted_key, "Information Text"].item() # .item() should return the single entry, "scalor" value
        return context, predicted_key
    except ValueError: # 0 or multiple matches for when Lookup_Key==predicted_key, .item() only allows for single row
        return "", predicted_key


    #print(f"Constructed key for DB query: {predicted_key}")
    #print(f"Retrieved Information from DB: {context}")







def single_query_response(question: str) -> str:
    context, _ = query_university_context(question)
    answer = b.AnswerQuery(question, context)
    return answer


def run_multiple_queries_test():
    #now_et = datetime.now(ZoneInfo("America/New_York"))
    LOG_FILE = "multiple_queries_test.txt"


    df_test = pd.read_csv('test_questions.csv')

    with open(LOG_FILE, 'w') as f:
        f.write("=== Experiments For DB Retrieval LOCALLY===\n")

    fail_count = 0
    for i, row in df_test.iterrows():
        #if i < 2:
        q = row['question']
        context, predicted_key = query_university_context(q)

        a = "ERROR: No answer generated because answerable, try again or be more specific."
        if context != "":
            a = b.AnswerQuery(q,context)
        expected_key = row['expected_key']
        match_key = predicted_key == expected_key #bool
        fail_count += 1 if not match_key else 0
        
        with open(LOG_FILE, 'a') as f:
            f.write(f"Question: {q}\n")
            f.write(f"Predicted key: {predicted_key}\n")
            f.write(f"Expected key: {expected_key}\n")
            f.write(f"Match: {match_key}\n")
            f.write(f"LLM response: {a}\n\n")

        # else:
        #     break

    with open(LOG_FILE, 'a') as f:
        f.write(f"Test completed. Total questions: {len(df_test)}, Failed key predictions: {fail_count}.\n")

    return 0

    # test_count = len(questions)
    # fail_count = 0

    # with open(LOG_FILE, 'w') as f:
    #     f.write("=== Experiments For DB Retrieval LOCALLY===\n")

    # for q in questions:
    #     context, key = query_university_context(q)
    #     if context == "":
    #         fail_count += 1
        
    #     answer = b.AnswerQuery(q, context)
    #     with open(LOG_FILE, 'a') as f:
    #         f.write(f"Question: {q}\n")
    #         f.write(f"Context retrieved from DB: {context}\n")
    #         f.write(f"Key used: {key}\n")
    #         f.write(f"LLM response: {answer}\n\n")


    # summary = f"Test completed. Total questions: {test_count}, Failed retrievals: {fail_count}."
    # return Response(content=summary, media_type="text/plain")

if __name__ == "__main__":
    status = run_multiple_queries_test()
    print(f"Status of test is {"Success" if status==0 else "Failure"}")