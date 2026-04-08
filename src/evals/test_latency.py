import time
from dotenv import load_dotenv
import asyncio
from pathlib import Path

import pandas as pd
from baml_client.sync_client import b as b_sync
from baml_client.async_client import b as b_async
from baml_client.types import ClassifiedInput

load_dotenv()

# This gives you the directory the script lives in, regardless of where you run from
# need this to open and read the test .csv file in /eval
SCRIPT_DIR = Path(__file__).parent

from baml_client.async_client import b

sem = asyncio.Semaphore(10)

sync_exp_times = []
async_exp_times = []

db = pd.read_csv("DB.csv")

test_inputs = pd.read_csv(SCRIPT_DIR/"test_sets/test_classify_easy.csv").iloc[50:100] # reduce test set since sync takes long
#test_inputs = pd.read_csv(SCRIPT_DIR/"test_sets/classify_short.csv")

def query_university_context(parsed: ClassifiedInput) -> str:

    predicted_key = parsed.group + "_" + parsed.subgroup
    try:
        context = db.loc[db["Lookup_Key"]==predicted_key, "Information Text"].item() # .item() should return the single entry, "scalor" value
        return context, predicted_key
    except ValueError: # 0 or multiple matches for when Lookup_Key==predicted_key, .item() only allows for single row
        return "", predicted_key

def run_sync_tests():
    
    for idx, row in test_inputs.iterrows():
        start_test = time.perf_counter()
        try:
            parsed = b_sync.ClassifyInput(current_input=row["current_input"],transcript=row["transcript"])
            if parsed.overall_classification == "Out_Of_Scope":
                predicted_key = "NotApplicable_NotApplicable"
                instruction = "Instruct that the users request was out of scope. Try to ask a clarifying question or tell them topics you can answer"
                response =  b_sync.AnswerQuery(question=instruction, context="", transcript=row["transcript"]+f"\nUser: {row["current_input"]}", language="English")
            
            elif parsed.overall_classification == "End_Call":  
                predicted_key = "NotApplicable_NotApplicable"
                response = b_sync.AnswerQuery(question="Say a goodbye message to end the call", context="", transcript="", language="English")

            elif parsed.confidence <= 0.5 or parsed.group == "UnAnswerable" or parsed.subgroup == "NoSubgroup":
                predicted_key = "NotApplicable_NotApplicable"
                instruction = "Ask a clarifying question since it is not clear from the transcript what the user is asking for."
                response =  b_sync.AnswerQuery(question=instruction, context="", transcript=row["transcript"]+f"\nUser: {row["current_input"]}", language="English")
            #elif REQUEST USER AGENT CASE, ADD LATER:
            else: 
                # Normal processing
                context, predicted_key = query_university_context(parsed)
                response = b_sync.AnswerQuery(question=row["current_input"],context=context,transcript=row["transcript"], language="English")

            single_test_time = time.perf_counter() - start_test
            sync_exp_times.append(single_test_time)

            block = (
            f"--- SYNC Test {idx} ---\n"
            f"  Input: {row['current_input']}\n"
            f"  Expected: overall={row['expected_overall']}  key={row['expected_key']}\n"
            f"  Got:      overall={parsed.overall_classification}  key={predicted_key}\n"
            f"  Agent Response: {response}\n"
            f"  Time elapsed for test: {single_test_time:.2}\n"
            )
        except Exception as e:
            block = (
            f"--- SYNC Test {idx} ---\n"
            f"  Input: {row['current_input']}\n"
            f"  Expected: overall={row['expected_overall']}  key={row['expected_key']}\n"
            f"  Got:     RAISED EXCEPTION (LIKELY BAML PARSE ERROR)\n"
            f"  No Agent Response , No Time Recorded: "
            )
            

        with open(SCRIPT_DIR/"logs/latency_test.log", 'a') as f:
            f.write(block)

