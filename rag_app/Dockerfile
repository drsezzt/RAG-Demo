FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY rag_app/requirements.txt .

RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip install --no-cache-dir -r requirements.txt

# 如果 llm_service 依赖 libs
COPY rag_app/ /app/rag_app
COPY libs/ /app/libs

EXPOSE 8000

CMD ["python3", "-m", "rag_app.main"]