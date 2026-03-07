from unittest import result
from dotenv import load_dotenv
from sympy import im
from baml_client.sync_client import b
import mysql.connector as mysql
import pandas as pd


# from baml_client import types

# def get_uni_context(group : str, subgroup: str) -> str:
#     concat_key = group + subgroup

#     fake_db = {
#         "Admission Requirements DomesticGPA": 3.8,
#         "Application Questions Dates": "January 1st"
#     }

#     return str(fake_db.get(concat_key, "Invalid Key"))

df = pd.read_excel('Data.xlsx', engine='openpyxl')
context_dict = df.groupby('Key')['Information Text'].apply(lambda x: " ".join(x.astype(str))).to_dict()
def get_university_context(key : str) -> str:

    # fake_db = {
    #     "AdmissionDomesticSubgroup.GPA": 3.8,
    #     "Application Questions Dates": "January 1st",
    #     "GlobalStudentSubgroup.Abroad_Opportunities": "Northeastern offers study abroad programs in Europe, Asia, and Australia."
    # }

    information = context_dict.get(key, "Invalid Key")
    return information



if __name__ == "__main__":
    load_dotenv()

    question = "What materials do I need for my application?"

    ##### for testing
    # parsed = {
    #     "category": {
    #         "AdmissionDomestic_Subgroup": "GPA"
    #     }
    # }
    # print(f"Parsed is: {parsed.get('category', 'N/A').keys()}")
    # first = list(parsed.get('category', 'N/A').keys())[0]
    # second = parsed["category"][first] if first else "No category found"

    # print(f"First:{first}, Second:{second}")

    parsed = b.ParseQuery(question)

    parsed_dict = parsed.category.model_dump()
    print("Pydantic Object:", parsed_dict)
    print("parsing option 1 (get Group by itself): ", list(parsed_dict.keys())[0].replace("_Subgroup", ""))
    print("parsing option 2 (gets total from serialized PyDantic): ", list(parsed_dict.values())[0])
 
    total_key = str(list(parsed_dict.values())[0])

    db_context = get_university_context(key=total_key)
    print(f"Retrieved Context:{db_context}")

    AgentResponse = b.AnswerQuery(question,db_context)
    cleaned_response = AgentResponse.replace('\n', ' ')
    print("Formatted Response:",cleaned_response)



    # BAML will automatically print the response in the terminal
    #print(f"LLM response:{answer}")
    
