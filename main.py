from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.usuarios import router as usuarios_router

app = FastAPI(
    title="Facial API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(usuarios_router)


@app.get("/")
def home():
    return {
        "status": "ok",
        "mensagem": "Facial API funcionando!"
    }