# src/agent/agent_graph.py
from typing import TypedDict, Annotated, List, Union
import operator
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    AIMessage, HumanMessage, ToolMessage
)
import streamlit as st
from src.agent.tools import (
    update_temp_blood_sugar,
    update_temp_preferences,
    generate_meal_plan,
    get_user_profile_internal  # 改为导入内部函数
)

class AgentState(TypedDict):
    messages: Annotated[List[Union[HumanMessage, AIMessage, ToolMessage]], operator.add]
    username: str
    meal_type: str
    special_need: str
    temp_blood_sugar: float
    temp_likes: str
    temp_dislikes: str
    iteration: int
    # 新增：标记是否已经获取过用户档案
    profile_fetched: bool

# 只暴露给 LLM 的工具（不包含 get_user_profile，因为我们在节点内部处理）
tools = [
    update_temp_blood_sugar,
    update_temp_preferences,
    generate_meal_plan
]

llm = ChatOpenAI(
    model="deepseek-chat",
    api_key=st.secrets.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1",
    temperature=0.7
)
llm_with_tools = llm.bind_tools(tools)

def agent_node(state: AgentState):
    messages = state["messages"]
    if state.get("iteration", 0) > 10:
        return {
            "messages": [AIMessage(content="抱歉，思考时间过长，请重新提问。")],
            "iteration": state["iteration"] + 1
        }
    
    # 构造系统提示，告知 Agent 用户信息已预加载
    profile = get_user_profile_internal(state["username"])
    profile_text = f"""
用户档案信息：
- 用户名：{state['username']}
- 身高：{profile['profile'].get('height', '未知')}cm
- 体重：{profile['profile'].get('weight', '未知')}kg
- 年龄：{profile['profile'].get('age', '未知')}岁
- 性别：{profile['profile'].get('gender', '未知')}
- 偏好：{', '.join(profile['preferences'].get('likes', [])) or '无'}
- 忌口：{', '.join(profile['preferences'].get('dislikes', [])) or '无'}
你已经拥有了用户的所有信息，不需要再向用户询问用户名、身高、体重等基础信息。
只需要在生成食谱前，向用户询问临时血糖值和临时偏好即可。
"""
    # 将系统提示插入到消息列表开头
    system_msg = AIMessage(content=profile_text)
    # 如果消息列表为空或第一条不是系统消息，插入系统消息
    if not messages or not isinstance(messages[0], AIMessage) or "用户档案信息" not in messages[0].content:
        messages_with_context = [system_msg] + messages
    else:
        messages_with_context = messages
    
    response = llm_with_tools.invoke(messages_with_context)
    return {"messages": [response], "iteration": state["iteration"] + 1}

def should_continue(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    else:
        return "end"

# 使用 ToolNode
tool_node = ToolNode(tools)

workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_node)
workflow.set_entry_point("agent")
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        "end": END
    }
)
workflow.add_edge("tools", "agent")
app = workflow.compile()
