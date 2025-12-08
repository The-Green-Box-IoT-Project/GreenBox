FROM python:3.11-slim

WORKDIR /app

ENV PYTHONPATH=/app

COPY . /app/

RUN pip install --no-cache-dir fastapi uvicorn pymongo

EXPOSE 8082

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8082"]