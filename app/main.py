"""FastAPI entrypoint: uvicorn app.main:app --reload"""
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .routes import router

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="ComicCraft - AI Comic Story Creator")

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

app.include_router(router)
