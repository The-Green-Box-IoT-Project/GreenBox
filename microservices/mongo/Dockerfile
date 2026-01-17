FROM python:3.11-slim

WORKDIR /app

ENV PYTHONPATH=/app

COPY . /app/

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

EXPOSE 8082

CMD ["python", "app.py"]