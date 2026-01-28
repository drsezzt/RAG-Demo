FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY llm_service/requirements.txt .

RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip install --no-cache-dir -r requirements.txt

COPY llm_service/ /app/llm_service
COPY libs/ /app/libs

ARG TARGET=cpu
COPY llm_service/chatglm_cpp/native/${TARGET}/_C.cpython-310-x86_64-linux-gnu.so \
    /app/llm_service/chatglm_cpp/_C.cpython-310-x86_64-linux-gnu.so

EXPOSE 8001

CMD ["python3", "-m", "llm_service.main"]