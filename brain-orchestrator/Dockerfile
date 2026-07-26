FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Docker CLI
RUN apt-get update && apt-get install -y docker.io docker-compose && rm -rf /var/lib/apt/lists/*

# Copy source code and models
COPY . /app

CMD ["python", "main.py"]
