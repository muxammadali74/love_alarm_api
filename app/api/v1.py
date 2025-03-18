from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from passlib.context import CryptContext
from app.models import User, UserInteraction, UserLogin, UserInfo, Location, LikeRequest
from app.database import get_db_connection
import os
import shutil
from math import radians, sin, cos, sqrt, atan2

router = APIRouter()

# Путь для Render Disk
UPLOAD_DIR = "/app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Монтируем папку для статических файлов (доступ через /uploads/)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

R = 6371000  # Радиус Земли в метрах

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Радиус Земли в км
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

@router.get("/")
async def root():
    return {"message": "Love Alarm API v1 is running!"}

@router.post("/users/{user_id}/activate-signal/")
async def activate_signal(user_id: int, location: Location):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE users SET latitude = %s, longitude = %s, signal_active = TRUE WHERE id = %s",
            (location.latitude, location.longitude, user_id)
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Ищем пользователей поблизости (радиус 1 км)
        cur.execute(
            "SELECT id, profile_photo, latitude, longitude FROM users WHERE signal_active = TRUE AND id != %s",
            (user_id,)
        )
        nearby_users = cur.fetchall()
        nearby_list = []
        user_lat = location.latitude
        user_lon = location.longitude
        
        for user in nearby_users:
            distance = haversine(user_lat, user_lon, user['latitude'], user['longitude'])
            if distance <= 1:  # Радиус 1 км
                nearby_list.append({
                    "id": user['id'],
                    "profile_photo": user['profile_photo']
                })
        
        conn.commit()
        return {"message": "Signal activated", "nearby_users": nearby_list}
    finally:
        cur.close()
        conn.close()

@router.post("/users/{user_id}/deactivate-signal/")
async def deactivate_signal(user_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE users SET signal_active = FALSE WHERE id = %s",
            (user_id,)
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found")
        conn.commit()
        return {"message": "Signal deactivated"}
    finally:
        cur.close()
        conn.close()

@router.get("/users/{user_id}/signal-status/")
async def get_signal_status(user_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT signal_active, latitude, longitude FROM users WHERE id = %s",
            (user_id,)
        )
        user_data = cur.fetchone()
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        
        is_active = user_data["signal_active"]
        nearby_list = []
        if is_active:
            cur.execute(
                "SELECT id, profile_photo, latitude, longitude FROM users WHERE signal_active = TRUE AND id != %s",
                (user_id,)
            )
            nearby_users = cur.fetchall()
            user_lat = user_data["latitude"]
            user_lon = user_data["longitude"]
            for user in nearby_users:
                distance = haversine(user_lat, user_lon, user['latitude'], user['longitude'])
                if distance <= 1:  # Радиус 1 км
                    nearby_list.append({
                        "id": user['id'],
                        "profile_photo": user['profile_photo']
                    })
        
        return {
            "is_active": is_active,
            "nearby_users": nearby_list
        }
    finally:
        cur.close()
        conn.close()

@router.post("/users/{user_id}/send-like/")
async def send_like(user_id: int, like: LikeRequest):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO likes (from_user_id, to_user_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (user_id, like.target_user_id)
        )
        conn.commit()
        return {"message": "Like sent"}
    finally:
        cur.close()
        conn.close()

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

@router.post("/users/")
async def create_user(user: User):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        hashed_password = hash_password(user.password)
        cur.execute(
            "INSERT INTO users (username, name, surname, email, password_hash, profile_photo, latitude, longitude) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (user.username, user.name, user.surname, user.email, hashed_password, user.profile_photo, user.latitude, user.longitude)
        )
        user_id = cur.fetchone()["id"]
        conn.commit()
        return {"message": "User created", "user_id": user_id}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"User creation failed: {str(e)}")
    finally:
        cur.close()
        conn.close()

@router.post("/login/")
async def login_user(login: UserLogin):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id, password_hash FROM users WHERE username = %s",
            (login.username,)
        )
        user = cur.fetchone()
        if not user or not verify_password(login.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid username or password")
        return {"message": "(Login successful", "id": user["id"]}  # Совместимо с ApiClient
    finally:
        cur.close()
        conn.close()

@router.get("/users/{user_id}/", response_model=UserInfo)
async def get_user_info(user_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id, username, name, surname, email, profile_photo FROM users WHERE id = %s",
            (user_id,)
        )
        user_data = cur.fetchone()
        if user_data is None:
            raise HTTPException(status_code=404, detail="User not found")
        return {
            "id": user_data['id'],
            "username": user_data['username'],
            "name": user_data["name"],
            "surname": user_data["surname"],
            "email": user_data["email"],
            "profile_photo": user_data["profile_photo"]
        }
    except Exception as e:
        print(f"Exception type: {type(e)}, Message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {type(e).__name__} - {str(e)}")
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
        photo_url = f"/uploads/{user_id}_{file.filename}"  # Относительный путь для Render
        cur.execute(
            "UPDATE users SET profile_photo = %s WHERE id = %s",
            (photo_url, user_id)
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found")
        conn.commit()
        return {"message": "Photo uploaded", "file_path": photo_url}
    finally:
        cur.close()
        conn.close()

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
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Interaction creation failed: {str(e)}")
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
                distance = haversine(user_lat, user_lon, liker_data["latitude"], liker_data["longitude"])
                if distance <= 0.1:  # 100 метров
                    love_count += 1
    finally:
        cur.close()
        conn.close()
    return {"user_id": user_id, "love_count": love_count, "message": f"{love_count} people nearby like you"}