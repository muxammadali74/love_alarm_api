from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException
from passlib.context import CryptContext
from app.models import User, UserInteraction, UserLogin
from app.database import get_db_connection
import os
import shutil
from math import radians, sin, cos, sqrt, atan2

app = FastAPI(title="Love Alarm API v1")
router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

R = 6371000  # Радиус Земли в метрах


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c
    print(f"Distance: {distance} meters")
    return distance


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


@router.get("/")
async def root():
    return {"message": "Love Alarm API v1 is running!"}


@router.post("/users/")
async def create_user(user: User):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        hashed_password = hash_password(user.password)  # Хэшируем пароль
        cur.execute(
            "INSERT INTO users (username, name, surname, email, password_hash, profile_photo, latitude, longitude) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (user.username, user.name, user.surname, user.email, hashed_password, user.profile_photo, user.latitude,
             user.longitude)
        )
        user_id = cur.fetchone()["id"]
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"User creation failed: {str(e)}")
    finally:
        cur.close()
        conn.close()
    return {"message": "User created", "user_id": user_id}


@router.post("/login/")
async def login_user(login: UserLogin):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Получаем пользователя по username
        cur.execute(
            "SELECT id, password_hash FROM users WHERE username = %s",
            (login.username,)
        )
        user = cur.fetchone()
        if not user or not verify_password(login.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid username or password")
        return {"message": "Login successful", "user_id": user["id"]}
    finally:
        cur.close()
        conn.close()


@router.post("/users/{user_id}/photo/")
async def upload_photo(user_id: int, file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, f"{user_id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE users SET profile_photo = %s WHERE id = %s",
            (file_path, user_id)
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()
    return {"message": "Photo uploaded", "file_path": file_path}


@router.put("/users/{user_id}/location/")
async def update_location(user_id: int, latitude: float, longitude: float):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE users SET latitude = %s, longitude = %s WHERE id = %s RETURNING id",
            (latitude, longitude, user_id)
        )
        updated_id = cur.fetchone()
        if not updated_id:
            raise HTTPException(status_code=404, detail="User not found")
        conn.commit()
    finally:
        cur.close()
        conn.close()
    return {"message": "Location updated", "user_id": user_id, "latitude": latitude, "longitude": longitude}


@router.post("/interactions/")
async def create_interaction(interaction: UserInteraction):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO interactions (user_id, target_id, interaction_type) VALUES (%s, %s, %s) RETURNING id",
            (interaction.user_id, interaction.target_id, interaction.interaction_type)
        )
        interaction_id = cur.fetchone()["id"]
        conn.commit()
    finally:
        cur.close()
        conn.close()
    return {"message": "Interaction saved", "interaction_id": interaction_id}


@router.get("/check-love/{user_id}")
async def check_love(user_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT latitude, longitude FROM users WHERE id = %s", (user_id,))
        user_data = cur.fetchone()
        if not user_data or user_data["latitude"] is None:
            raise HTTPException(status_code=404, detail="User location not found")

        user_lat, user_lon = user_data["latitude"], user_data["longitude"]
        cur.execute(
            "SELECT DISTINCT user_id FROM interactions WHERE target_id = %s",
            (user_id,)
        )
        likers = [row["user_id"] for row in cur.fetchall()]

        love_count = 0
        for liker_id in likers:
            cur.execute("SELECT latitude, longitude FROM users WHERE id = %s", (liker_id,))
            liker_data = cur.fetchone()
            if liker_data and liker_data["latitude"] is not None:
                distance = haversine_distance(
                    user_lat, user_lon, liker_data["latitude"], liker_data["longitude"]
                )
                if distance <= 100:
                    love_count += 1
    finally:
        cur.close()
        conn.close()
    return {"user_id": user_id, "love_count": love_count, "message": f"{love_count} people nearby like you"}