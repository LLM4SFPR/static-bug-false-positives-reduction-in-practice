import json

import openai

from tqdm import tqdm
import pdb

from openai import OpenAI
import time

MODEL_NAME = "deepseek"


def call_gpt(messages):
    try:
        model_name = "gpt-4o-mini"
        # model_name = "gpt-4o"
        client = openai.OpenAI(
            base_url="https://openkey.cloud/v1",
            api_key=''
        )
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            timeout=6000
        )
        return response.choices[0].message.content

    except Exception as e:
        print(f"Error calling GPT API: {e}")
        return f"Error calling GPT API: {e}"


def call_deepseek(messages):
    try:
        model_name = "deepseek-reasoner"  # DeepSeek-R1-0528
        client = openai.OpenAI(
            base_url="https://api.deepseek.com/v1",
            api_key=''
        )
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            timeout=6000
        )

        response_content = response.choices[0].message.content

        return response_content

    except Exception as e:
        print(f"Error calling Deepseek API: {e}")
        return f"Error calling Deepseek API: {e}"


def call_qwen(messages):
    try:
        model_name = "qwen3-235b-a22b"
        client = openai.OpenAI(
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key=''
        )
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            stream=False,
            extra_body={"enable_thinking": False},
            timeout=6000
        )
        return response.choices[0].message.content

    except Exception as e:
        print(f"Error calling qwen3 API: {e}")
        return f"Error calling qwen3 API: {e}"


def call_claude(messages):
    try:
        model_name = "claude-opus-4-20250514"
        client = openai.OpenAI(
            base_url="https://openkey.cloud/v1",
            api_key=''
        )
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            timeout=6000
        )
        return response.choices[0].message.content

    except Exception as e:
        print(f"Error calling claude API: {e}")
        return f"Error calling claude API: {e}"


def call_model(prompt):
    messages = [{"role": "user", "content": prompt}]
    if MODEL_NAME == "gpt":
        return call_gpt(messages)
    elif MODEL_NAME == "deepseek":
        return call_deepseek(messages)
    elif MODEL_NAME == "qwen":
        return call_qwen(messages)
    elif MODEL_NAME == "claude":
        return call_claude(messages)


system_prompt = ("You are an expert C/C++ programmer.\n# Task Description\n"
                 "The code snippet and the bug report will be provided to you for the purpose of examining "
                 "the presence of the bug within the code snippet. "
                 "Initially, you need to explain the behavior of the code. "
                 "Subsequently, you can determine whether the bug is a true positive or a false positive "
                 "based on the explanation.  "
                 "To conclude your answer, you will provide one of the following labels: "
                 "'@@@ real bug @@@', '@@@ false alarm @@@', or '@@@ unknown @@@'.\n")


def get_bug_report(var_name, loc_text, warning_type):
    bug_report_dict = {
        "DivideByZero": (f"{loc_text}\nAttempting to divide by {var_name}, which may be zero; "
                         f"ensure to validate its value before performing the operation."),
        "NullPointer": (f"{loc_text}\nValue {var_name} may be null; "
                        f"it should be checked before dereferencing."),
        "OutOfBound": (f"{loc_text}\nAccessing the index of array {var_name}, which may be out of bounds; "
                       "Please verify the index value before accessing the array.")
    }
    return bug_report_dict[warning_type]


def get_prompt(bug_report, code_snippet):
    prompt = f"""{system_prompt}# Bug Report\n{bug_report}\n\n# Code Snippet\n{code_snippet}\n"""
    return prompt


def get_final_answer(response):
    # 截取@@@ @@@之间的内容
    start = response.find("@@@")
    end = response.find("@@@", start + 1)
    return response[start + 4:end - 1]


def llm4sa(var_name, code_snippet, loc_text, warning_type):
    bug_report = get_bug_report(var_name, loc_text, warning_type)
    detect_result = None

    prompt = get_prompt(bug_report, code_snippet)
    response = call_model(prompt)
    final_answer = get_final_answer(response)

    if final_answer in ("real bug"):
        detect_result = True
    elif final_answer in ("false alarm"):
        detect_result = False
    result_item = {
        "bug_report": bug_report,
        "code_snippet": code_snippet,
        "warning_type": warning_type,
        "response": response,
        "detect_result": detect_result
    }
    return result_item


if __name__ == "__main__":
    # 记录开始时间
    start_time = time.time()

    run_type_list = [
        "DivideByZero-covers",
        "DivideByZero-not-covers",
        "DivideByZero-real-bug",
        "Nullpointer",
        "OutOfBound-covers",
        "OutOfBound-not-covers",
        "OutOfBound-real-bug"
    ]

    for run_type in run_type_list:
        print(f"run-type: {run_type}")
        # 结果字典
        result_list = []

        date = ""
        input_file = f"../data/{run_type}-Final.json"
        output_file = f"{date}/{date}-{run_type}-output-llm4sa-prompt.json"

        with open(input_file, 'r', encoding='utf-8') as file:
            items = json.load(file)
            for item in items:
                index = item['index']
                print(f"item: {item['index']}")
                code_snippet = item["code_snippet"]
                var_name = item["warning_target"]
                loc_text = item["loc_text"]
                warning_type = item["warning_type"]
                result = llm4sa(var_name, code_snippet, loc_text, warning_type)
                result["index"] = item["index"]
                result["label"] = item["label"]

                result_list.append(result)

        # 将结果写入到一个新的 JSON 文件
        with open(output_file, 'w', encoding='utf-8') as outfile:
            json.dump(result_list, outfile, ensure_ascii=False, indent=4)

    # 记录结束时间
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"[INFO] 程序运行时间: {elapsed_time:.4f} 秒")
