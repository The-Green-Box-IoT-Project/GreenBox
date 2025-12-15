FROM python:3.11-slim

WORKDIR /app

ENV PYTHONPATH=/app

COPY . /app/

RUN pip install --no-cache-dir cherrypy pymongo

EXPOSE 8082

CMD ["python", "app.py"]