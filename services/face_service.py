import cv2
import numpy as np
from insightface.app import FaceAnalysis


face_app = FaceAnalysis(
    name="buffalo_l",
    providers=["CPUExecutionProvider"],
    addons=["liveness"],
    liveness_mode="normal",
    liveness_threshold=0.8
)

face_app.prepare(
    ctx_id=0,
    det_size=(640, 640)
)


def analisar_rosto(caminho_foto: str):
    imagem = cv2.imread(caminho_foto)

    if imagem is None:
        raise ValueError("Não foi possível ler a imagem.")

    faces = face_app.get(imagem)

    if not faces:
        raise ValueError("Nenhum rosto encontrado.")

    if len(faces) > 1:
        raise ValueError("Mais de um rosto encontrado.")

    face = faces[0]

    liveness = face.liveness

    return {
        "is_live": liveness.is_live,
        "live_score": float(liveness.live_score),
        "status": liveness.status,
        "face": face
    }


def gerar_embedding(caminho_foto: str):

    resultado = analisar_rosto(caminho_foto)

    if resultado["is_live"] is not True:
        raise ValueError(
            f"Rosto não considerado real. "
            f"Liveness: {resultado['live_score']:.4f}"
        )

    face = resultado["face"]

    embedding = face.embedding

    norma = np.linalg.norm(embedding)

    if norma == 0:
        raise ValueError("Embedding inválido.")

    embedding = embedding / norma

    return embedding.tolist()


def calcular_similaridade(embedding1, embedding2):

    a = np.array(embedding1, dtype=np.float32)
    b = np.array(embedding2, dtype=np.float32)

    norma_a = np.linalg.norm(a)
    norma_b = np.linalg.norm(b)

    if norma_a == 0 or norma_b == 0:
        return 0.0

    similaridade = np.dot(a, b) / (norma_a * norma_b)

    return float(similaridade)