from openai import OpenAI


def recognize_food_with_ai(api_key, food_input):
    """
    严格识别食物名称：不接受错别字，必须完全匹配标准名称。
    返回: (成功标志, 识别结果, 提示信息)
    """
    if not food_input or not food_input.strip():
        return False, "", "输入内容为空，请重新输入"

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": """
你是一个严格的食物名称识别器。

【任务】
用户会输入一个词或短语，你需要判断它是否是一个准确、规范的具体食物名称。

【严格规则】
1. 如果输入是标准、准确的食物名称（如"鸡肉"、"西兰花"、"米饭"），返回该食物名称。
2. 如果输入包含错别字、谐音、简称（如"迷饭"、"jī肉"、"鸡"）、或表达不完整，统统视为无效，返回"识别失败"。
3. 不要进行任何联想、纠错或补充，只接受完全正确的书写形式。
4. 只返回食物名称本身或"识别失败"，不要输出其他内容。
"""},
                {"role": "user", "content": f"请严格识别：{food_input}"}
            ],
            temperature=0.1,
            max_tokens=20
        )
        result = response.choices[0].message.content.strip()

        if "识别失败" in result or len(result) > 20 or len(result) < 1:
            return False, "", "识别失败，请检查输入是否有错别字，或输入更具体的食物名称"
        return True, result, f"已识别：{result}"
    except Exception as e:
        return False, "", f"AI识别出错：{str(e)}"


def check_food_suitable_for_diabetes(api_key, food_name):
    """
    使用AI判断该食物是否适合糖尿病患者食用。
    返回: (是否适合, 原因说明)
    """
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": """
你是一位专业的内分泌科营养师，专门评估食物是否适合糖尿病患者。

【任务】
用户会输入一个食物名称，你需要判断该食物是否适合2型糖尿病患者食用。

【判断标准】
1. 如果该食物属于高升糖指数（高GI）、高糖、高精制碳水（如含糖饮料、甜点、白面包、白米饭等），则判定为"不适合"。
2. 如果该食物属于低GI、高纤维、高蛋白、健康脂肪等（如绿叶蔬菜、全谷物、瘦肉、鱼、豆制品等），则判定为"适合"。
3. 如果该食物是加工食品，需要根据其糖分和碳水含量判断。
4. 对于模糊不清或非食物的输入，判定为"不确定"。

【输出格式】
你必须严格按以下格式输出两行：
第一行：适合 / 不适合 / 不确定
第二行：简短的判断理由（20字以内）
"""},
                {"role": "user", "content": f"请判断：{food_name}"}
            ],
            temperature=0.3,
            max_tokens=100
        )
        result = response.choices[0].message.content.strip().split("\n")
        if len(result) >= 2:
            verdict = result[0].strip()
            reason = result[1].strip()
            if verdict == "适合":
                return True, reason
            elif verdict == "不适合":
                return False, reason
            else:
                return False, f"不确定是否适合，为安全起见不建议加入。AI反馈：{reason}"
        else:
            return False, "AI判断结果格式异常，请重试"
    except Exception as e:
        return False, f"AI判断出错：{str(e)}"