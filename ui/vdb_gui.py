import time
import json

import streamlit as st

from shared.config import get_app_config, get_rag_config
from libs.utils.logger import init_component_logger
from ui.vdb_client import VDBClient

@st.cache_resource
def get_app_config_cached():
    return get_app_config()

@st.cache_resource
def get_rag_config_cached():
    return get_rag_config()

@st.cache_resource
def get_logger():
    return init_component_logger("VDB_GUI")

@st.cache_resource
def get_vdb_client():
    rag_config = get_rag_config_cached()
    url = "http://" + rag_config.host + ":" + str(rag_config.port)
    logger.info(f"op=vdb_client_load_start url={url}")
    vdb_client = VDBClient(base_url=url)
    logger.info(f"op=vdb_client_load_done")
    return vdb_client

rag_config = get_rag_config_cached()
app_config = get_app_config_cached()
logger = get_logger()
vdb_client = get_vdb_client()

# 在脚本顶层初始化一个用于控制 file_uploader 的版本号
if "file_uploader_key" not in st.session_state:
    st.session_state["file_uploader_key"] = 0

def render_admin():
    st.set_page_config(page_title="知识库管理", layout="wide")
    st.header("⚖️ 知识库维护后台")

    tab1, tab2 = st.tabs(["📚 文档概览与删除", "📤 导入新语料"])

    with tab1:
        docs = vdb_client.get_doc_list()
        if not docs:
            st.info("当前知识库为空")
        else:
            # 表头
            header_cols = st.columns([3, 1, 2, 1])
            header_cols[0].markdown("**📄 文件名**")
            header_cols[1].markdown("**📦 大小(KB)**")
            header_cols[2].markdown("**🕒 创建时间**")
            header_cols[3].markdown("**🗑 删除**")

            st.divider()

            for doc in docs:
                file_id = doc["file_id"]
                name = doc.get("filename")
                size = doc.get("size", 0)
                created_at = doc.get("created_at", "-")

                cols = st.columns([3, 1, 2, 1])
                cols[0].write(f"📄 {name}")
                cols[1].write(f"{size / 1024:.1f}")
                cols[2].write(created_at)

                if cols[3].button("删除", key=f"delete_{file_id}"):
                    with st.spinner(f"正在删除《{name}》..."):
                        try:
                            if vdb_client.delete_doc(file_id):
                                st.toast(f"已删除《{name}》")
                                time.sleep(0.8)
                                st.rerun()
                            else:
                                st.error(f"删除失败")

                        except Exception as e:
                            st.error(f"异常：{e}")

    with tab2:
        st.subheader("上传知识文档 TXT 文件")
        st.caption("提示：文件名将自动作为文档名称，内容请按‘第X条’格式排版")
        uploaded_file = st.file_uploader(
            "选择文件",
            type=app_config.supported_file_extensions,
            key=f"uploader_{st.session_state['file_uploader_key']}",
            max_upload_size=app_config.max_file_size_mb
        )

        if uploaded_file:
            file_content = uploaded_file.getvalue().decode('utf-8')

            if st.button("开始向量化导入", type="primary"):
                result = False
                with st.spinner("文件上传中，请稍候..."):
                    try:
                        if vdb_client.add_doc(uploaded_file.name, file_content):
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