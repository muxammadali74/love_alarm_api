from fastapi import FastAPI
from app.api.v1 import router
from app.database import init_db


app = FastAPI(title="Love Alarm API")
app.include_router(router, prefix='/v1')
init_db()

