#!/bin/bash

# Influx
cd ./microservices/influx
docker compose up -d --build

# Mongo
cd ../../microservices/mongo
docker compose up -d --build

# Statistics
cd ../../microservices/statistics
docker compose up -d --build

# Control strategies
cd ../../microservices/controller
docker compose up -d --build

# Catalog
cd ../../microservices/catalog
docker compose up -d --build