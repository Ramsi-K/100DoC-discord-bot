# Dockerfile for 100DoC Discord Bot
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create a volume for persistent database storage
VOLUME ["/data"]

# Set environment variable for DB path (optional, see compose)
ENV DB_PATH=/data/streaks.db

CMD ["python", "main.py"]
