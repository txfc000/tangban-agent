from openai import OpenAI


def generate_recipe(api_key, user_data, meal_type="全天", special_need=""):
    profile = user_data.get("profile", {})
    height = profile.get("height", 170)
    weight = profile.get("weight", 70)
    age = profile.get("age", 50)
    gender = profile.get("gender", "男")

    likes = ", ".join(user_data.get("preferences", {}).get("likes", [])) or "无特殊偏好"
    dislikes = ", ".join(user_data.get("preferences", {}).get("dislikes", [])) or "无"

    meal_instruction = {
        "全天": "请生成完整的每日三餐（早餐+午餐+晚餐）+ 一次加餐",
        "早餐": "请仅生成早餐食谱",
        "午餐": "请仅生成午餐食谱",
        "晚餐": "请仅生成晚餐食谱"
    }.get(meal_type, "请生成完整的每日三餐")

    special_instruction = ""
    if special_need and special_need.strip():
        special_instruction = f"\n【特殊需求】\n用户补充说明：{special_need}\n请根据这个需求调整食谱。"

    system_prompt = f"""
你是一名专业的内分泌科营养师，专门为2型糖尿病患者制定个性化饮食方案。

【患者基本信息】
- 性别：{gender}
- 年龄：{age}岁
- 身高：{height} cm
- 体重：{weight} kg
- 计算所得BMI：{weight / ((height / 100) ** 2):.1f}

【饮食偏好】
- 喜欢的食物：{likes}
- 不喜欢的食物：{dislikes}

【生成要求】
- 任务：{meal_instruction}
- 每餐需标注：热量(kcal)、碳水(g)、蛋白质(g)、脂肪(g)
- 优选低GI食材（燕麦、糙米、全麦、杂粮、绿叶蔬菜）
- 绝对不要包含用户不喜欢的食物
- 尽量融入用户喜欢的食物
{special_instruction}

【输出格式】
请用清晰的文字分段输出，每餐之间用分隔线隔开。
"""

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"请根据以上信息生成{meal_type}食谱。"}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"生成失败：{str(e)}"