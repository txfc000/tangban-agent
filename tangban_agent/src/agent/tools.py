# src/agent/tools.py
from langchain_core.tools import tool
from src.utils import db
import streamlit as st

# 注意：此函数不再作为工具直接暴露给 LLM，而是由 agent_graph 内部调用
def get_user_profile_internal(username: str) -> dict:
    """内部函数，直接根据用户名获取档案"""
    user_data = db.load_user_data(username)
    profile = user_data.get("profile", {})
    preferences = user_data.get("preferences", {})
    return {
        "profile": profile,
        "preferences": preferences
    }

# 以下工具函数保留，但只作为内部使用，不直接暴露给 LLM
@tool
def update_temp_blood_sugar(username: str, sugar_value: float) -> str:
    """
    临时记录用户本次的餐前血糖值，用于当前食谱生成会话。
    这个值不会被永久保存，只在本次对话中有效。
    参数 username: 用户名， sugar_value: 血糖值（mmol/L）
    """
    return f"已记录餐前血糖 {sugar_value} mmol/L（临时，仅本次有效）"

@tool
def update_temp_preferences(username: str, likes: str, dislikes: str) -> str:
    """
    临时更新用户本次对话中的特殊喜好/忌口（优先级高于永久库）。
    参数 username: 用户名， likes: 用户想吃的食物（逗号分隔）， dislikes: 用户不想吃的食物。
    """
    return f"已记录临时偏好：喜欢 {likes}，不喜欢 {dislikes}（仅本次有效）"

@tool
def generate_meal_plan(
    username: str,
    meal_type: str,
    special_need: str = "",
    temp_blood_sugar: float = None,
    temp_likes: str = None,
    temp_dislikes: str = None
) -> str:
    """
    根据用户档案、临时血糖值、临时偏好以及永久偏好，生成个性化食谱。
    这是最终生成食谱的工具，调用后将返回完整的食谱文本。
    参数：
        username: 用户名
        meal_type: 全天/早餐/午餐/晚餐
        special_need: 特殊需求文本（可选）
        temp_blood_sugar: 本次临时血糖（如果提供，覆盖档案中的血糖）
        temp_likes: 本次临时喜好（会与永久喜好合并，并优先使用）
        temp_dislikes: 本次临时忌口（会与永久忌口合并，并严格排除）
    """
    user_data = db.load_user_data(username)
    
    if temp_blood_sugar is not None:
        user_data["profile"]["glucose"] = temp_blood_sugar
    if temp_likes:
        temp_likes_list = [x.strip() for x in temp_likes.split(",") if x.strip()]
        existing_likes = user_data["preferences"].get("likes", [])
        user_data["preferences"]["likes"] = temp_likes_list + existing_likes
    if temp_dislikes:
        temp_dislikes_list = [x.strip() for x in temp_dislikes.split(",") if x.strip()]
        existing_dislikes = user_data["preferences"].get("dislikes", [])
        user_data["preferences"]["dislikes"] = existing_dislikes + temp_dislikes_list

    from src.agent import recipe_generator
    api_key = st.secrets.get("DEEPSEEK_API_KEY")
    recipe_text = recipe_generator.generate_recipe(
        api_key=api_key,
        user_data=user_data,
        meal_type=meal_type,
        special_need=special_need
    )
    return recipe_text
