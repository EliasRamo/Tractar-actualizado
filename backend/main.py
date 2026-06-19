from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from bson import ObjectId
from io import BytesIO
from openpyxl import Workbook
from datetime import datetime, timezone

from database import usuarios, vehiculos, afiliaciones, viajes, db

# =========================
# HELPERS
# =========================

def next_seq(collection_name: str) -> int:
    """Genera un ID numérico autoincremental por colección."""
    result = db["counters"].find_one_and_update(
        {"_id": collection_name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    return result["seq"]


def serialize(doc: dict) -> dict:
    """Devuelve el doc con 'id' como int (seq_id) y convierte ObjectId/datetime."""
    if doc is None:
        return doc
    out = {}
    for k, v in doc.items():
        if k == "_id":
            continue  # omitir el ObjectId interno
        elif k == "seq_id":
            out["id"] = v  # exponer como 'id' entero
        elif isinstance(v, ObjectId):
            out[k] = str(v)  # referencias internas como string (no se usan en Flutter como int)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


def find_by_seq(collection, seq_id: int):
    """Busca documento por su ID numérico."""
    try:
        return collection.find_one({"seq_id": int(seq_id)})
    except Exception:
        return None


def safe_float(value, default=0.0) -> float:
    try:
        return float(str(value).replace(",", "."))
    except Exception:
        return default


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# =========================
# APP
# =========================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# MODELOS PYDANTIC
# (IDs como int | str para aceptar ambos desde Flutter)
# =========================
class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username:        str
    password:        str
    nombre_completo: str
    cedula:          str
    correo:          str
    telefono:        str
    rol:             str  # "propietario" | "conductor"


class VehicleRequest(BaseModel):
    user_id: int
    placa: str
    marca: str
    modelo: str
    color: str
    apodo: str | None = None


class TripRequest(BaseModel):
    user_id: int
    driver_id: int | None = None
    origen: str
    destino: str
    vehiculo: str | None = None
    flete: str | None = None


class AssignDriverRequest(BaseModel):
    driver_id: int
    vehicle_id: int


class AssignTripRequest(BaseModel):
    trip_id: int
    driver_id: int
    vehicle_id: int


# =========================
# AUTH
# =========================
@app.post("/register")
def register(data: RegisterRequest):
    roles_validos = {"propietario", "conductor"}
    if data.rol not in roles_validos:
        return {"success": False, "message": "Rol inválido. Use 'propietario' o 'conductor'"}

    if usuarios.find_one({"username": data.username}):
        return {"success": False, "message": "El username ya está en uso"}
    if usuarios.find_one({"cedula": data.cedula}):
        return {"success": False, "message": "La cédula ya está registrada"}
    if usuarios.find_one({"correo": data.correo}):
        return {"success": False, "message": "El correo ya está registrado"}

    seq = next_seq("usuarios")
    usuarios.insert_one({
        "seq_id":          seq,
        "username":        data.username,
        "password":        data.password,
        "nombre_completo": data.nombre_completo,
        "cedula":          data.cedula,
        "correo":          data.correo,
        "telefono":        data.telefono,
        "rol":             data.rol,
        "estado":          "Disponible",
    })
    return {"success": True}


@app.post("/login")
def login(data: LoginRequest):
    user = usuarios.find_one({"username": data.username, "password": data.password})
    if user:
        return {
            "success":         True,
            "user_id":         user["seq_id"],
            "username":        user["username"],
            "nombre_completo": user.get("nombre_completo", ""),
            "cedula":          user.get("cedula", ""),
            "correo":          user.get("correo", ""),
            "telefono":        user.get("telefono", ""),
            "rol":             user.get("rol", user.get("role", "")),
            "status":          user.get("estado", user.get("status", "Disponible")),
        }
    return {"success": False}


# =========================
# CONDUCTORES
# =========================
@app.put("/driver/status/{driver_id}")
def update_driver_status(driver_id: int, status: str):
    allowed = ["Disponible", "En viaje", "Inactivo"]
    if status not in allowed:
        return {"success": False, "message": "Estado no válido"}

    usuarios.update_one({"seq_id": driver_id}, {"$set": {"estado": status, "status": status}})
    return {"success": True, "message": f"Estado actualizado a {status}"}


@app.get("/driver/affiliations/{driver_id}")
def get_driver_affiliations(driver_id: int):
    aff_docs = list(afiliaciones.find({"driver_seq_id": driver_id}))
    v_seq_ids = [a["vehicle_seq_id"] for a in aff_docs]

    result = []
    for v in vehiculos.find({"seq_id": {"$in": v_seq_ids}}):
        owner = usuarios.find_one({"seq_id": v.get("owner_seq_id")})
        result.append({
            "vehicle_id":  v["seq_id"],
            "placa":       v.get("placa", ""),
            "marca":       v.get("marca", ""),
            "modelo":      v.get("modelo", ""),
            "color":       v.get("color", ""),
            "propietario": owner["username"] if owner else "",
        })

    return {"success": True, "affiliations": result}


@app.get("/drivers")
def get_drivers():
    docs = list(usuarios.find({"$or": [{"rol": "conductor"}, {"role": "conductor"}]}).sort("username", 1))
    result = [
        {"id": d["seq_id"], "username": d.get("username", ""), "status": d.get("status", "")}
        for d in docs
    ]
    return {"success": True, "drivers": result}


# =========================
# AFILIAR CONDUCTOR
# =========================
@app.post("/assign-driver")
def assign_driver(data: AssignDriverRequest):
    existing = afiliaciones.find_one({
        "vehicle_seq_id": data.vehicle_id,
        "driver_seq_id":  data.driver_id,
    })
    if existing:
        return {"success": False, "message": "Este conductor ya está afiliado a este vehículo"}

    afiliaciones.insert_one({
        "seq_id":         next_seq("afiliaciones"),
        "vehicle_seq_id": data.vehicle_id,
        "driver_seq_id":  data.driver_id,
        "created_at":     now_utc(),
    })

    vehiculos.update_one({"seq_id": data.vehicle_id}, {"$set": {"driver_seq_id": data.driver_id}})

    return {"success": True, "message": "Afiliado correctamente"}


# =========================
# ASIGNAR VIAJE
# =========================
@app.post("/assign-trip")
def assign_trip(data: AssignTripRequest):
    active_count = viajes.count_documents({
        "driver_seq_id": data.driver_id,
        "trip_status":   {"$in": ["Asignado", "En ruta"]},
    })
    if active_count > 0:
        return {"success": False, "message": "Este conductor ya tiene un viaje activo"}

    vehicle = vehiculos.find_one({"seq_id": data.vehicle_id})
    if not vehicle:
        return {"success": False, "message": "Vehículo no encontrado"}

    viajes.update_one(
        {"seq_id": data.trip_id},
        {"$set": {
            "driver_seq_id":  data.driver_id,
            "vehicle_seq_id": data.vehicle_id,
            "vehiculo":       vehicle.get("placa", ""),
            "trip_status":    "Asignado",
        }}
    )

    usuarios.update_one({"seq_id": data.driver_id}, {"$set": {"estado": "En viaje", "status": "En viaje"}})

    return {"success": True, "message": "Viaje asignado correctamente"}


# =========================
# DASHBOARD CONDUCTOR
# =========================
@app.get("/driver/dashboard/{driver_id}")
def driver_dashboard(driver_id: int):
    docs = list(vehiculos.find({"driver_seq_id": driver_id}))
    result = []
    for v in docs:
        owner = usuarios.find_one({"seq_id": v.get("owner_seq_id")})
        row = serialize(v)
        row["propietario"] = owner["username"] if owner else ""
        result.append(row)
    return {"success": True, "vehicles": result}


# =========================
# KPIs CONDUCTOR
# =========================
@app.get("/driver/kpis/{driver_id}")
def driver_kpis(driver_id: int):
    all_trips = list(viajes.find({"driver_seq_id": driver_id}))

    active    = sum(1 for t in all_trips if t.get("trip_status") in ("Asignado", "En ruta"))
    completed = sum(1 for t in all_trips if t.get("trip_status") == "Finalizado")
    cancelled = sum(1 for t in all_trips if t.get("trip_status") == "Cancelado")
    income    = sum(safe_float(t.get("flete", 0)) for t in all_trips if t.get("trip_status") == "Finalizado")

    return {
        "success": True,
        "kpis": {
            "active":    active,
            "completed": completed,
            "cancelled": cancelled,
            "income":    income,
        }
    }


# =========================
# VIAJES CONDUCTOR CON FILTRO
# =========================
@app.get("/driver/trips/{driver_id}")
def driver_trips(driver_id: int, status: str = "Todos"):
    # Vehículos afiliados al conductor
    aff_docs = list(afiliaciones.find({"driver_seq_id": driver_id}))
    affiliated_v_ids = [a["vehicle_seq_id"] for a in aff_docs]

    direct_v = list(vehiculos.find({"driver_seq_id": driver_id}))
    direct_v_ids = [v["seq_id"] for v in direct_v]

    all_v_ids = list(set(affiliated_v_ids + direct_v_ids))

    query: dict = {
        "$or": [
            {"driver_seq_id": driver_id},
            {"vehicle_seq_id": {"$in": all_v_ids}},
        ]
    }
    if status != "Todos":
        query["trip_status"] = status

    docs = list(viajes.find(query).sort("seq_id", -1))

    result = []
    for t in docs:
        row = serialize(t)
        if t.get("vehicle_seq_id"):
            v = vehiculos.find_one({"seq_id": t["vehicle_seq_id"]})
            row["placa"] = v.get("placa", "") if v else ""
        result.append(row)

    return {"success": True, "trips": result}


# =========================
# UPDATE STATUS VIAJE
# =========================
@app.put("/driver/trips/{trip_id}/status")
def update_trip_status(trip_id: int, status: str):
    trip = viajes.find_one({"seq_id": trip_id})
    viajes.update_one({"seq_id": trip_id}, {"$set": {"trip_status": status}})

    if status in ("Finalizado", "Cancelado") and trip and trip.get("driver_seq_id"):
        driver_seq = trip["driver_seq_id"]
        other_active = viajes.count_documents({
            "driver_seq_id": driver_seq,
            "trip_status":   {"$in": ["Asignado", "En ruta"]},
            "seq_id":        {"$ne": trip_id},
        })
        if other_active == 0:
            usuarios.update_one({"seq_id": driver_seq}, {"$set": {"estado": "Disponible", "status": "Disponible"}})

    return {"success": True}


# =========================
# VEHÍCULOS — SIN AFILIAR
# =========================
@app.get("/vehicles/{user_id}/sin-afiliar")
def get_vehicles_sin_afiliar_v2(user_id: int):
    owner_vehicles = list(vehiculos.find({"owner_seq_id": user_id}))
    result = []
    for v in owner_vehicles:
        active = viajes.count_documents({
            "vehiculo":    v.get("placa", ""),
            "trip_status": {"$in": ["Asignado", "En ruta"]},
        })
        if active == 0:
            result.append({
                "id":     v["seq_id"],
                "placa":  v.get("placa", ""),
                "marca":  v.get("marca", ""),
                "modelo": v.get("modelo", ""),
                "color":  v.get("color", ""),
                "apodo":  v.get("apodo"),
            })
    return {"success": True, "vehicles": result}


# =========================
# VEHÍCULOS — AFILIADOS
# =========================
@app.get("/vehicles/{user_id}/afiliados")
def get_vehicles_afiliados_v2(user_id: int):
    docs = list(vehiculos.find({
        "owner_seq_id":  user_id,
        "driver_seq_id": {"$exists": True, "$ne": None},
    }))
    result = []
    for v in docs:
        driver = usuarios.find_one({"seq_id": v["driver_seq_id"]}) if v.get("driver_seq_id") else None
        result.append({
            "id":              v["seq_id"],
            "placa":           v.get("placa", ""),
            "marca":           v.get("marca", ""),
            "modelo":          v.get("modelo", ""),
            "color":           v.get("color", ""),
            "apodo":           v.get("apodo"),
            "driver_id":       v.get("driver_seq_id"),
            "driver_username": driver["username"] if driver else "",
        })
    return {"success": True, "vehicles": result}


# =========================
# VEHÍCULOS — LISTADO PROPIETARIO
# =========================
@app.get("/vehicles/{user_id}")
def get_vehicles(user_id: int):
    docs = list(vehiculos.find({"owner_seq_id": user_id}))
    return [serialize(v) for v in docs]


# =========================
# CREAR VEHÍCULO
# =========================
@app.post("/vehicles")
def add_vehicle(v: VehicleRequest):
    try:
        placa = v.placa.strip().upper() if v.placa else v.placa
        if vehiculos.find_one({"placa": placa}):
            return {"success": False, "message": "Ya existe un vehículo con esa placa"}

        vehiculos.insert_one({
            "seq_id":      next_seq("vehiculos"),
            "owner_seq_id": v.user_id,
            "placa":       placa,
            "marca":       v.marca,
            "modelo":      v.modelo,
            "color":       v.color,
            "apodo":       v.apodo if v.apodo and v.apodo.strip() else None,
        })
        return {"success": True, "message": "Vehículo creado"}
    except Exception as e:
        return {"success": False, "message": str(e)}


# =========================
# VIAJES — SIN ASIGNAR
# =========================
@app.get("/trips/{user_id}/sin-asignar")
def get_trips_sin_asignar_early(user_id: int):
    docs = list(viajes.find({
        "owner_seq_id": user_id,
        "trip_status":  {"$in": [None, "", "Pendiente"]},
        "$or": [
            {"driver_seq_id": {"$exists": False}},
            {"driver_seq_id": None},
        ],
    }))
    result = [
        {
            "id":          d["seq_id"],
            "origen":      d.get("origen", ""),
            "destino":     d.get("destino", ""),
            "flete":       d.get("flete", ""),
            "trip_status": d.get("trip_status") or "Pendiente",
        }
        for d in docs
    ]
    return {"success": True, "trips": result}


# =========================
# VIAJES — LISTADO PROPIETARIO
# =========================
@app.get("/trips/{user_id}")
def get_trips(user_id: int):
    docs = list(viajes.find({"owner_seq_id": user_id}).sort("seq_id", -1))
    return [serialize(d) for d in docs]


# =========================
# CREAR VIAJE
# =========================
@app.post("/trips")
def add_trip(t: TripRequest):
    viajes.insert_one({
        "seq_id":       next_seq("viajes"),
        "owner_seq_id": t.user_id,
        "driver_seq_id": t.driver_id,
        "origen":       t.origen,
        "destino":      t.destino,
        "vehiculo":     t.vehiculo,
        "flete":        t.flete,
        "trip_status":  "Pendiente",
        "created_at":   now_utc(),
    })
    return {"success": True}


# =========================
# DETALLE VEHÍCULO
# =========================
def _get_vehicle_detail(vehicle_id: int):
    v = vehiculos.find_one({"seq_id": vehicle_id})
    if not v:
        return {"success": False}

    vehicle = serialize(v)

    aff_docs = list(afiliaciones.find({"vehicle_seq_id": vehicle_id}))
    driver_seq_ids = [a["driver_seq_id"] for a in aff_docs]
    driver_docs = list(usuarios.find({"seq_id": {"$in": driver_seq_ids}}))
    drivers = [
        {"id": d["seq_id"], "username": d.get("username", ""), "status": d.get("status", "")}
        for d in driver_docs
    ]

    return {"success": True, "vehicle": vehicle, "drivers": drivers}


@app.get("/vehicle/{vehicle_id}")
def get_vehicle_detail(vehicle_id: int):
    return _get_vehicle_detail(vehicle_id)


@app.get("/vehicle/detail/{vehicle_id}")
def get_vehicle_detail_alias(vehicle_id: int):
    return _get_vehicle_detail(vehicle_id)


# =========================
# ACTUALIZAR VEHÍCULO
# =========================
@app.put("/vehicle/{vehicle_id}")
def update_vehicle(vehicle_id: int, data: dict = Body(...)):
    vehiculos.update_one(
        {"seq_id": vehicle_id},
        {"$set": {
            "placa":  data.get("placa"),
            "marca":  data.get("marca"),
            "modelo": data.get("modelo"),
            "color":  data.get("color"),
            "apodo":  data.get("apodo"),
        }}
    )
    return {"success": True, "message": "Vehículo actualizado"}


# =========================
# HISTORIAL DE TRACTÁS
# =========================
@app.get("/tractas/{user_id}")
def get_tractas(user_id: int):
    docs = list(viajes.find({
        "owner_seq_id": user_id,
        "trip_status":  {"$in": ["Asignado", "En ruta", "Finalizado", "Cancelado"]},
    }).sort("seq_id", -1))

    result = []
    for t in docs:
        row = {
            "id":          t["seq_id"],
            "origen":      t.get("origen", ""),
            "destino":     t.get("destino", ""),
            "vehiculo":    t.get("vehiculo", ""),
            "flete":       t.get("flete", ""),
            "trip_status": t.get("trip_status", ""),
            "driver":      "",
        }
        if t.get("driver_seq_id"):
            driver = usuarios.find_one({"seq_id": t["driver_seq_id"]})
            row["driver"] = driver["username"] if driver else ""
        result.append(row)

    return {"success": True, "tractas": result}


# =========================
# AFILIACIONES PROPIETARIO
# =========================
@app.get("/affiliations/owner/{user_id}")
def get_all_affiliations(user_id: int):
    owner_vehicles = list(vehiculos.find({"owner_seq_id": user_id}))
    v_seq_ids = [v["seq_id"] for v in owner_vehicles]

    aff_docs = list(afiliaciones.find({"vehicle_seq_id": {"$in": v_seq_ids}}).sort("created_at", -1))

    result = []
    for a in aff_docs:
        v = vehiculos.find_one({"seq_id": a["vehicle_seq_id"]})
        d = usuarios.find_one({"seq_id": a["driver_seq_id"]})
        if v and d:
            result.append({
                "vehicle_id":      v["seq_id"],
                "placa":           v.get("placa", ""),
                "apodo":           v.get("apodo"),
                "marca":           v.get("marca", ""),
                "driver_id":       d["seq_id"],
                "driver_username": d.get("username", ""),
            })

    return {"success": True, "affiliations": result}


@app.get("/vehicle/{vehicle_id}/affiliations")
def get_vehicle_affiliations(vehicle_id: int):
    aff_docs = list(afiliaciones.find({"vehicle_seq_id": vehicle_id}))
    driver_seq_ids = [a["driver_seq_id"] for a in aff_docs]
    driver_docs = list(usuarios.find({"seq_id": {"$in": driver_seq_ids}}))
    result = [
        {"id": d["seq_id"], "username": d.get("username", ""), "status": d.get("status", "")}
        for d in driver_docs
    ]
    return {"success": True, "drivers": result}


# =========================
# PERFIL CONDUCTOR
# =========================
@app.get("/driver/profile/{driver_id}")
def get_driver_profile(driver_id: int):
    user = usuarios.find_one({"seq_id": driver_id})
    if not user:
        return {"success": False, "message": f"Usuario {driver_id} no encontrado"}

    data = {
        "id":              user["seq_id"],
        "username":        user.get("username", ""),
        "nombre_completo": user.get("nombre_completo", ""),
        "cedula":          user.get("cedula", "") or "",
        "correo":          user.get("correo", user.get("email", "")) or "",
        "telefono":        user.get("telefono", "") or "",
        "rol":             user.get("rol", user.get("role", "")),
        "status":          user.get("estado", user.get("status", "Disponible")),
    }

    aff_docs = list(afiliaciones.find({"driver_seq_id": driver_id}))
    v_seq_ids = [a["vehicle_seq_id"] for a in aff_docs]
    v_docs = list(vehiculos.find({"seq_id": {"$in": v_seq_ids}}))
    data["vehicles"] = [
        {
            "id":     v["seq_id"],
            "placa":  v.get("placa", ""),
            "apodo":  v.get("apodo"),
            "marca":  v.get("marca", ""),
            "modelo": v.get("modelo", ""),
            "color":  v.get("color", ""),
        }
        for v in v_docs
    ]

    tracta_docs = list(viajes.find({"driver_seq_id": driver_id}).sort("seq_id", -1))
    data["tractas"] = [
        {
            "id":          t["seq_id"],
            "origen":      t.get("origen", ""),
            "destino":     t.get("destino", ""),
            "flete":       t.get("flete", ""),
            "trip_status": t.get("trip_status", ""),
            "placa":       t.get("vehiculo", ""),
            "apodo":       None,
        }
        for t in tracta_docs
    ]

    data["income"] = sum(
        safe_float(t.get("flete", 0))
        for t in tracta_docs
        if t.get("trip_status") == "Finalizado"
    )

    return {"success": True, "driver": data}


# =========================
# TRACTÁS CONDUCTOR (dashboard)
# =========================
@app.get("/driver/tractas/{driver_id}")
def get_driver_tractas(driver_id: int):
    docs = list(viajes.find({"driver_seq_id": driver_id}).sort("seq_id", 1))

    result = []
    for t in docs:
        row = {
            "id":            t["seq_id"],
            "origen":        t.get("origen", ""),
            "destino":       t.get("destino", ""),
            "flete":         t.get("flete", ""),
            "trip_status":   t.get("trip_status", ""),
            "vehicle_placa": t.get("vehiculo", ""),
            "vehicle_id":    None,
            "placa":         t.get("vehiculo", ""),
            "apodo":         None,
            "marca":         None,
            "modelo":        None,
            "color":         None,
            "propietario":   None,
        }
        if t.get("vehicle_seq_id"):
            v = vehiculos.find_one({"seq_id": t["vehicle_seq_id"]})
            if v:
                owner = usuarios.find_one({"seq_id": v.get("owner_seq_id")})
                row.update({
                    "vehicle_id":  v["seq_id"],
                    "placa":       v.get("placa", ""),
                    "apodo":       v.get("apodo"),
                    "marca":       v.get("marca", ""),
                    "modelo":      v.get("modelo", ""),
                    "color":       v.get("color", ""),
                    "propietario": owner["username"] if owner else None,
                })
        result.append(row)

    return {"success": True, "tractas": result}


# =========================
# REPORTES
# =========================
@app.get("/reports/{user_id}")
def get_reports(
    user_id: int,
    fecha_inicio: str = None,
    fecha_fin: str = None,
    estado: str = None,
):
    query: dict = {"owner_seq_id": user_id}

    if fecha_inicio or fecha_fin:
        date_filter: dict = {}
        if fecha_inicio:
            date_filter["$gte"] = datetime.strptime(fecha_inicio, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if fecha_fin:
            date_filter["$lte"] = datetime.strptime(fecha_fin, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        query["created_at"] = date_filter

    if estado and estado != "Todos":
        query["trip_status"] = estado

    docs = list(viajes.find(query).sort("seq_id", -1))

    total_trips = len(docs)
    completed   = sum(1 for t in docs if t.get("trip_status") == "Finalizado")
    cancelled   = sum(1 for t in docs if t.get("trip_status") == "Cancelado")
    income      = sum(safe_float(t.get("flete", 0)) for t in docs if t.get("trip_status") == "Finalizado")

    return {
        "success": True,
        "summary": {
            "total_trips": total_trips,
            "completed":   completed,
            "cancelled":   cancelled,
            "income":      income,
        },
        "trips": [serialize(t) for t in docs],
    }


@app.get("/reports/{user_id}/excel")
def download_excel(user_id: int):
    docs = list(viajes.find({"owner_seq_id": user_id}).sort("seq_id", -1))
    rows = [
        {
            "origen":      t.get("origen", ""),
            "destino":     t.get("destino", ""),
            "vehiculo":    t.get("vehiculo", ""),
            "flete":       t.get("flete", ""),
            "trip_status": t.get("trip_status", ""),
        }
        for t in docs
    ]

    wb = Workbook()
    ws = wb.active
    ws.title = "Viajes"
    ws.append(["Origen", "Destino", "Vehículo", "Flete", "Estado"])
    for row in rows:
        ws.append([row["origen"], row["destino"], row["vehiculo"], row["flete"], row["trip_status"]])

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=reporte.xlsx"},
    )


# =========================
# FACTURACIÓN
# =========================
@app.get("/billing/{user_id}")
def get_billing(user_id: int):
    finalized = list(viajes.find({"owner_seq_id": user_id, "trip_status": "Finalizado"}))

    total   = sum(safe_float(t.get("flete", 0)) for t in finalized)
    now     = now_utc()
    monthly = sum(
        safe_float(t.get("flete", 0))
        for t in finalized
        if t.get("created_at") and t["created_at"].year == now.year and t["created_at"].month == now.month
    )

    by_vehicle_map: dict = {}
    for t in finalized:
        placa = t.get("vehiculo") or "Sin vehículo"
        entry = by_vehicle_map.setdefault(placa, {"vehiculo": placa, "trips": 0, "total": 0.0})
        entry["trips"] += 1
        entry["total"] += safe_float(t.get("flete", 0))
    by_vehicle = sorted(by_vehicle_map.values(), key=lambda x: x["total"], reverse=True)

    by_driver_map: dict = {}
    for t in finalized:
        if not t.get("driver_seq_id"):
            continue
        driver = usuarios.find_one({"seq_id": t["driver_seq_id"]})
        username = driver["username"] if driver else str(t["driver_seq_id"])
        entry = by_driver_map.setdefault(username, {"username": username, "trips": 0, "total": 0.0})
        entry["trips"] += 1
        entry["total"] += safe_float(t.get("flete", 0))
    by_driver = sorted(by_driver_map.values(), key=lambda x: x["total"], reverse=True)

    return {
        "success": True,
        "billing": {
            "total":      total,
            "monthly":    {"total": monthly},
            "by_vehicle": by_vehicle,
            "by_driver":  by_driver,
        },
    }


# =========================
# STARTUP — índices MongoDB
# =========================
@app.on_event("startup")
async def create_indexes():
    usuarios.create_index("seq_id", unique=True)
    usuarios.create_index("username", unique=True)
    usuarios.create_index("cedula", unique=True, sparse=True)
    usuarios.create_index("correo", unique=True, sparse=True)
    vehiculos.create_index("seq_id", unique=True)
    vehiculos.create_index("placa", unique=True)
    afiliaciones.create_index([("vehicle_seq_id", 1), ("driver_seq_id", 1)], unique=True)
    viajes.create_index("seq_id", unique=True)
    viajes.create_index("owner_seq_id")
    viajes.create_index("driver_seq_id")
    viajes.create_index("trip_status")