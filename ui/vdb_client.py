import requests
import logging

logger = logging.getLogger("VDB_GUI")

class VDBClient:
    def __init__(self, base_url):
        self.base_url = base_url

    def add_law(self, file_name, file_contnt):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        try:
            response = requests.post(
                f"{self.base_url}/law",
                json={
                    "name": file_name,
                    "content": file_contnt,
                },
                headers=headers,
            )
            if response.status_code != 200:
                return False
            return True
        except Exception as e:
            raise Exception(f"Failed to communicate with VDB Service: {str(e)}")

    def delete_law(self, law_name):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        try:
            response = requests.delete(
                f"{self.base_url}/law/{law_name}",
                headers=headers,
            )
            res_json = response.json()
            if res_json.get('status') != "success":
                logger.error("Error: Failed to Delete Law")
                return False
            return True
        except Exception as e:
            raise Exception(f"Failed to communicate with VDB Service: {str(e)}")

    def get_law_list(self):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        try:
            response = requests.get(
                f"{self.base_url}/law",
                headers=headers,
            )
            res_json = response.json()
            return res_json.get("laws")
        except Exception as e:
            raise Exception(f"Failed to communicate with VDB Service: {str(e)}")
