# Adapters/mongo/app.py
import os
from datetime import datetime
from typing import Dict, Any, List

from fastapi import FastAPI, HTTPException, Query

from Mongo_DB_adapter import MongoAdapter  # usa la tua classe

# Config da variabili d'ambiente (ci pensa docker-compose a passarle)
MONGO_URI = os.getenv("MONGO_URI", "mongodb://root:rootpassword@mongo:27017/")
DB_NAME = os.getenv("MONGO_DB", "greenbox")

mongo = MongoAdapter(MONGO_URI, DB_NAME)

app = FastAPI(title="GreenBox Mongo Adapter")

@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

@app.get("/greenhouses")
def list_greenhouses(username: str = Query(...)):
    """
    Ritorna tutte le serre associate a uno username (tenant).
    Per il test filtriamo per greenhouse.tenant_id == username.
    """
    items = list(mongo.db.greenhouses.find({"tenant_id": username}, {"_id": 0}))
    return {"items": items}

@app.get("/devices")
def list_devices(greenhouse_id: str = Query(...)):
    """
    Ritorna i device associati a una greenhouse.
    Per il test leggiamo collection devices filtrando per greenhouse_id.
    """
    items = list(mongo.db.devices.find({"greenhouse_id": greenhouse_id}, {"_id": 0}))
    return {"items": items}

@app.get("/greenhouses/{greenhouse_id}")
def get_greenhouse(greenhouse_id: str):
    gh = mongo.retrieve_greenhouse(greenhouse_id)
    if not gh:
        raise HTTPException(status_code=404, detail="greenhouse_not_found")
    gh.pop("_id", None)
    return gh

@app.get("/devices/{device_id}")
def get_device(device_id: str):
    dev = mongo.retrieve_device(device_id)
    if not dev:
        raise HTTPException(status_code=404, detail="device_not_found")
    dev.pop("_id", None)
    return dev
