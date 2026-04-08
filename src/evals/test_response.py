import os 
from dotenv import load_dotenv
import asyncio
from pathlib import Path

import pandas as pd

from baml_client.async_client import b

from deepeval import evaluate
from deepeval.metrics import FaithfulnessMetric, AnswerRelevancyMetric
from deepeval.test_case import LLMTestCase
from deepeval.evaluate import AsyncConfig


os.environ["DEEPEVAL_ASYNC_TIMEOUT"] = "600"  # seconds


load_dotenv()

# This gives you the directory the script lives in, regardless of where you run from
# need this to open and read the test .csv file in /eval/test_sets
SCRIPT_DIR = Path(__file__).parent

sem = asyncio.Semaphore(10)

db = pd.read_csv("DB.csv")


def query_university_context(predicted_key:str) -> str:

    #predicted_key = parsed.group + "_" + parsed.subgroup
    try:
        context = db.loc[db["Lookup_Key"]==predicted_key, "Information Text"].item() # .item() should return the single entry, "scalor" value
        return context, predicted_key
    except ValueError: # 0 or multiple matches for when Lookup_Key==predicted_key, .item() only allows for single row
        return "", predicted_key

async def build_single_test(idx, row):
    async with sem:

        # Normal processing
        context, _ = query_university_context(row["expected_key"])
        response = await b.AnswerQuery(question=row["current_input"],context=context,transcript=row["transcript"], language="English")

        tc = LLMTestCase(
            input=row["current_input"],              
            actual_output=response,                  
            retrieval_context=[context],             
            expected_output=None                     
        )

        return tc



async def create_test_cases():
    test_input = pd.read_csv(SCRIPT_DIR/"test_sets/test_classify_easy.csv").iloc[50:100]
    #test_input = pd.read_csv(SCRIPT_DIR/"test_sets/classify_short.csv")
    
    tasks = []
    for idx, row in test_input.iterrows():
        tasks.append(build_single_test(idx, row))
        
    test_cases = await asyncio.gather(*tasks)

    return test_cases

if __name__ == "__main__":

    test_cases = asyncio.run(create_test_cases())

    # specifically measures whether the response is grounded in the provided context
    faithfulness = FaithfulnessMetric(model="gpt-4o", threshold=0.7) 
    
    #check that the response actually addresses the question asked, since a response can be faithful to the context but answer the wrong question
    relevancy = AnswerRelevancyMetric(model="gpt-4o", threshold=0.7)

    results = evaluate(
        test_cases, 
        metrics=[faithfulness, relevancy], 
        async_config=AsyncConfig(run_async=True, max_concurrent=3, throttle_value=10) # do not overwhelm by sending too many concurrent: now it is almost sequential (sync) 
        ) 


    with open(SCRIPT_DIR/"logs/answer_eval.log", "w") as f:
        for r in results.test_results:
            f.write(f"Input: {r.input}\n")
            f.write(f"Output: {r.actual_output}\n")
            f.write(f"Pass: {r.success}\n")
            for m in r.metrics_data: # for the two metrics above
                f.write(f"  Metric: {m.name}  Score: {m.score}  Pass: {m.success}\n")
                f.write(f"  Reason: {m.reason}\n")
                f.write(f"  Cost: ${m.evaluation_cost:.4f}\n")
                if m.error:
                    f.write(f"  Error: {m.error}\n")
            f.write("\n")

        # Summary at the end
        total_cost = sum(
            m.evaluation_cost for r in results.test_results for m in r.metrics_data
        )
        total_pass = sum(r.success for r in results.test_results)
        total = len(results.test_results)
        f.write(f"--- SUMMARY ---\n")
        f.write(f"Passed: {total_pass}/{total} ({total_pass/total:.2%})\n")
        f.write(f"Total eval cost: ${total_cost:.4f}\n")