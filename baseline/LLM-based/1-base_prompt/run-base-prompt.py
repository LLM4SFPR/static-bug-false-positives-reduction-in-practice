import json

import openai
import requests
import time
import re

from openai import OpenAI


def get_base_prompt(code_snippet):
    base_prompt = f"""Is this code vulnerable? Answer in YES or NO.
        ### Code Snippet:{code_snippet}
        """
    return base_prompt


def get_summary_prompt(last_response):
    summary_prompt = f"""Please analyze whether your last response {last_response} means YES or NO according to the message of this conversation. 
    You are only allowed to return YES or NO, and no other content, otherwise it will cause serious errors later.
    You are only allowed to summarize, not to change the result of the last answer.
    """
    return summary_prompt


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


def call_model(messages):
    if MODEL_NAME == "gpt":
        return call_gpt(messages)
    elif MODEL_NAME == "deepseek":
        return call_deepseek(messages)
    elif MODEL_NAME == "qwen":
        return call_qwen(messages)
    elif MODEL_NAME == "claude":
        return call_claude(messages)


def process_case(code_snippet):
    # 这部分对话记录
    messages = []
    # 结果
    result = {}

    # 正常检测的prompt
    prompt = get_base_prompt(code_snippet)
    # 大模型判断：该代码是否符合规则
    messages.append({"role": "user", "content": prompt})
    response = call_model(messages)
    messages.append({"role": "assistant", "content": response})

    # 提取结果：Yes 或 No
    if response in ("Yes", "YES", "yes"):  # 大模型返回YES：real bug
        result = {
            "code_snippet": code_snippet,
            "messages": messages,
            "detect_result": True
        }
    elif response in ("No", "NO", "no"):  # 大模型返回NO：误报
        result = {
            "code_snippet": code_snippet,
            "messages": messages,
            "detect_result": False
        }
    else:  # 返回格式有问题
        try_count = 0  # 最多尝试3次，超过3次则默认No，继续判断下一条
        while (response not in ["Yes", "YES", "yes", "No", "NO", "no"]) and (try_count < 3):
            summary_prompt = get_summary_prompt(response)
            messages.append({"role": "user", "content": summary_prompt})
            summary_response = call_gpt(messages)
            messages.append({"role": "assistant", "content": summary_response})
            # 提取结果：Yes 或 No
            if summary_response in ("Yes", "YES", "yes"):  # 大模型返回YES：real bug
                result = {
                    "code_snippet": code_snippet,
                    "messages": messages,
                    "detect_result": True
                }
                return result
            elif summary_response in ("No", "NO", "no"):  # 大模型返回NO：误报
                result = {
                    "code_snippet": code_snippet,
                    "messages": messages,
                    "detect_result": False
                }
                return result
            try_count += 1
        # 重试3遍依然格式错误
        result = {
            "code_snippet": code_snippet,
            "messages": messages,
            "detect_result": None
        }

    return result


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
        output_file = f"{date}/{date}-{run_type}-output-base-prompt.json"

        with open(input_file, 'r', encoding='utf-8') as file:
            items = json.load(file)
            for item in items:
                index = item['index']
                print(f"item: {item['index']}")
                code_snippet = item["code_snippet"]
                result = process_case(code_snippet)
                result["index"] = item["index"]
                result["warning_type"] = item["warning_type"]
                result["label"] = item["label"]

                result_list.append(result)

        # 将结果写入到一个新的 JSON 文件
        with open(output_file, 'w', encoding='utf-8') as outfile:
            json.dump(result_list, outfile, ensure_ascii=False, indent=4)

    # 记录结束时间
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"[INFO] 程序运行时间: {elapsed_time:.4f} 秒")
