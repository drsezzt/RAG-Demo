import requests
import logging

logger = logging.getLogger("VDB_GUI")

class VDBClient:
    def __init__(self, base_url):
        self.base_url = base_url

    def add_doc(self, doc_name, file_contnt):
        logger.info(
            "op=ui_add_doc_start "
            f"doc_name={doc_name}"
        )
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        try:
            response = requests.post(
                f"{self.base_url}/doc",
                json={
                    "name": doc_name,
                    "content": file_contnt,
                },
                headers=headers,
            )
            res_json = response.json()
            if res_json.get('status') != "ok":
                logger.error("Error: Failed to Add Doc")
                return False
        except Exception as e:
            raise Exception(f"Failed to communicate with VDB Service: {str(e)}")

        logger.info("op=ui_add_doc_done")
        return True

    def delete_doc(self, doc_name):
        logger.info(
            "op=ui_delete_doc_start "
            f"doc_name={doc_name}"
        )
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        try:
            response = requests.delete(
                f"{self.base_url}/doc/{doc_name}",
                headers=headers,
            )
            res_json = response.json()
            if res_json.get('status') != "ok":
                logger.error("Error: Failed to Delete Doc")
                return False
        except Exception as e:
            raise Exception(f"Failed to communicate with VDB Service: {str(e)}")

        logger.info("op=ui_delete_doc_done")
        return True

    def get_doc_list(self):
        logger.info("op=ui_list_doc_start")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        try:
            response = requests.get(
                f"{self.base_url}/doc",
                headers=headers,
            )
            res_json = response.json()
            docs = res_json.get("docs")
        except Exception as e:
            raise Exception(f"Failed to communicate with VDB Service: {str(e)}")

        logger.info(
            "op=ui_list_doc_done "
            f"doc_count={len(docs)}"
        )
        return docs
