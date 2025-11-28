# Adapters/mongo/app.py
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

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
def list_greenhouses(username: str = Query(None)):
    """
    Ritorna le serre. Se username è fornito, filtra per owner == username.
    """
    query = {}
    if username:
        query["owner"] = username   # oppure "tenant_id" se cambi schema

    items = list(mongo.db.greenhouses.find(query, {"_id": 0}))
    return {"items": items}


@app.get("/devices")
def list_devices(greenhouse_id: str = Query(...)):
    """
    Ritorna i device associati a una greenhouse.
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
