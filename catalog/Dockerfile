FROM python:latest
LABEL authors="Senpais"
RUN mkdir /app
ADD . /app
WORKDIR /app
RUN pip install -r req.txt
CMD ["python", "catalog.py"]