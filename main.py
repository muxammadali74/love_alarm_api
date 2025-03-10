from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app import router, init_db

app = FastAPI(title="Love Alarm API")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Можно указать ['http://localhost:3000'] для фронта
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix='/v1')

init_db()
