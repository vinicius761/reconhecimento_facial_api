from fastapi import FastAPI

app = FastAPI(
    title="Facial API",
    version="1.0.0"
)


@app.get("/")
def home():
    return {
        "status": "ok",
        "mensagem": "Facial API funcionando! 123"
    }