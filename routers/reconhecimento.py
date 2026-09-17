from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session

from database.connection import SessionLocal
import controllers.reconhecimento_controller as reconhecimento_controller

router = APIRouter(
    prefix="/reconhecimento",
    tags=["Reconhecimento"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/")
async def reconhecer(
    foto: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    return await reconhecimento_controller.processar_reconhecimento(
        foto, db
    )