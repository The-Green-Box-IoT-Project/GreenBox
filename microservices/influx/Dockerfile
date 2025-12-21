FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir cherrypy pandas influxdb3-python python-dotenv
EXPOSE 8080
CMD ["python", "app.py"]