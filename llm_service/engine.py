import logging
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chatglm_cpp

logger = logging.getLogger("LLM")

class ChatGLM:
    def __init__(self, path):
        try:
            self.pipeline = chatglm_cpp.Pipeline(path)
            logger.info("ChatGLM3-6B model loaded successfully.")
        except Exception as e:
            raise e

    def chat(self, text: str, history, do_sample, temperature, top_p, max_tokens):
        try:
            response = self.pipeline.chat(
                messages=[chatglm_cpp.ChatMessage(role="user", content=text)],
                max_length=max_tokens,
                do_sample=do_sample,
                top_p=top_p,
                temperature=temperature
            )
            return response.content, history
        except Exception as e:
            logger.error(f"Inference error: {e}")
            raise e
