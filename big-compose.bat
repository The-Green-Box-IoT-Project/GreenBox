REM Influx
cd ./microservices/influx
docker compose up -d --build

REM Mongo
cd ../../microservices/mongo
docker compose up -d --build

REM Statistics
cd ../../microservices/statistics
docker compose up -d --build

REM Control strategies
cd ../../microservices/controller
docker compose up -d --build

REM Catalog
cd ../../microservices/catalog
docker compose up -d --build

pause