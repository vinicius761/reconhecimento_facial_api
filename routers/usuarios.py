import os
import shutil
import uuid
import json

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from sqlalchemy import text

from database.connection import SessionLocal
from services.face_service import calcular_similaridade, gerar_embedding

router = APIRouter(
    prefix="/usuarios",
    tags=["Usuários"]
)

UPLOAD_DIR = "/app/uploads/faces"

os.makedirs(UPLOAD_DIR, exist_ok=True)

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

    nome_arquivo = f"{uuid.uuid4()}{extensao}"

    caminho = os.path.join(
        UPLOAD_DIR,
        nome_arquivo
    )

    db = SessionLocal()

    try:

        # ==========================================
        # 1. SALVAR FOTO
        # ==========================================

        with open(caminho, "wb") as arquivo:
            shutil.copyfileobj(
                foto.file,
                arquivo
            )

        print("Foto salva:", caminho)

        # ==========================================
        # 2. GERAR EMBEDDING DO ROSTO
        # ==========================================

        print("Gerando embedding...")

        embedding = gerar_embedding(caminho)

        print(
            "Embedding gerado:",
            len(embedding),
            "valores"
        )

        # ==========================================
        # 3. TRANSFORMAR EMBEDDING EM JSON
        # ==========================================

        embedding_json = json.dumps(
            embedding
        )

        # ==========================================
        # 4. SALVAR USUÁRIO + EMBEDDING
        # ==========================================

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
                "foto_path": f"uploads/faces/{nome_arquivo}",
                "embedding": embedding_json
            }
        )

        usuario_id = resultado.scalar()

        db.commit()

        print(
            "Usuário cadastrado:",
            usuario_id
        )

        # ==========================================
        # 5. RETORNO
        # ==========================================

        return {
            "sucesso": True,
            "usuario_id": str(usuario_id),
            "nome": nome,
            "foto": f"uploads/faces/{nome_arquivo}",
            "embedding_salvo": True
        }

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


@router.post("/reconhecer")
async def reconhecer(
    foto: UploadFile = File(...)
):
    print("================================")
    print("ARQUIVO RECEBIDO:")
    print("filename:", foto.filename)
    print("content_type:", foto.content_type)
    print("================================")

    nome_arquivo = f"{uuid.uuid4()}.jpg"

    caminho = os.path.join(
        UPLOAD_DIR,
        nome_arquivo
    )

    db = SessionLocal()

    try:

        # ==========================================
        # 1. SALVAR FOTO TEMPORARIAMENTE
        # ==========================================

        print("Recebendo foto...")

        with open(caminho, "wb") as arquivo:
            shutil.copyfileobj(
                foto.file,
                arquivo
            )

        print("Foto salva.")

        # ==========================================
        # 2. GERAR EMBEDDING DO ROSTO RECEBIDO
        # ==========================================

        print("Gerando embedding...")

        embedding_recebido = gerar_embedding(caminho)

        print(
            "Embedding recebido:",
            len(embedding_recebido),
            "dimensões"
        )

        # ==========================================
        # 3. BUSCAR USUÁRIOS CADASTRADOS
        # ==========================================

        print("Buscando usuários cadastrados...")

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

        usuarios = resultado.mappings().all()

        print(
            "Usuários encontrados:",
            len(usuarios)
        )

        # ==========================================
        # 4. VERIFICAR SE EXISTEM USUÁRIOS
        # ==========================================

        if not usuarios:

            return {
                "sucesso": True,
                "reconhecido": False,
                "similaridade": 0,
                "usuario": None,
                "mensagem": "Nenhum usuário com rosto cadastrado."
            }

        # ==========================================
        # 5. COMPARAR COM OS USUÁRIOS
        # ==========================================

        melhor_usuario = None
        melhor_similaridade = -1

        for usuario in usuarios:

            embedding_cadastrado = usuario["embedding"]

            similaridade = calcular_similaridade(
                embedding_recebido,
                embedding_cadastrado
            )

            print(
                f"Comparando com: {usuario['nome']} "
                f"| Similaridade: {similaridade:.4f}"
            )

            if similaridade > melhor_similaridade:

                melhor_similaridade = similaridade
                melhor_usuario = usuario

        # ==========================================
        # 6. LIMIAR
        # ==========================================

        LIMIAR = 0.50

        print(
            f"Melhor similaridade: "
            f"{melhor_similaridade:.4f}"
        )

        print(
            f"Limiar: {LIMIAR}"
        )

        # ==========================================
        # 7. VERIFICAR SE RECONHECEU
        # ==========================================

        if melhor_similaridade >= LIMIAR:

            print(
                "ROSTO RECONHECIDO:",
                melhor_usuario["nome"]
            )

            return {
                "sucesso": True,
                "reconhecido": True,
                "similaridade": round(
                    melhor_similaridade,
                    4
                ),
                "usuario": {
                    "id": str(
                        melhor_usuario["id"]
                    ),
                    "nome": melhor_usuario["nome"],
                    "cpf": melhor_usuario["cpf"],
                    "email": melhor_usuario["email"]
                }
            }

        # ==========================================
        # 8. NÃO RECONHECIDO
        # ==========================================

        print("ROSTO NÃO RECONHECIDO")

        return {
            "sucesso": True,
            "reconhecido": False,
            "similaridade": round(
                melhor_similaridade,
                4
            ),
            "usuario": None,
            "mensagem": "Rosto não reconhecido."
        }

    except Exception as e:

        db.rollback()

        print(
            f"Erro no reconhecimento: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:

        db.close()

        if os.path.exists(caminho):
            os.remove(caminho)