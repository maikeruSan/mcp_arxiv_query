FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir "arxiv>=1.4.8" && \
    pip install --no-cache-dir arxiv-query-fluent && \
    pip install --no-cache-dir "mcp>=1.0.0" && \
    pip install --no-cache-dir "PyPDF2>=3.0.0" && \
    pip install -e .

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "-m", "mcp_arxiv_query"]
