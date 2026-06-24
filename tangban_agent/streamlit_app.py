import streamlit as st
from src.utils import auth, db, preference_ai
from src.agent import recipe_generator
from src.agent.agent_graph import app as agent_app
from langchain_core.messages import HumanMessage, AIMessage

# ==================== 从 st.secrets 读取 DeepSeek API Key ====================
DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]
# =============================================================================

st.set_page_config(page_title="🍬 糖伴 · 控糖助手", layout="wide")

# ---------- 初始化 ----------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

# ---------- 登录/注册 ----------
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

# ---------- 加载用户数据 ----------
username = st.session_state.username
user_data = db.load_user_data(username)

# ---------- 首次登录强制填写个人资料 ----------
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

# ---------- 侧边栏（只展示数据） ----------
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

# ---------- 主界面 ----------
st.title("🍬 糖伴 · 智能控糖助手")

# ---- 编辑个人资料（默认展开） ----
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

# ---- 三大功能标签页 ----
tab1, tab2, tab3 = st.tabs(["📅 生成食谱", "🎯 个性化设置", "💬 AI对话"])

# ========== 食谱生成 ==========
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

    # ---------- 生成按钮 ----------
    if st.button("🚀 生成食谱", type="primary", use_container_width=True):
        # ----- 原有两种方式（直接生成 / 特殊需求） -----
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

        # ----- 新增：智能生成（Agent） -----
        else:
            # 初始化消息历史（用于展示对话）
            if "agent_messages" not in st.session_state:
                st.session_state.agent_messages = []
            # 用户发起请求
            user_query = f"请帮我生成{meal_type}食谱。"
            if special_need:
                user_query += f" 特殊需求：{special_need}"
            st.session_state.agent_messages.append(HumanMessage(content=user_query))

            # 构建初始状态
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
            # 运行 Agent 图
            final_state = agent_app.invoke(initial_state)
            st.session_state.agent_messages = final_state["messages"]
            st.rerun()

    # ---------- 显示智能生成的对话历史 ----------
    if "agent_messages" in st.session_state and st.session_state.agent_messages:
        st.divider()
        st.subheader("💬 智能生成对话")
        for msg in st.session_state.agent_messages:
            if isinstance(msg, HumanMessage):
                with st.chat_message("user"):
                    st.write(msg.content)
            elif isinstance(msg, AIMessage):
                with st.chat_message("assistant"):
                    st.write(msg.content)
        st.divider()

    # ---------- 智能生成时的用户输入框（用于回答追问） ----------
    if "agent_messages" in st.session_state and st.session_state.agent_messages:
        # 简单判断：如果最后一条消息是 AI 的追问（包含问号）
        last_msg = st.session_state.agent_messages[-1]
        if isinstance(last_msg, AIMessage) and "?" in last_msg.content:
            reply = st.chat_input("请输入您的回答...")
            if reply:
                st.session_state.agent_messages.append(HumanMessage(content=reply))
                # 重新运行 Agent 图
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

    # ---------- 历史食谱记录 ----------
    with st.expander("📚 历史食谱记录"):
        if user_data.get("recipes"):
            for i, r in enumerate(reversed(user_data["recipes"])):
                st.markdown(f"**第 {len(user_data['recipes']) - i} 次**")
                st.markdown(r)
                st.divider()
        else:
            st.info("还没有生成过食谱")

