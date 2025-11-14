# Adapters/mongo/app.py
from fastapi import FastAPI, HTTPException, Query
from typing import Dict, Any
import os
from datetime import datetime

from Mongo_DB_adapter import MongoAdapter  # <-- usa la tua classe

# Config da env (passati da docker-compose)
MONGO_URI = os.getenv("MONGO_URI", "mongodb://root:rootpassword@mongo:27017/")
DB_NAME = os.getenv("MONGO_DB", "greenbox")

# Istanza condivisa dell'adapter
mongo = MongoAdapter(MONGO_URI, DB_NAME)

app = FastAPI(title="GreenBox Mongo Adapter")

@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

@app.get("/greenhouses")
def list_greenhouses(tenant_id: str = Query(...)):
    """
    Ritorna tutte le serre di un tenant.
    Per ora usiamo tenant_id come filtro sul campo greenhouse.tenant_id
    """
    # Se in Mongo_DB_adapter non hai ancora un metodo dedicato, puoi leggere direttamente:
    items = list(mongo.db.greenhouses.find({"tenant_id": tenant_id}, {"_id": 0}))
    return {"items": items}

@app.get("/devices")
def list_devices(greenhouse_id: str = Query(...)):
    """
    Ritorna i raspberry_connectors associati alla greenhouse.
    """
    items = list(mongo.db.raspberry_connectors.find({"greenhouse_id": greenhouse_id}, {"_id": 0}))
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
