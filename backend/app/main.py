from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .db import Base, engine
from .routers import auth, records, collection, reviews, feed, follows, comments, conversations
import os
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response


Base.metadata.create_all(bind=engine)


# 🟢 Liste aqui os domínios do front (DNS/localhost)
FRONT_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://jojisdomain.ddns.net:5173",   # troque pelo seu DNS
    "http://jojisdomain.ddns.net",        # se servir sem porta
    "https://jojisdomain.ddns.net",       # se usar HTTPS no front
]

app = FastAPI()

# Tente usar allow_private_network=True (Starlette >= 0.27)
try:
  app.add_middleware(
      CORSMiddleware,
      allow_origins=FRONT_ORIGINS,
      allow_credentials=True,             # se usar cookies; p/ Bearer não é obrigatório
      allow_methods=["*"],
      # ou especifique: ["Authorization", "Content-Type"]
      allow_headers=["*"],
      max_age=3600,
      allow_private_network=True,         # ✅ PNA (Chrome/Edge)
  )
except TypeError:
  # Starlette antigo não tem allow_private_network -> adiciona um OPTIONS manual com o header PNA
  app.add_middleware(
      CORSMiddleware,
      allow_origins=FRONT_ORIGINS,
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
      max_age=3600,
  )

  @app.options("/{rest_of_path:path}")
  async def _pna_preflight(request: Request, rest_of_path: str):
    origin = request.headers.get("origin", "")
    acrh = request.headers.get(
        "access-control-request-headers", "Authorization, Content-Type")
    resp = Response(status_code=204)
    # espelha CORS + habilita PNA
    resp.headers["Access-Control-Allow-Origin"] = origin if origin in FRONT_ORIGINS else ""
    resp.headers["Vary"] = "Origin"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = acrh
    resp.headers["Access-Control-Allow-Private-Network"] = "true"
    return resp

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
