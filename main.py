from fastapi import FastAPI

from routers.usuarios import router as usuarios_router

app = FastAPI(
    title="Facial API",
    version="1.0.0"
)

app.include_router(usuarios_router)


@app.get("/")
def home():
    return {
        "status": "ok",
        "mensagem": "Facial API funcionando!"
    }