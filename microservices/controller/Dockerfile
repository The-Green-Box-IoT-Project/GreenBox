FROM python:3.12-slim
WORKDIR /app

COPY ./controller /app/
COPY ./utils /app/utils

COPY ./controller/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

EXPOSE 8080
CMD ["python", "main.py"]