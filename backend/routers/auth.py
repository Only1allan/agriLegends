import re
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import bcrypt
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from config import settings
from services.neo4j import query, query_one

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

PHONE_RE = re.compile(r"^(\+2547\d{8}|07\d{8})$")


def normalize_phone(phone: str) -> str:
    p = phone.strip()
    if p.startswith("07"):
        p = "+254" + p[1:]
    elif p.startswith("7"):
        p = "+254" + p
    return p


def create_jwt(farmer_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": farmer_id, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_farmer(token: str = Depends(oauth2_scheme)) -> dict:
    payload = decode_jwt(token)
    farmer_id = payload.get("sub")
    if not farmer_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    farmer = query_one("MATCH (f:Farmer {farmerId: $fid}) RETURN f", {"fid": farmer_id})
    if not farmer:
        raise HTTPException(status_code=401, detail="Farmer not found")
    return {"farmerId": farmer_id, **farmer.get("f", {})}


class RegisterRequest(BaseModel):
    name: str
    phone: str
    password: str


class LoginRequest(BaseModel):
    phone: str
    password: str


class AuthResponse(BaseModel):
    farmerId: str
    token: str
    name: str


class FarmerProfile(BaseModel):
    farmerId: str
    name: str
    phone: str


@router.post("/register")
async def register(req: RegisterRequest) -> AuthResponse:
    phone = normalize_phone(req.phone)
    if not PHONE_RE.match(phone) and not phone.startswith("+254"):
        raise HTTPException(status_code=400, detail="Invalid Kenyan phone number. Use +2547XXXXXXXX or 07XXXXXXXX")

    if len(req.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters")
    if not req.name or not req.name.strip():
        raise HTTPException(status_code=400, detail="Name is required")

    existing = query_one("MATCH (f:Farmer {phone: $phone}) RETURN f.farmerId AS farmerId, f.name AS name", {"phone": phone})
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"A farmer with phone {phone} is already registered. Please log in instead."
        )

    farmer_id = str(uuid.uuid4())
    try:
        password_hash = bcrypt.hashpw(req.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to hash password")

    try:
        query(
            """
            CREATE (f:Farmer {
                farmerId: $id, name: $name, phone: $phone,
                passwordHash: $hash, preferredChannel: ['whatsapp_text'],
                preferredLanguage: 'en', registrationDate: date()
            })
            """,
            {"id": farmer_id, "name": req.name.strip(), "phone": phone, "hash": password_hash},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create farmer account: {str(e)}")

    token = create_jwt(farmer_id)
    return AuthResponse(farmerId=farmer_id, token=token, name=req.name.strip())


@router.post("/login")
async def login(req: LoginRequest) -> AuthResponse:
    phone = normalize_phone(req.phone)

    result = query_one(
        "MATCH (f:Farmer {phone: $phone}) RETURN f.farmerId AS farmerId, f.name AS name, f.passwordHash AS passwordHash",
        {"phone": phone},
    )
    if not result:
        raise HTTPException(status_code=401, detail="Invalid phone or password")

    stored_hash = result.get("passwordHash", "")
    if not stored_hash:
        raise HTTPException(status_code=401, detail="Invalid phone or password")

    if not bcrypt.checkpw(req.password.encode("utf-8"), stored_hash.encode("utf-8")):
        raise HTTPException(status_code=401, detail="Invalid phone or password")

    token = create_jwt(result["farmerId"])
    return AuthResponse(farmerId=result["farmerId"], token=token, name=result.get("name", ""))


@router.get("/me")
async def get_me(farmer: dict = Depends(get_current_farmer)) -> FarmerProfile:
    return FarmerProfile(
        farmerId=farmer["farmerId"],
        name=farmer.get("name", ""),
        phone=farmer.get("phone", ""),
    )
