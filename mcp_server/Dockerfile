FROM python:3.12-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mcp_server/ ./mcp_server/
COPY agents/ ./agents/
COPY data/ ./data/

CMD ["python", "mcp_server/server.py"]
