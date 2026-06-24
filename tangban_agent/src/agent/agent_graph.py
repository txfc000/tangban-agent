# src/agent/agent_graph.py
from typing import TypedDict, Annotated, List, Union
import operator
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    AIMessage, HumanMessage, ToolMessage
)
import streamlit as st
from src.agent.tools import (
    get_user_profile,
    update_temp_blood_sugar,
    update_temp_preferences,
    generate_meal_plan
)

# 1. 定义状态结构
class AgentState(TypedDict):
    messages: Annotated[List[Union[HumanMessage, AIMessage, ToolMessage]], operator.add]
    username: str
    meal_type: str
    special_need: str
    temp_blood_sugar: float          # 临时血糖，初始为 None
    temp_likes: str                  # 临时喜好
    temp_dislikes: str               # 临时忌口
    iteration: int                   # 循环计数

# 2. 初始化工具列表
tools = [
    get_user_profile,
    update_temp_blood_sugar,
    update_temp_preferences,
    generate_meal_plan
]
tool_executor = ToolExecutor(tools)

# 3. 初始化 LLM（DeepSeek）
llm = ChatOpenAI(
    model="deepseek-chat",
    api_key=st.secrets.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1",
    temperature=0.7
)
llm_with_tools = llm.bind_tools(tools)

# 4. 定义节点函数
def agent_node(state: AgentState):
    """Agent 推理节点"""
    messages = state["messages"]
    if state.get("iteration", 0) > 10:
        return {
            "messages": [AIMessage(content="抱歉，思考时间过长，请重新提问。")],
            "iteration": state["iteration"] + 1
        }
    response = llm_with_tools.invoke(messages)
    return {"messages": [response], "iteration": state["iteration"] + 1}

def tool_node(state: AgentState):
    """工具执行节点"""
    messages = state["messages"]
    last_message = messages[-1]
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return {}
    results = []
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        # 执行工具
        tool_result = tool_executor.invoke({"name": tool_name, "args": tool_args})
        results.append(
            ToolMessage(
                content=str(tool_result),
                tool_call_id=tool_call["id"]
            )
        )
    return {"messages": results}

def should_continue(state: AgentState):
    """决定下一步"""
    messages = state["messages"]
    last_message = messages[-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    else:
        return "end"

# 5. 构建图
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