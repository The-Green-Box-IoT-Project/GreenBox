FROM python:3.11-slim

WORKDIR /app

ENV PYTHONPATH=/app

COPY . /app/

RUN pip install --no-cache-dir cherrypy influxdb-client-3 pandas

EXPOSE 8086

CMD ["python", "app.py"]
