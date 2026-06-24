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
    get_user_profile,
    update_temp_blood_sugar,
    update_temp_preferences,
    generate_meal_plan
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

tools = [
    get_user_profile,
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
    response = llm_with_tools.invoke(messages)
    return {"messages": [response], "iteration": state["iteration"] + 1}

# 使用 ToolNode（新版 LangGraph 推荐）
tool_node = ToolNode(tools)

def should_continue(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    else:
        return "end"

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
