from libs.utils.logger import init_component_logger
from ui.vdb_client import VDBClient
import streamlit as st
import time
import os

RAG_API_URL = os.getenv("RAG_API_URL", "http://localhost:8000")

@st.cache_resource
def get_vdb_client():
    return VDBClient(base_url=RAG_API_URL)

@st.cache_resource
def get_logger():
    _logger = init_component_logger("VDB_GUI")
    _logger.info("VDB 管理UI启动...")
    _logger.info(f"Using RAG_API_URL={RAG_API_URL}")
    return _logger

logger = get_logger()
vdb_client = get_vdb_client()

# 在脚本顶层初始化一个用于控制 file_uploader 的版本号
if "file_uploader_key" not in st.session_state:
    st.session_state["file_uploader_key"] = 0

def render_admin():
    st.set_page_config(page_title="法律知识库管理", layout="wide")
    st.header("⚖️ 知识库维护后台")

    tab1, tab2 = st.tabs(["📚 法律概览与删除", "📤 导入新语料"])

    with tab1:
        laws = vdb_client.get_law_list()
        if not laws:
            st.info("当前知识库为空")
        else:
            for law in laws:
                col1, col2 = st.columns([3, 1])
                col1.write(f"📖 {law}")
                # 使用 key 防止按钮冲突
                if col2.button(f"移除", key=f"del_{law}"):
                    result = False
                    with st.spinner(f"正在移除《{law}》..."):
                        try:
                            if vdb_client.delete_law(law):
                                result = True
                            else:
                                st.error(f"移除失败：后端未正常处理")
                        except Exception as e:
                            st.error(f"发生异常：{e}")
                    if result:
                        st.toast(f"已成功移除《{law}》")
                        time.sleep(1)
                        st.rerun()

    with tab2:
        st.subheader("上传法律条文 TXT 文件")
        st.caption("提示：文件名将自动作为法律名称，内容请按‘第X条’格式排版")
        uploaded_file = st.file_uploader(
            "选择文件",
            type=['txt'],
            key=f"uploader_{st.session_state['file_uploader_key']}"
        )

        if uploaded_file:
            file_content = uploaded_file.getvalue().decode('utf-8')

            if st.button("开始向量化导入", type="primary"):
                result = False
                with st.spinner("文件上传中，请稍候..."):
                    try:
                        if vdb_client.add_law(uploaded_file.name, file_content):
                            result = True
                            st.session_state["file_uploader_key"] += 1
                        else:
                            st.error(f"导入失败：后端未正常处理")
                    except Exception as e:
                        st.error(f"发生异常：{e}")
                if result:
                    st.toast(f"《{uploaded_file.name}》导入成功！")
                    time.sleep(1)
                    st.rerun()

# --- 4. 关键：启动入口 ---
if __name__ == "__main__":
    render_admin()
