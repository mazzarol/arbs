FROM python:3.12-slim

WORKDIR /app

# Install only what's needed
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY app/ ./app/

# Persistent data volume
VOLUME /data

ENV DB_PATH=/data/recruiter.db

EXPOSE 8000

CMD ["sh", "-c", "python -c \"from app.database import init_db; init_db()\" && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
