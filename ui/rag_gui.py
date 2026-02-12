import requests

import streamlit as st

from shared.config import (
    get_ui_config,
    get_rag_config,
    get_llm_config
)
from libs.utils.logger import init_component_logger

@st.cache_resource
def get_ui_config_cached():
    return get_ui_config()

@st.cache_resource
def get_rag_config_cached():
    return get_rag_config()

@st.cache_resource
def get_llm_config_cached():
    return get_llm_config()

@st.cache_resource
def get_logger():
    return init_component_logger("RAG_GUI")

ui_config = get_ui_config_cached()
rag_config = get_rag_config_cached()
llm_config = get_llm_config_cached()
logger = get_logger()

def render_admin():
    st.set_page_config(page_title="AI 知识助手", page_icon="⚖️")

    st.title("⚖️AI 智能知识问答系统")
    st.markdown("---")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    with st.sidebar:
        st.header("系统状态")
        st.success("后端连接正常")
        st.info("当前模型：" + llm_config.models[0].name)
        if st.button("清除对话历史"):
            st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_input := st.chat_input("请描述您的问题..."):
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        url = "http://" + rag_config.host + ":" + str(rag_config.port)
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("🔍 正在检索知识库并生成回复...")

            try:
                response = requests.post(
                    url + rag_config.endpoint,
                    json={"text": user_input},
                    timeout=ui_config.timeout
                )

                if response.status_code == 200:
                    full_res = response.json()
                    answer = full_res.get("response", "未收到有效回复")
                    message_placeholder.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                else:
                    message_placeholder.error(f"后端报错: {response.status_code}")
            except Exception as e:
                message_placeholder.error(f"连接失败: {str(e)}")

# --- 4. 关键：启动入口 ---
if __name__ == "__main__":
    render_admin()