import streamlit as st
from src.utils import auth, db, preference_ai
from src.agent import recipe_generator
from src.agent.agent_graph import app as agent_app
from langchain_core.messages import HumanMessage, AIMessage

DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]

st.set_page_config(page_title="🍬 糖伴 · 控糖助手", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

# ----- 登录/注册（保持不变）-----
if not st.session_state.logged_in:
    st.title("🍬 糖伴 — 2型糖尿病AI食谱助手")
    st.caption("专属您的智能控糖管家")
    tab1, tab2 = st.tabs(["登录", "注册"])
    with tab1:
        with st.form("login_form"):
            username = st.text_input("用户名")
            password = st.text_input("密码", type="password")
            if st.form_submit_button("登录"):
                ok, msg = auth.login(username, password)
                if ok:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error(msg)
    with tab2:
        with st.form("register_form"):
            new_user = st.text_input("设置用户名")
            new_pass = st.text_input("设置密码", type="password")
            confirm = st.text_input("确认密码", type="password")
            if st.form_submit_button("注册"):
                if new_pass != confirm:
                    st.error("两次密码不一致")
                elif len(new_user) < 2:
                    st.error("用户名至少2个字符")
                else:
                    ok, msg = auth.register(new_user, new_pass)
                    if ok:
                        st.success("注册成功！请登录")
                    else:
                        st.error(msg)
    st.stop()

username = st.session_state.username
user_data = db.load_user_data(username)

profile = user_data.get("profile", {})
if not profile.get("height") or not profile.get("weight") or not profile.get("age") or not profile.get("gender"):
    st.title("📝 欢迎首次使用，请填写个人基本信息")
    with st.form("profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            height = st.number_input("身高 (cm)", min_value=100, max_value=220, value=170)
            age = st.number_input("年龄", min_value=10, max_value=120, value=50)
        with col2:
            weight = st.number_input("体重 (kg)", min_value=30, max_value=200, value=70)
            gender = st.selectbox("性别", ["男", "女"])
        if st.form_submit_button("保存并进入"):
            user_data["profile"] = {"height": height, "weight": weight, "age": age, "gender": gender}
            db.save_user_data(username, user_data)
            st.rerun()
    st.stop()

# ----- 侧边栏 -----
with st.sidebar:
    st.header(f"👋 {username}")
    st.divider()
    st.subheader("📊 我的数据")
    st.metric("身高", f"{profile['height']} cm")
    st.metric("体重", f"{profile['weight']} kg")
    st.metric("年龄", f"{profile['age']} 岁")
    st.metric("性别", profile['gender'])
    bmi = profile['weight'] / ((profile['height'] / 100) ** 2)
    st.metric("BMI", f"{bmi:.1f}")
    st.divider()
    if st.button("🚪 退出登录"):
        st.session_state.clear()
        st.rerun()

st.title("🍬 糖伴 · 智能控糖助手")

with st.expander("✏️ 编辑个人数据（身高、体重、年龄、性别）", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        new_height = st.number_input("身高 (cm)", min_value=100, max_value=220, value=profile['height'])
        new_age = st.number_input("年龄", min_value=10, max_value=120, value=profile['age'])
    with col2:
        new_weight = st.number_input("体重 (kg)", min_value=30, max_value=200, value=profile['weight'])
        new_gender = st.selectbox("性别", ["男", "女"], index=0 if profile['gender'] == "男" else 1)
    if st.button("💾 保存个人数据"):
        user_data["profile"] = {"height": new_height, "weight": new_weight, "age": new_age, "gender": new_gender}
        db.save_user_data(username, user_data)
        st.success("✅ 个人数据已更新！")
        st.rerun()

tab1, tab2, tab3 = st.tabs(["📅 生成食谱", "🎯 个性化设置", "💬 AI对话"])

# ================== 食谱生成 ==================
with tab1:
    meal_type = st.radio("选择餐次", ["全天食谱", "早餐", "午餐", "晚餐"], horizontal=True)
    meal_map = {"全天食谱": "全天", "早餐": "早餐", "午餐": "午餐", "晚餐": "晚餐"}

    st.divider()
    gen_method = st.radio("生成方式", [
        "直接生成",
        "输入特殊需求后生成",
        "🤖 智能生成（Agent会主动追问）"
    ], horizontal=True)
    special_need = ""
    if gen_method == "输入特殊需求后生成":
        special_need = st.text_area("请输入您的特殊情况（如：我刚散步回来）", height=80)
        st.caption("💡 特殊需求会被传递给AI，食谱会根据您的描述做调整")

    # ---- 按钮 ----
    if st.button("🚀 生成食谱", type="primary", use_container_width=True):
        if gen_method in ["直接生成", "输入特殊需求后生成"]:
            with st.spinner("🧠 AI正在为您定制专属食谱..."):
                recipe = recipe_generator.generate_recipe(
                    DEEPSEEK_API_KEY,
                    user_data,
                    meal_map[meal_type],
                    special_need
                )
                user_data.setdefault("recipes", []).append(f"【{meal_type}】\n{recipe}")
                db.save_user_data(username, user_data)
                st.success("✅ 食谱生成完成！")
                st.markdown(recipe)
        else:
            # 智能生成
            if "agent_messages" not in st.session_state:
                st.session_state.agent_messages = []
            if not st.session_state.agent_messages:
                user_query = f"请帮我生成{meal_type}食谱。"
                if special_need:
                    user_query += f" 特殊需求：{special_need}"
                st.session_state.agent_messages.append(HumanMessage(content=user_query))
                initial_state = {
                    "messages": st.session_state.agent_messages.copy(),
                    "username": username,
                    "meal_type": meal_map[meal_type],
                    "special_need": special_need,
                    "temp_blood_sugar": None,
                    "temp_likes": None,
                    "temp_dislikes": None,
                    "iteration": 0
                }
                final_state = agent_app.invoke(initial_state)
                st.session_state.agent_messages = final_state["messages"]
            st.rerun()

    # ---- 智能生成对话区域（永远显示输入框） ----
    if gen_method == "🤖 智能生成（Agent会主动追问）":
        st.divider()
        st.subheader("💬 智能生成对话")

        # 显示历史消息
        if "agent_messages" in st.session_state and st.session_state.agent_messages:
            for msg in st.session_state.agent_messages:
                if isinstance(msg, HumanMessage):
                    with st.chat_message("user"):
                        st.write(msg.content)
                elif isinstance(msg, AIMessage):
                    with st.chat_message("assistant"):
                        st.write(msg.content)
        else:
            st.info("点击“生成食谱”按钮开始智能对话")

        # ---------- 输入框：无条件显示 ----------
        # 判断是否已生成完整食谱（仅供提示，不影响输入框显示）
        last_msg = st.session_state.agent_messages[-1] if "agent_messages" in st.session_state and st.session_state.agent_messages else None
        is_finished = False
        if isinstance(last_msg, AIMessage) and len(last_msg.content) > 200 and ("食谱" in last_msg.content or "热量" in last_msg.content):
            is_finished = True

        # 输入框永远显示
        reply = st.chat_input("请输入您的回答..." if not is_finished else "食谱已生成，如需重新生成请再次点击按钮")
        if reply:
            st.session_state.agent_messages.append(HumanMessage(content=reply))
            initial_state = {
                "messages": st.session_state.agent_messages,
                "username": username,
                "meal_type": meal_map[meal_type],
                "special_need": special_need,
                "temp_blood_sugar": None,
                "temp_likes": None,
                "temp_dislikes": None,
                "iteration": 0
            }
            final_state = agent_app.invoke(initial_state)
            st.session_state.agent_messages = final_state["messages"]
            st.rerun()

        if is_finished:
            st.success("✅ 食谱已生成，您可以在上方查看。如需重新生成，请再次点击“生成食谱”按钮。")

    # ---- 历史食谱 ----
    with st.expander("📚 历史食谱记录"):
        if user_data.get("recipes"):
            for i, r in enumerate(reversed(user_data["recipes"])):
                st.markdown(f"**第 {len(user_data['recipes']) - i} 次**")
                st.markdown(r)
                st.divider()
        else:
            st.info("还没有生成过食谱")

# ========== 个性化设置 ==========
# （完全保留，与原代码相同，此处省略，请从之前的代码中复制）
# 注意：你之前的个性化设置代码很长，我为了简洁省略了，但实际你必须保留它。
# 你可以在替换时把之前的个性化设置和AI对话部分原样粘贴回来。
