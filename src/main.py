from unittest import result
from dotenv import load_dotenv
from baml_client.sync_client import b
# from baml_client import types

# def get_uni_context(group : str, subgroup: str) -> str:
#     concat_key = group + subgroup

#     fake_db = {
#         "Admission Requirements DomesticGPA": 3.8,
#         "Application Questions Dates": "January 1st"
#     }

#     return str(fake_db.get(concat_key, "Invalid Key"))

def get_university_context(key : str) -> str:

    fake_db = {
        "AdmissionDomesticSubgroup.GPA": 3.8,
        "Application Questions Dates": "January 1st"
    }

    return str(fake_db.get(key, "Invalid Key"))



if __name__ == "__main__":
    load_dotenv()

    question = "What GPA does Northeastern require for admissions?"

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
    print("parsing option 1 (get Group by itself): ", list(parsed_dict.keys())[0])
    print("parsing option 2 (gets total from serialized PyDantic): ", list(parsed_dict.values())[0])

    total_key = str(list(parsed_dict.values())[0])


    db_context = get_university_context(key=total_key)
    print(f"Retrieved Context:{db_context}")

    answer = b.AnswerQuery(question, db_context)
    
    # BAML will automatically print the response in the terminal
    #print(f"LLM response:{answer}")
    
