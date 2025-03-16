FROM python:3.12-slim

# 安裝必要的工具
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 複製專案文件
COPY . .

# 安裝依賴和專案
RUN pip install --no-cache-dir "arxiv>=1.4.8" && \
    pip install --no-cache-dir arxiv-query-fluent && \
    pip install --no-cache-dir "mcp>=1.0.0" && \
    pip install --no-cache-dir "PyPDF2>=3.0.0" && \
    pip install -e .

# 設定環境變數
ENV PYTHONUNBUFFERED=1

# 使用 Python 模組作為入口點
ENTRYPOINT ["python", "-m", "mcp_arxiv_query"]
