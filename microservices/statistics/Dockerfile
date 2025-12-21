FROM python:3.12-slim
WORKDIR /app

COPY ./statistics /app/
COPY ./utils /app/utils

COPY ./statistics/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

EXPOSE 8080
CMD ["python", "main.py"]