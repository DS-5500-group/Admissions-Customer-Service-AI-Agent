import sys
from dotenv import load_dotenv
import asyncio
import pandas as pd
from pathlib import Path

from baml_client.async_client import b

# This gives you the directory the script lives in, regardless of where you run from
# need this to open and read the test .csv file in /eval
SCRIPT_DIR = Path(__file__).parent

# need to change back some code below realted to union vs flat
load_dotenv()

sem = asyncio.Semaphore(10)
failures = {"flat": {}, "union": {}}


async def run_test(idx, row, classify_fn, variant_name):
    async with sem:
        try:
            parsed = await classify_fn(row["current_input"], row["transcript"])
        except Exception as e:
            failures[variant_name][idx] = row["current_input"]
            return {
                "idx": idx,
                "variant": variant_name,
                "block": (
                    f"--- Test {idx} [{variant_name}] ---\n"
                    f"  Input: {row['current_input']}\n"
                    f"  Expected: overall={row['expected_overall']}  key={row['expected_key']}\n"
                    f"  Got:      ERROR (see the exceptions log file)\n"
                    f"  Overall CLassification: FAIL(ERROR)  "
                    f"  Key Classification: FAIL(ERROR)"
                ),
                "overall_pass": False,
                "key_pass": False,
                "question": row["current_input"],
                "error": True,
                "eror_block": (
                    f"--- Test {idx} [{variant_name}] ---\n"
                    f"  Input: {row['current_input']}\n"
                    f"  ERROR: {e}\n"
                ),
            }

        if variant_name == "union":
            parsed_dict = parsed.category.model_dump()
            group = list(parsed_dict.keys())[0]
            subgroup = str(list(parsed_dict.values())[0]).split(".")[-1]
            predicted_key = f"{group}_{subgroup}"
        else:
            predicted_key = parsed.group + "_" + parsed.subgroup

        matched_overall = parsed.overall_classification == row["expected_overall"] # .value before
        matched_key = predicted_key == row["expected_key"]

        block = (
            f"--- Test {idx} [{variant_name}] ---\n"
            f"  Input: {row['current_input']}\n"
            f"  Expected: overall={row['expected_overall']}  key={row['expected_key']}\n"
            f"  Got:      overall={parsed.overall_classification}  key={predicted_key}\n"
            f"  Confidence of Key Classification: {parsed.confidence}\n"
            f"  Clarification: {'Not Needed' if not parsed.clarification else parsed.clarification}\n"
            f"  Overall CLassification: {'PASS' if matched_overall else 'FAIL'}  "
            f"  Key Classification: {'PASS' if matched_key else 'FAIL'}\n"
        )

        # catch both cases, and if both happens, it won't be double count
        if not matched_overall:
            failures[variant_name][idx] = row["current_input"]

        if not matched_key:
            failures[variant_name][idx] = row["current_input"]



        return {
            "idx": idx,
            "variant": variant_name,
            "block": block,
            "overall_pass": matched_overall,
            "key_pass": matched_key,
            "question": row["current_input"],
            "error" : False,
        }


async def main():

    mode = sys.argv[1]
    if mode == "--easy":
        df = pd.read_csv(SCRIPT_DIR /"test_sets/test_classify_easy.csv") 
        exceptions_log = "logs/classify_flat_union_easy_exceptions.log"
        normal_log = "logs/classify_flat_union_easy.log"
    elif mode == "--hard":
        df = pd.read_csv(SCRIPT_DIR /"test_sets/test_classify_hard.csv")
        exceptions_log = "logs/classify_flat_union_hard_exceptions.log"
        normal_log = "logs/classify_flat_union_hard.log"
    else:
        print("Run either: python -m evals.test_classify_flat_union --easy OR: python -m evals.test_classify_flat_union --hard")
        return

    tasks = []
    for idx, row in df.iterrows():
        tasks.append(run_test(idx, row, b.ClassifyInput, "flat")) 
        tasks.append(run_test(idx, row, b.ClassifyInput_Union, "union"))

    results = await asyncio.gather(*tasks)

    with open(SCRIPT_DIR /exceptions_log, "w") as exf, open(SCRIPT_DIR /normal_log, "w") as f:
        for r in results:
            if r["error"]:
                exf.write(r["eror_block"] + "\n")

            f.write(r["block"] + "\n")

    print("Test results:")
    log_string = "Test results:"
    for variant in ("flat", "union"):
        variant_results = [r for r in results if r["variant"] == variant]
        total = len(variant_results)
        errors = sum(1 for r in variant_results if r["error"])
        overall_acc = sum(r["overall_pass"] for r in variant_results) / total
        key_acc = sum(r["key_pass"] for r in variant_results) / total
        
        print(f"\n{variant}:\n (Overall) Classifying Acc. :{overall_acc:.2%}\n  (Groups and SubGroups) Classifying Acc. :{key_acc:.2%}\n  Num. Exceptions:{errors}\n")
        log_string+=f"\n{variant}:\n (Overall) Classifying Acc. :{overall_acc:.2%}\n  (Groups and SubGroups) Classifying Acc. :{key_acc:.2%}\n  Num. Exceptions:{errors}\n"
        if failures[variant]:
            print(f"  Failed rows:")
            for k, v in failures[variant].items():
                print(f"Test: {k} Question: {v}")
                log_string+=f"Test: {k} Question: {v}\n"

    with open(SCRIPT_DIR /normal_log, "a") as f:
        f.write(log_string)
           


asyncio.run(main())