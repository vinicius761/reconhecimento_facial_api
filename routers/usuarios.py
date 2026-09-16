import os
import shutil
import uuid
import json

import numpy as np

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from sqlalchemy import text

from database.connection import SessionLocal
from services.face_service import (
    analisar_rosto,
    calcular_similaridade
)


router = APIRouter(
    prefix="/usuarios",
    tags=["Usuários"]
)


UPLOAD_DIR = "/app/uploads/faces"

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)


# ==========================================================
# CADASTRAR USUÁRIO
# ==========================================================

@router.post("/")
async def cadastrar_usuario(
    nome: str = Form(...),
    cpf: str = Form(None),
    email: str = Form(None),
    foto: UploadFile = File(...)
):

    extensao = ""

    if foto.filename:
        extensao = os.path.splitext(
            foto.filename
        )[1].lower()

    if not extensao:
        extensao = ".jpg"

    nome_arquivo = f"{uuid.uuid4()}{extensao}"

    caminho = os.path.join(
        UPLOAD_DIR,
        nome_arquivo
    )

    db = SessionLocal()

    try:

        # ==================================================
        # 1. SALVAR FOTO
        # ==================================================

        with open(caminho, "wb") as arquivo:

            shutil.copyfileobj(
                foto.file,
                arquivo
            )

        print("Foto salva:", caminho)

        # ==================================================
        # 2. ANALISAR ROSTO + LIVENESS
        # ==================================================

        print("Analisando rosto e liveness...")

        resultado_face = analisar_rosto(
            caminho
        )

        face = resultado_face["face"]

        is_live = resultado_face["is_live"]

        live_score = resultado_face["live_score"]

        status = resultado_face["status"]

        print("Liveness:")
        print("is_live:", is_live)
        print("score:", live_score)
        print("status:", status)

        # ==================================================
        # 3. BLOQUEAR FOTO / SPOOF
        # ==================================================

        if is_live is not True:

            raise HTTPException(
                status_code=400,
                detail={
                    "mensagem": "O rosto não foi considerado real.",
                    "liveness": {
                        "is_live": False,
                        "score": round(
                            live_score,
                            4
                        ),
                        "status": status
                    }
                }
            )

        # ==================================================
        # 4. GERAR EMBEDDING
        # ==================================================

        print("Gerando embedding...")

        embedding = face.embedding

        norma = np.linalg.norm(
            embedding
        )

        if norma == 0:

            raise ValueError(
                "Embedding inválido."
            )

        embedding = (
            embedding / norma
        )

        embedding = embedding.tolist()

        print(
            "Embedding gerado:",
            len(embedding),
            "valores"
        )

        # ==================================================
        # 5. TRANSFORMAR EMBEDDING EM JSON
        # ==================================================

        embedding_json = json.dumps(
            embedding
        )

        # ==================================================
        # 6. SALVAR USUÁRIO
        # ==================================================


        # Busca se já existe algum registro com o mesmo CPF
        usuario_existente = db.execute(
            text("SELECT id FROM usuarios WHERE cpf = :cpf"),
            {"cpf": cpf}
        ).first()

        if usuario_existente:
            raise HTTPException(
                status_code=400,
                detail={
                    "mensagem": "CPF já cadastrado no sistema.",
                    "campo": "cpf"
                }
            )

        resultado = db.execute(
            text("""
                INSERT INTO usuarios (
                    nome,
                    cpf,
                    email,
                    foto_path,
                    embedding
                )
                VALUES (
                    :nome,
                    :cpf,
                    :email,
                    :foto_path,
                    CAST(:embedding AS jsonb)
                )
                RETURNING id
            """),
            {
                "nome": nome,
                "cpf": cpf,
                "email": email,
                "foto_path": (
                    f"uploads/faces/{nome_arquivo}"
                ),
                "embedding": embedding_json
            }
        )

        usuario_id = resultado.scalar()

        db.commit()

        print(
            "Usuário cadastrado:",
            usuario_id
        )

        # ==================================================
        # 7. RETORNO
        # ==================================================

        return {

            "sucesso": True,

            "usuario_id": str(
                usuario_id
            ),

            "nome": nome,

            "foto": (
                f"uploads/faces/{nome_arquivo}"
            ),

            "embedding_salvo": True,

            "liveness": {
                "is_live": True,
                "score": round(
                    live_score,
                    4
                ),
                "status": status
            }
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

        print(
            "Erro ao cadastrar usuário:",
            e
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:

        db.close()


# ==========================================================
# RECONHECER USUÁRIO
# ==========================================================

@router.post("/reconhecer")
async def reconhecer(
    foto: UploadFile = File(...)
):

    print("================================")
    print("ARQUIVO RECEBIDO:")
    print("filename:", foto.filename)
    print("content_type:", foto.content_type)
    print("================================")

    extensao = ""

    if foto.filename:
        extensao = os.path.splitext(
            foto.filename
        )[1].lower()

    if not extensao:
        extensao = ".jpg"

    nome_arquivo = (
        f"{uuid.uuid4()}{extensao}"
    )

    caminho = os.path.join(
        UPLOAD_DIR,
        nome_arquivo
    )

    db = SessionLocal()

    try:

        # ==================================================
        # 1. SALVAR FOTO TEMPORARIAMENTE
        # ==================================================

        print("Recebendo foto...")

        with open(caminho, "wb") as arquivo:

            shutil.copyfileobj(
                foto.file,
                arquivo
            )

        print("Foto salva.")

        # ==================================================
        # 2. LIVENESS
        # ==================================================

        print(
            "Analisando liveness..."
        )

        resultado_face = analisar_rosto(
            caminho
        )

        face = resultado_face["face"]

        is_live = resultado_face["is_live"]

        live_score = resultado_face["live_score"]

        status = resultado_face["status"]

        print("================================")
        print("LIVENESS")
        print("is_live:", is_live)
        print("score:", live_score)
        print("status:", status)
        print("================================")

        # ==================================================
        # 3. BLOQUEAR SPOOFING
        # ==================================================

        if is_live is not True:

            print(
                "ROSTO REPROVADO NO LIVENESS"
            )

            return {

                "sucesso": True,

                "reconhecido": False,

                "liveness": {

                    "is_live": False,

                    "score": round(
                        live_score,
                        4
                    ),

                    "status": status
                },

                "similaridade": 0,

                "usuario": None,

                "mensagem":
                    "Rosto não considerado real."
            }

        print(
            "LIVENESS APROVADO"
        )

        # ==================================================
        # 4. GERAR EMBEDDING
        # ==================================================

        print(
            "Gerando embedding..."
        )

        embedding_recebido = face.embedding

        norma = np.linalg.norm(
            embedding_recebido
        )

        if norma == 0:

            raise ValueError(
                "Embedding inválido."
            )

        embedding_recebido = (
            embedding_recebido / norma
        )

        embedding_recebido = (
            embedding_recebido.tolist()
        )

        print(
            "Embedding recebido:",
            len(embedding_recebido),
            "dimensões"
        )

        # ==================================================
        # 5. BUSCAR USUÁRIOS
        # ==================================================

        print(
            "Buscando usuários cadastrados..."
        )

        resultado = db.execute(
            text("""
                SELECT
                    id,
                    nome,
                    cpf,
                    email,
                    embedding
                FROM usuarios
                WHERE ativo = TRUE
                  AND embedding IS NOT NULL
            """)
        )

        usuarios = (
            resultado
            .mappings()
            .all()
        )

        print(
            "Usuários encontrados:",
            len(usuarios)
        )

        # ==================================================
        # 6. NENHUM USUÁRIO
        # ==================================================

        if not usuarios:

            return {

                "sucesso": True,

                "reconhecido": False,

                "liveness": {

                    "is_live": True,

                    "score": round(
                        live_score,
                        4
                    ),

                    "status": status
                },

                "similaridade": 0,

                "usuario": None,

                "mensagem":
                    "Nenhum usuário com rosto cadastrado."
            }

        # ==================================================
        # 7. COMPARAR EMBEDDINGS
        # ==================================================

        melhor_usuario = None

        melhor_similaridade = -1

        for usuario in usuarios:

            embedding_cadastrado = (
                usuario["embedding"]
            )

            # Caso o PostgreSQL retorne JSON como string
            if isinstance(
                embedding_cadastrado,
                str
            ):

                embedding_cadastrado = (
                    json.loads(
                        embedding_cadastrado
                    )
                )

            similaridade = (
                calcular_similaridade(
                    embedding_recebido,
                    embedding_cadastrado
                )
            )

            print(
                f"Comparando com: "
                f"{usuario['nome']} "
                f"| Similaridade: "
                f"{similaridade:.4f}"
            )

            if (
                similaridade
                > melhor_similaridade
            ):

                melhor_similaridade = (
                    similaridade
                )

                melhor_usuario = (
                    usuario
                )

        # ==================================================
        # 8. LIMIAR
        # ==================================================

        LIMIAR = 0.50

        print(
            "================================"
        )

        print(
            "Melhor similaridade:",
            f"{melhor_similaridade:.4f}"
        )

        print(
            "Limiar:",
            LIMIAR
        )

        print(
            "================================"
        )

        # ==================================================
        # 9. RECONHECIDO
        # ==================================================

        if (
            melhor_similaridade
            >= LIMIAR
        ):

            print(
                "ROSTO RECONHECIDO:",
                melhor_usuario["nome"]
            )

            return {

                "sucesso": True,

                "reconhecido": True,

                "liveness": {

                    "is_live": True,

                    "score": round(
                        live_score,
                        4
                    ),

                    "status": status
                },

                "similaridade": round(
                    melhor_similaridade,
                    4
                ),

                "usuario": {

                    "id": str(
                        melhor_usuario["id"]
                    ),

                    "nome":
                        melhor_usuario["nome"],

                    "cpf":
                        melhor_usuario["cpf"],

                    "email":
                        melhor_usuario["email"]
                }
            }

        # ==================================================
        # 10. NÃO RECONHECIDO
        # ==================================================

        print(
            "ROSTO NÃO RECONHECIDO"
        )

        return {

            "sucesso": True,

            "reconhecido": False,

            "liveness": {

                "is_live": True,

                "score": round(
                    live_score,
                    4
                ),

                "status": status
            },

            "similaridade": round(
                melhor_similaridade,
                4
            ),

            "usuario": None,

            "mensagem":
                "Rosto não reconhecido."
        }

    except Exception as e:

        db.rollback()

        print(
            "Erro no reconhecimento:",
            e
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:

        db.close()

        if os.path.exists(caminho):
            os.remove(caminho)