async def single_async(idx, row):
    async with sem:
        start_test = time.perf_counter()
        try:
            parsed = await b_async.ClassifyInput(row["current_input"], row["transcript"])
        except Exception as e:
            block = (
                f"--- asynchronous Test {idx} ---\n"
                f"  Input: {row['current_input']}\n"
                f"  Expected: overall={row['expected_overall']}  key={row['expected_key']}\n"
                f"  Got:     RAISED EXCEPTION (LIKELY BAML PARSE ERROR)\n"
                f"  No Agent Response , No Time Recorded.\n"
            )
            return block 
        
        if parsed.overall_classification == "Out_Of_Scope":
            predicted_key = "NotApplicable_NotApplicable"
            instruction = "Instruct that the users request was out of scope. Try to ask a clarifying question or tell them topics you can answer"
            response = await b_async.AnswerQuery(question=instruction, context="", transcript=row["transcript"]+f"\nUser: {row["current_input"]}", language="English")
                
        elif parsed.overall_classification == "End_Call":  
            predicted_key = "NotApplicable_NotApplicable"
            response = await b_async.AnswerQuery(question="Say a goodbye message to end the call", context="", transcript="", language="English")

        elif parsed.confidence <= 0.5 or parsed.group == "UnAnswerable" or parsed.subgroup == "NoSubgroup":
            predicted_key = "NotApplicable_NotApplicable"
            instruction = "Ask a clarifying question since it is not clear from the transcript what the user is asking for."
            response =  await b_async.AnswerQuery(question=instruction, context="", transcript=row["transcript"]+f"\nUser: {row["current_input"]}", language="English")
        #elif REQUEST USER AGENT CASE, ADD LATER:
        else: 
            # Normal processing
            context, predicted_key = query_university_context(parsed)
            response = await b_async.AnswerQuery(question=row["current_input"],context=context,transcript=row["transcript"], language="English")

        single_test_time = time.perf_counter() - start_test
        async_exp_times.append(single_test_time)

        block = (
        f"--- asynchronous Test {idx} ---\n"
        f"  Input: {row['current_input']}\n"
        f"  Expected: overall={row['expected_overall']}  key={row['expected_key']}\n"
        f"  Got:      overall={parsed.overall_classification}  key={predicted_key}\n"
        f"  Agent Response: {response}\n"
        f"  Time elapsed for test: {single_test_time:.2f}\n"
        )
        return block 

async def run_async_tests():
    tasks = []
    for idx, row in test_inputs.iterrows():
        tasks.append(single_async(idx, row)) 
        

    results = await asyncio.gather(*tasks)

    with open(SCRIPT_DIR/"logs/latency_test.log", 'a') as f:
        for r in results:
            f.write(r)



if __name__ == "__main__":
    with open(SCRIPT_DIR/"logs/latency_test.log", 'w') as f:
        f.write("START OF SYNCHRONOUS TESTS\n")
    start_all_sync = time.perf_counter()
    run_sync_tests()
    total_all_sync = time.perf_counter() - start_all_sync

    with open(SCRIPT_DIR/"logs/latency_test.log", 'a') as f:
        f.write("\n\nSTART OF ASYNC TESTS\n")

    start_all_as = time.perf_counter()
    asyncio.run(run_async_tests())
    total_all_as = time.perf_counter() - start_all_as


    # start creating summmary stats
    num_succesfull_sync = len(sync_exp_times)
    avg_sync = sum( exe_time for exe_time in sync_exp_times) / num_succesfull_sync
    min_sync = min(exe_time for exe_time in sync_exp_times)
    max_sync = max(exe_time for exe_time in sync_exp_times)
    range_sync = max_sync - min_sync

    num_succesfull_as = len(async_exp_times)
    avg_as = sum( exe_time for exe_time in async_exp_times) / num_succesfull_as
    min_as = min(exe_time for exe_time in async_exp_times)
    max_as = max(exe_time for exe_time in async_exp_times)
    range_as = max_as - min_as

    speedup = total_all_sync/total_all_as # is there error here? check log?

    summary = (
        "\n\n--- SUMMARY STATS FOR SYNC TESTS ---\n"
        f"Sync Tests Total Runtime: {total_all_sync:.2f}\n"
        f"Average Time of Single Test: {avg_sync:.2f}\n"
        f"MIN Time: {min_sync:.2f}, MAX Time: {max_sync:.2f}\n"
        f"Time Range: {range_sync:.2f}\n\n"
        "--- SUMMARY STATS FOR Asynchronous TESTS ---\n"
        f"ASYNC Tests Total Runtime: {total_all_as:.2f}\n"
        f"Average Time of Single Test: {avg_as:.2f}\n"
        f"MIN Time: {min_as:.2f}, MAX Time: {max_as:.2f}\n"
        f"Time Range: {range_as:.2f}\n\n"
        f"Speedup Factor of ASYNC version: {speedup:.2f}"
    )

    with open(SCRIPT_DIR/"logs/latency_test.log", 'a') as f:
        f.write(summary)

