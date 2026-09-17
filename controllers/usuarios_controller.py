import os
import shutil
import uuid
import json
import numpy as np
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
import bcrypt

from services.face_service import analisar_rosto

UPLOAD_DIR = "/app/uploads/faces"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _salvar_arquivo_temp(foto) -> tuple[str, str]:
    extensao = os.path.splitext(foto.filename)[1].lower() if foto.filename else ".jpg"
    if not extensao:
        extensao = ".jpg"
        
    nome_arquivo = f"{uuid.uuid4()}{extensao}"
    caminho = os.path.join(UPLOAD_DIR, nome_arquivo)
    
    with open(caminho, "wb") as arquivo:
        shutil.copyfileobj(foto.file, arquivo)
        
    return caminho, nome_arquivo


async def processar_cadastro_usuario(
    nome: str,
    cpf: str,
    email: str,
    foto,
    senha,
    db: Session,
    nivel_acesso: str = "USUARIO",  
) -> dict:
    caminho, nome_arquivo = _salvar_arquivo_temp(foto)

    try:
        resultado_face = analisar_rosto(caminho)
        face = resultado_face["face"]
        is_live = resultado_face["is_live"]
        live_score = resultado_face["live_score"]
        status = resultado_face["status"]

        if is_live is not True:
            raise HTTPException(
                status_code=400,
                detail={
                    "mensagem": "O rosto não foi considerado real.",
                    "liveness": {
                        "is_live": False,
                        "score": round(live_score, 4),
                        "status": status,
                    },
                },
            )

        embedding = face.embedding
        norma = np.linalg.norm(embedding)
        if norma == 0:
            raise ValueError("Embedding inválido.")

        embedding = (embedding / norma).tolist()
        embedding_json = json.dumps(embedding)

        # Checa se CPF ou Email já estão cadastrados
        usuario_existente = db.execute(
            text("SELECT cpf, email FROM usuarios WHERE cpf = :cpf OR email = :email"),
            {"cpf": cpf, "email": email},
        ).first()

        if usuario_existente:
            campo = "cpf" if usuario_existente.cpf == cpf else "email"
            raise HTTPException(
                status_code=400,
                detail={
                    "mensagem": f"{campo.upper()} já cadastrado no sistema.",
                    "campo": campo,
                },
            )

        salt = bcrypt.gensalt()
        senha_hash = bcrypt.hashpw(senha.encode('utf-8'), salt).decode('utf-8')

        foto_relativa = f"uploads/faces/{nome_arquivo}"
        resultado = db.execute(
            text("""
                INSERT INTO usuarios (nome, cpf, email, foto_path, embedding, nivel_acesso, senha)
                VALUES (:nome, :cpf, :email, :foto_path, CAST(:embedding AS jsonb), :nivel_accesso, :senha)
                RETURNING id
            """),
            {
                "nome": nome,
                "cpf": cpf,
                "email": email,
                "foto_path": foto_relativa,
                "embedding": embedding_json,
                "nivel_accesso": nivel_acesso.upper(), 
                "senha":senha_hash
            },
        )
        usuario_id = resultado.scalar()
        db.commit()

        return {
            "sucesso": True,
            "usuario_id": str(usuario_id),
            "nome": nome,
            "nivel_accesso": nivel_acesso.upper(),
            "foto": foto_relativa,
            "embedding_salvo": True,
            "liveness": {
                "is_live": True,
                "score": round(live_score, 4),
                "status": status,
            },
        }

    except HTTPException:
        db.rollback()
        if os.path.exists(caminho):
            os.remove(caminho)
        raise

    except Exception as e:
        db.rollback()
        if os.path.exists(caminho):
            os.remove(caminho)
        raise HTTPException(status_code=500, detail=str(e))


