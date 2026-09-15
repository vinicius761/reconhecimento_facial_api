import cv2
import numpy as np
from insightface.app import FaceAnalysis


face_app = FaceAnalysis(
    name="buffalo_l",
    providers=["CPUExecutionProvider"]
)

face_app.prepare(
    ctx_id=0,
    det_size=(640, 640)
)


def gerar_embedding(caminho_foto: str):

    imagem = cv2.imread(caminho_foto)

    if imagem is None:
        raise ValueError("Não foi possível ler a imagem.")

    faces = face_app.get(imagem)

    if not faces:
        raise ValueError("Nenhum rosto encontrado.")

    if len(faces) > 1:
        raise ValueError("Mais de um rosto encontrado.")

    face = faces[0]

    embedding = face.embedding.astype(np.float32)

    # Normalização
    norma = np.linalg.norm(embedding)

    if norma == 0:
        raise ValueError("Embedding inválido.")

    embedding = embedding / norma

    return embedding.tolist()


def calcular_similaridade(embedding1, embedding2):

    a = np.array(
        embedding1,
        dtype=np.float32
    )

    b = np.array(
        embedding2,
        dtype=np.float32
    )

    norma_a = np.linalg.norm(a)
    norma_b = np.linalg.norm(b)

    if norma_a == 0 or norma_b == 0:
        return 0.0

    return float(
        np.dot(a, b) /
        (norma_a * norma_b)
    )

