import mysql.connector as mysql
from dotenv import load_dotenv
import os
from baml_client.sync_client import b





def get_universityInfo(question: str) -> str:
# Connect to the database
#My database was set up in mysql workbench
    conn = mysql.connect(
        host="localhost",
        user="", #Make sure to replace this with your actual username or use environment variables for security
        password="", #Make sure to replace this with your actual password or use environment variables for security
        database="capstonedb" #Name of the database after the sql file is run
    )

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

if __name__ == "__main__":
    load_dotenv()

    question = "What GPA does Northeastern require for admissions?"
    answer = get_universityInfo(question)