# ========== 个性化设置（已删除“清空输入”按钮） ==========
with tab2:
    sub_tab1, sub_tab2 = st.tabs(["❤️ 喜好设置", "🚫 忌口设置"])

    with sub_tab1:
        st.subheader("添加喜欢的食物")
        like_input = st.text_input("输入一个食物名称（必须准确，无错别字）", key="like_input", placeholder="如：鸡肉")
        if st.button("✅ 确认添加（喜好）"):
            if like_input and like_input.strip():
                success, result, msg = preference_ai.recognize_food_with_ai(
                    DEEPSEEK_API_KEY, like_input
                )
                if not success:
                    st.error(msg)
                else:
                    suitable, reason = preference_ai.check_food_suitable_for_diabetes(
                        DEEPSEEK_API_KEY, result
                    )
                    if not suitable:
                        st.error(f"❌ {reason}，不能加入喜好库")
                    else:
                        if result not in user_data["preferences"]["likes"]:
                            user_data["preferences"]["likes"].append(result)
                            db.save_user_data(username, user_data)
                            st.success(f"✅ 已添加「{result}」到喜好库（AI判定：{reason}）")
                            st.rerun()
                        else:
                            st.info(f"「{result}」已在喜好库中")
            else:
                st.warning("请输入食物名称")

        st.divider()
        st.subheader("📋 我的喜好库")
        likes = user_data["preferences"].get("likes", [])
        if "manage_likes" not in st.session_state:
            st.session_state.manage_likes = False
        if "selected_likes" not in st.session_state:
            st.session_state.selected_likes = {}

        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("管理" if not st.session_state.manage_likes else "取消管理"):
                st.session_state.manage_likes = not st.session_state.manage_likes
                if not st.session_state.manage_likes:
                    st.session_state.selected_likes = {}
                st.rerun()

        if likes:
            if st.session_state.manage_likes:
                st.write("勾选要删除的词，然后点击下方的「删除选中」")
                for idx, item in enumerate(likes):
                    key = f"like_{idx}"
                    if key not in st.session_state.selected_likes:
                        st.session_state.selected_likes[key] = False
                    checked = st.checkbox(item, key=key, value=st.session_state.selected_likes[key])
                    st.session_state.selected_likes[key] = checked
                if st.button("🗑️ 删除选中", type="primary"):
                    to_delete = []
                    for idx, item in enumerate(likes):
                        key = f"like_{idx}"
                        if st.session_state.selected_likes.get(key, False):
                            to_delete.append(idx)
                    if to_delete:
                        for idx in sorted(to_delete, reverse=True):
                            del likes[idx]
                        user_data["preferences"]["likes"] = likes
                        db.save_user_data(username, user_data)
                        st.session_state.selected_likes = {}
                        st.session_state.manage_likes = False
                        st.success(f"已删除 {len(to_delete)} 项")
                        st.rerun()
                    else:
                        st.warning("请至少勾选一项")
            else:
                for item in likes:
                    st.write(f"• {item}")
        else:
            st.info("喜好库为空，请添加喜欢的食物")

    with sub_tab2:
        st.subheader("添加不喜欢的食物")
        dislike_input = st.text_input("输入一个食物名称（必须准确，无错别字）", key="dislike_input", placeholder="如：苦瓜")
        if st.button("✅ 确认添加（忌口）"):
            if dislike_input and dislike_input.strip():
                success, result, msg = preference_ai.recognize_food_with_ai(
                    DEEPSEEK_API_KEY, dislike_input
                )
                if not success:
                    st.error(msg)
                else:
                    if result not in user_data["preferences"]["dislikes"]:
                        user_data["preferences"]["dislikes"].append(result)
                        db.save_user_data(username, user_data)
                        st.success(f"✅ 已添加「{result}」到忌口库")
                        st.rerun()
                    else:
                        st.info(f"「{result}」已在忌口库中")
            else:
                st.warning("请输入食物名称")

        st.divider()
        st.subheader("📋 我的忌口库")
        dislikes = user_data["preferences"].get("dislikes", [])
        if "manage_dislikes" not in st.session_state:
            st.session_state.manage_dislikes = False
        if "selected_dislikes" not in st.session_state:
            st.session_state.selected_dislikes = {}

        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("管理" if not st.session_state.manage_dislikes else "取消管理", key="manage_dislikes_btn"):
                st.session_state.manage_dislikes = not st.session_state.manage_dislikes
                if not st.session_state.manage_dislikes:
                    st.session_state.selected_dislikes = {}
                st.rerun()

        if dislikes:
            if st.session_state.manage_dislikes:
                st.write("勾选要删除的词，然后点击下方的「删除选中」")
                for idx, item in enumerate(dislikes):
                    key = f"dislike_{idx}"
                    if key not in st.session_state.selected_dislikes:
                        st.session_state.selected_dislikes[key] = False
                    checked = st.checkbox(item, key=key, value=st.session_state.selected_dislikes[key])
                    st.session_state.selected_dislikes[key] = checked
                if st.button("🗑️ 删除选中", type="primary", key="del_dislikes"):
                    to_delete = []
                    for idx, item in enumerate(dislikes):
                        key = f"dislike_{idx}"
                        if st.session_state.selected_dislikes.get(key, False):
                            to_delete.append(idx)
                    if to_delete:
                        for idx in sorted(to_delete, reverse=True):
                            del dislikes[idx]
                        user_data["preferences"]["dislikes"] = dislikes
                        db.save_user_data(username, user_data)
                        st.session_state.selected_dislikes = {}
                        st.session_state.manage_dislikes = False
                        st.success(f"已删除 {len(to_delete)} 项")
                        st.rerun()
                    else:
                        st.warning("请至少勾选一项")
            else:
                for item in dislikes:
                    st.write(f"• {item}")
        else:
            st.info("忌口库为空，请添加不喜欢的食物")

# ========== AI对话 ==========
with tab3:
    st.subheader("💬 与智能体自由对话")
    st.caption("您可以咨询任何糖尿病相关的问题，智能体会结合您的个人数据回答")

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = user_data.get("chat_history", [])

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("请输入您的问题..."):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.chat_messages.append({"role": "user", "content": prompt})

        system_prompt = f"""
你是一名专业的内分泌科医生和糖尿病管理助手。

【患者信息】
- 性别：{profile.get('gender', '未知')}
- 年龄：{profile.get('age', '未知')}岁
- 身高：{profile.get('height', '未知')}cm
- 体重：{profile.get('weight', '未知')}kg
- BMI：{profile['weight'] / ((profile['height'] / 100) ** 2):.1f}

【饮食偏好】
- 喜欢的食物：{', '.join(user_data['preferences'].get('likes', [])) or '无'}
- 不喜欢的食物：{', '.join(user_data['preferences'].get('dislikes', [])) or '无'}

【规则】
1. 回答要基于糖尿病医学常识，具体、可执行
2. 如果用户问到饮食建议，请结合其个人数据回答
3. 不要给出超出你知识范围的医疗诊断
"""
        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url="https://api.deepseek.com"
            )
            messages = [{"role": "system", "content": system_prompt}]
            for m in st.session_state.chat_messages[-10:]:
                messages.append(m)

            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            reply = response.choices[0].message.content

            with st.chat_message("assistant"):
                st.markdown(reply)
            st.session_state.chat_messages.append({"role": "assistant", "content": reply})

            user_data["chat_history"] = st.session_state.chat_messages
            db.save_user_data(username, user_data)

        except Exception as e:
            st.error(f"对话出错：{e}")