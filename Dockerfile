FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    nodejs \
    npm \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

COPY coordinator/requirements.txt /app/coordinator/requirements.txt
RUN pip install --no-cache-dir -r /app/coordinator/requirements.txt

COPY coordinator /app/coordinator

WORKDIR /app/coordinator

EXPOSE 5000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
