from fastapi import FastAPI
from src.utils.logger import setup_logging
from src.api.routers.odd_router import router as odd_router

setup_logging()

app = FastAPI(title="ODD Review API")
app.include_router(odd_router)