from libs.utils.logger import init_component_logger
import streamlit as st
import requests
import os

RAG_API_URL = os.getenv("RAG_API_URL", "http://localhost:8000")

@st.cache_resource
def get_logger():
    _logger = init_component_logger("RAG_GUI")
    _logger.info("VDB 管理UI启动")
    _logger.info(f"Using RAG_API_URL={RAG_API_URL}")
    return _logger

logger = get_logger()

def render_admin():
    st.set_page_config(page_title="AI 法律助手", page_icon="⚖️")

    st.title("⚖️AI 法律智能咨询系统")
    st.markdown("---")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    with st.sidebar:
        st.header("系统状态")
        st.success("后端连接正常")
        st.info("当前模型：ChatGLM3-6B-Q5_1")
        if st.button("清除对话历史"):
            st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_input := st.chat_input("请描述您的法律问题..."):
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("🔍 正在检索法条并生成回复...")

            try:
                response = requests.post(
                    RAG_API_URL + "/chat",
                    json={"text": user_input},
                    timeout=60
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
