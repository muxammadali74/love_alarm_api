from fastapi import FastAPI
from app import router

from app import init_db

app = FastAPI(title="Love Alarm API")
app.include_router(router, prefix='/v1')
init_db()


