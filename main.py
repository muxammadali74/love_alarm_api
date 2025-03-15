from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app import router, init_db
import os
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Love Alarm API")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Можно указать ['http://localhost:3000'] для фронта
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = r'D:/Myprojects/Python/Lalarm/uploads'
os.makedirs(UPLOAD_DIR, exist_ok=True)
print("Serving uploads from:", UPLOAD_DIR)  # Отладка
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


app.include_router(router, prefix='/v1')

init_db()
