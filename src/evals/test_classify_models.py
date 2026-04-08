import sys
from dotenv import load_dotenv
import asyncio
import pandas as pd
from pathlib import Path

from baml_client.async_client import b

SCRIPT_DIR = Path(__file__).parent

load_dotenv()

sem = asyncio.Semaphore(10)

# Model names and corresponding BAML functions
MODELS = {
    "GPT4oMini": b.ClassifyInput_GPT4oMini,
    "Haiku": b.ClassifyInput_Haiku,
    "GeminiFlash": b.ClassifyInput_GeminiFlash,
    "Llama8B": b.ClassifyInput_Llama8B,
}

failures = {model: {} for model in MODELS}


async def run_test(idx, row, classify_fn, model_name):
    async with sem:
        try:
            parsed = await classify_fn(row["current_input"], row["transcript"])
        except Exception as e:
            failures[model_name][idx] = row["current_input"]
            return {
                "idx": idx,
                "model": model_name,
                "block": (
                    f"--- Test {idx} [{model_name}] ---\n"
                    f"  Input: {row['current_input']}\n"
                    f"  Expected: overall={row['expected_overall']}  key={row['expected_key']}\n"
                    f"  Got:      ERROR (see the exceptions log file)\n"
                    f"  Overall Classification: FAIL(ERROR)  "
                    f"  Key Classification: FAIL(ERROR)"
                ),
                "overall_pass": False,
                "key_pass": False,
                "question": row["current_input"],
                "error": True,
                "error_block": (
                    f"--- Test {idx} [{model_name}] ---\n"
                    f"  Input: {row['current_input']}\n"
                    f"  ERROR: {e}\n"
                ),
            }

        predicted_key = f"{parsed.group.value}_{parsed.subgroup.value}"

        matched_overall = parsed.overall_classification == row["expected_overall"]
        matched_key = predicted_key == row["expected_key"]

        block = (
            f"--- Test {idx} [{model_name}] ---\n"
            f"  Input: {row['current_input']}\n"
            f"  Expected: overall={row['expected_overall']}  key={row['expected_key']}\n"
            f"  Got:      overall={parsed.overall_classification}  key={predicted_key}\n"
            f"  Confidence of Key Classification: {parsed.confidence}\n"
            f"  Clarification: {'Not Needed' if not parsed.clarification else parsed.clarification}\n"
            f"  Overall Classification: {'PASS' if matched_overall else 'FAIL'}  "
            f"  Key Classification: {'PASS' if matched_key else 'FAIL'}\n"
        )

        if not matched_overall or not matched_key:
            failures[model_name][idx] = row["current_input"]

        return {
            "idx": idx,
            "model": model_name,
            "block": block,
            "overall_pass": matched_overall,
            "key_pass": matched_key,
            "question": row["current_input"],
            "error": False,
        }


async def main():
    if len(sys.argv) < 2:
        print("Run either: python -m evals.test_classify_models --easy OR: python -m evals.test_classify_models --hard")
        return

    mode = sys.argv[1]
    if mode == "--easy":
        df = pd.read_csv(SCRIPT_DIR / "test_sets/test_classify_easy.csv")
        #df = pd.read_csv(SCRIPT_DIR / "test_sets/classify_short.csv")
        log_suffix = "easy"
    elif mode == "--hard":
        df = pd.read_csv(SCRIPT_DIR / "test_sets/test_classify_hard.csv")
        #df = pd.read_csv(SCRIPT_DIR / "test_sets/classify_short.csv")

        log_suffix = "hard"
    else:
        print("Run either: python -m evals.test_classify_models --easy OR: python -m evals.test_classify_models --hard")
        return

    tasks = []
    for idx, row in df.iterrows():
        for model_name, classify_fn in MODELS.items():
            tasks.append(run_test(idx, row, classify_fn, model_name))

    results = await asyncio.gather(*tasks)

    # Write logs per model
    for model_name in MODELS:
        model_results = [r for r in results if r["model"] == model_name]

        exceptions_log = SCRIPT_DIR / f"logs/classify_{model_name}_{log_suffix}_exceptions.log"
        normal_log = SCRIPT_DIR / f"logs/classify_{model_name}_{log_suffix}.log"

        with open(exceptions_log, "w") as exf, open(normal_log, "w") as f:
            for r in model_results:
                if r["error"]:
                    exf.write(r["error_block"] + "\n")
                f.write(r["block"] + "\n")

    # Print and collect summary
    print("Test results:")
    summary_lines = ["Test results:"]

    for model_name in MODELS:
        model_results = [r for r in results if r["model"] == model_name]
        total = len(model_results)
        errors = sum(1 for r in model_results if r["error"])
        overall_acc = sum(r["overall_pass"] for r in model_results) / total
        key_acc = sum(r["key_pass"] for r in model_results) / total

        summary = (
            f"\n{model_name}:\n"
            f"  (Overall) Classifying Acc.: {overall_acc:.2%}\n"
            f"  (Groups and SubGroups) Classifying Acc.: {key_acc:.2%}\n"
            f"  Num. Exceptions: {errors}"
        )
        print(summary)
        summary_lines.append(summary)

        if failures[model_name]:
            print("  Failed rows:")
            summary_lines.append("  Failed rows:")
            for k, v in failures[model_name].items():
                line = f"    Test: {k} Question: {v}"
                print(line)
                summary_lines.append(line)

    # Append summary to each model's log file
    for model_name in MODELS:
        normal_log = SCRIPT_DIR / f"logs/classify_{model_name}_{log_suffix}.log"
        with open(normal_log, "a") as f:
            f.write("\n" + "\n".join(summary_lines))


asyncio.run(main())