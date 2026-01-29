"""
LLM engine management.
"""

import time
import logging

from llm_service import chatglm_cpp

logger = logging.getLogger("LLM")

class ChatGLM:
    def __init__(self, path):
        try:
            logger.info(
                f"op=model_load_start "
                f"path={path}"
            )
            start = time.time()
            self.pipeline = chatglm_cpp.Pipeline(path)
            logger.info(
                f"op=model_load_done "
                f"path={path} "
                f"cost={time.time() - start:.2f}s "
            )
        except Exception as e:
            logger.error(
                "op=model_load_error "
                f"cost={time.time() - start:.2f}s "
                f"error={type(e).__name__}"
            )
            raise e

    def chat(
        self,
        text: str,
        history,
        *,
        req_id: str,
        user_id: str | None = None,
        do_sample: bool = False,
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: int = 2048,
    ):
        user_id = user_id or "anonymous"
        logger.info(
            "op=llm_start "
            f"req={req_id} "
            f"user={user_id} "
            f"text_len={len(text)} "
        )

        logger.debug(
            "op=llm_params "
            f"req={req_id} "
            f"user={user_id} "
            f"do_sample={do_sample} "
            f"temperature={temperature} "
            f"top_p={top_p} "
            f"max_tokens={max_tokens}"
        )

        t0 = time.time()
        try:
            response = self.pipeline.chat(
                messages=[chatglm_cpp.ChatMessage(role="user", content=text)],
                max_length=max_tokens,
                do_sample=do_sample,
                top_p=top_p,
                temperature=temperature
            )

            logger.info(
                "op=llm_success "
                f"req={req_id} "
                f"user={user_id} "
                f"time={time.time() - t0:.2f}s "
                f"len={len(response.content)}"
            )
            return response.content, history
        except Exception as e:
            logger.error(
                "op=llm_error "
                f"req={req_id} "
                f"user={user_id} "
                f"time={time.time() - t0:.2f}s "
                f"error={type(e).__name__}"
            )

            raise e
