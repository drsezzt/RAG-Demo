# 通信客户端
# 职责：封装对llm_service的requests请求，后续可支持调用云端API
import requests
import logging
from libs.protocols.llm_contract import GenerateRequest, GenerateResponse

logger = logging.getLogger("RAG_APP")

class LLMClient:
    def __init__(self, url):
        self.url = url
    def chat(self, prompt, **kwargs):
        request_data = GenerateRequest(
            text=prompt,
            **kwargs
        )

        payload = request_data.model_dump()

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        try:
            response = requests.post(
                self.url + "/generate",
                json=payload,
                headers=headers,
                timeout=60
            )
            response.raise_for_status()

            res_json = response.json()
            chat_res = GenerateResponse.model_validate(res_json)
            if chat_res.status == "ok":
                return chat_res.response
            else:
                raise Exception(f"LLM Service Error: {chat_res.response}")
        except Exception as e:
            raise Exception(f"Failed to communicate with LLM Service: {str(e)}")
