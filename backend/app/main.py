from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .db import Base, engine
from .routers import auth, records, collection, reviews, feed, follows, comments, conversations
import os
from fastapi.staticfiles import StaticFiles


Base.metadata.create_all(bind=engine)


app = FastAPI(title="Retrofagia API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router)
app.include_router(records.router)
app.include_router(collection.router)
app.include_router(reviews.router)
app.include_router(feed.router)
app.include_router(follows.router)
app.include_router(comments.router)
app.include_router(conversations.router)

os.makedirs("uploads/covers", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/")
def root():
  return {"status": "ok", "service": "retrofagia"}
