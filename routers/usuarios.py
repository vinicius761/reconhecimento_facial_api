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
    senha: str = Form(...),  # Novo campo obrigatório
    cpf: str = Form(None),
    email: str = Form(None),
    nivel_acesso: str = Form("USUARIO"),  # Novo campo com valor padrão
    foto: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    return await usuario_controller.processar_cadastro_usuario(
        nome=nome,
        cpf=cpf,
        email=email,
        senha=senha,
        foto=foto,
        db=db,
        nivel_acesso=nivel_acesso,
    )

