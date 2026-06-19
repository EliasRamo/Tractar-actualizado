import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")

if not MONGODB_URL:
    raise RuntimeError("MONGODB_URL no está configurada")

client = MongoClient(MONGODB_URL)
db = client["tractar"]

# Colecciones
usuarios     = db["usuarios"]
vehiculos    = db["vehiculos"]
afiliaciones = db["afiliaciones"]
viajes       = db["viajes"]

def get_db():
    return db