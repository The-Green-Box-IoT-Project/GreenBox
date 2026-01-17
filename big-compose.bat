cd ./microservices/influx
docker compose up -d --build
cd ../../microservices/mongo
docker compose up -d --build
cd ../../microservices/catalog
docker compose up -d --build
cd ../../microservices/controller
docker compose up -d --build
cd ../../microservices/statistics
docker compose up -d --build
pause