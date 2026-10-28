FROM python:3.13-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY scripts ./scripts
COPY models ./models
COPY data/db/schema.sql ./data/db/schema.sql
ENV PYTHONPATH=/app/src MODELS_DIR=/app/models
EXPOSE 8000
CMD ["uvicorn", "smartcart.app:app", "--host", "0.0.0.0", "--port", "8000"]
