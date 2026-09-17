import os
import shutil
import uuid
import json
import numpy as np
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from services.face_service import analisar_rosto, calcular_similaridade

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



async def processar_reconhecimento(foto, db: Session) -> dict:
    caminho, _ = _salvar_arquivo_temp(foto)

    def registrar_log(usuario_id, sim, foi_reconhecido):
        db.execute(
            text("""
                INSERT INTO reconhecimentos (
                    id, usuario_id, foto_path, similaridade, reconhecido, criado_em
                ) VALUES (
                    :id, :usuario_id, :foto_path, :similaridade, :reconhecido, NOW()
                )
            """),
            {
                "id": str(uuid.uuid4()),
                "usuario_id": usuario_id,
                "foto_path": caminho,
                "similaridade": sim,
                "reconhecido": foi_reconhecido,
            },
        )
        db.commit()

    try:
        resultado_face = analisar_rosto(caminho)
        face = resultado_face["face"]
        is_live = resultado_face["is_live"]
        live_score = resultado_face["live_score"]
        status = resultado_face["status"]

        if is_live is not True:
            registrar_log(usuario_id=None, sim=0, foi_reconhecido=False)
            return {
                "sucesso": True,
                "reconhecido": False,
                "liveness": {
                    "is_live": False,
                    "score": round(live_score, 4),
                    "status": status,
                },
                "similaridade": 0,
                "usuario": None,
                "mensagem": "Rosto não considerado real.",
            }

        embedding_recebido = face.embedding
        norma = np.linalg.norm(embedding_recebido)
        if norma == 0:
            raise ValueError("Embedding inválido.")

        embedding_recebido = (embedding_recebido / norma).tolist()

        resultado = db.execute(
            text("""
                SELECT id, nome, cpf, email, embedding, nivel_acesso
                FROM usuarios
                WHERE ativo = TRUE AND embedding IS NOT NULL
            """)
        )
        usuarios = resultado.mappings().all()

        if not usuarios:
            registrar_log(usuario_id=None, sim=0, foi_reconhecido=False)
            return {
                "sucesso": True,
                "reconhecido": False,
                "liveness": {
                    "is_live": True,
                    "score": round(live_score, 4),
                    "status": status,
                },
                "similaridade": 0,
                "usuario": None,
                "mensagem": "Nenhum usuário com rosto cadastrado.",
            }

        melhor_usuario = None
        melhor_similaridade = -1

        for usuario in usuarios:
            embedding_cadastrado = usuario["embedding"]
            if isinstance(embedding_cadastrado, str):
                embedding_cadastrado = json.loads(embedding_cadastrado)

            similaridade = calcular_similaridade(
                embedding_recebido, embedding_cadastrado
            )

            if similaridade > melhor_similaridade:
                melhor_similaridade = similaridade
                melhor_usuario = usuario

        LIMIAR = 0.50

        if melhor_similaridade >= LIMIAR:
            registrar_log(
                usuario_id=str(melhor_usuario["id"]),
                sim=round(melhor_similaridade, 4),
                foi_reconhecido=True,
            )
            return {
                "sucesso": True,
                "reconhecido": True,
                "liveness": {
                    "is_live": True,
                    "score": round(live_score, 4),
                    "status": status,
                },
                "similaridade": round(melhor_similaridade, 4),
                "usuario": {
                    "id": str(melhor_usuario["id"]),
                    "nome": melhor_usuario["nome"],
                    "cpf": melhor_usuario["cpf"],
                    "email": melhor_usuario["email"],
                    "nivel_acesso": melhor_usuario["nivel_acesso"]
                },
            }

        registrar_log(
            usuario_id=str(melhor_usuario["id"]) if melhor_usuario else None,
            sim=round(melhor_similaridade, 4),
            foi_reconhecido=False,
        )
        return {
            "sucesso": True,
            "reconhecido": False,
            "liveness": {
                "is_live": True,
                "score": round(live_score, 4),
                "status": status,
            },
            "similaridade": round(melhor_similaridade, 4),
            "usuario": None,
            "mensagem": "Rosto não reconhecido.",
        }

    except Exception as e:
        db.rollback()
        if os.path.exists(caminho):
            os.remove(caminho)
        raise HTTPException(status_code=500, detail=str(e))