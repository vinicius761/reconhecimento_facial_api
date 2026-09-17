from fastapi import APIRouter, UploadFile, File, Form, Depends
from sqlalchemy.orm import Session

from database.connection import SessionLocal
import controllers.usuarios_controller as usuario_controller

router = APIRouter(
    prefix="/usuarios",
    tags=["Usuários"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/")
async def cadastrar_usuario(
    nome: str = Form(...),
    cpf: str = Form(None),
    email: str = Form(None),
    foto: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    return await usuario_controller.processar_cadastro_usuario(
        nome, cpf, email, foto, db
    )


@router.post("/reconhecer")
async def reconhecer(
    foto: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    return await usuario_controller.processar_reconhecimento(
        foto, db
    )