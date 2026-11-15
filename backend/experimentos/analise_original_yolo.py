# Experimento inicial do grupo (detecção com YOLO + notas por quadro de vídeo).
# Não faz parte do BCY Lens final: o sistema usa backend/analise.py.
# Para rodar: pip install ultralytics opencv-python numpy
# e coloque o vídeo em experimentos/Test_media/videointro3.mp4
import cv2
import numpy as np
import os
from collections import Counter
from ultralytics import YOLO


# Caminho do vídeo relativo à pasta deste script
pasta_script = os.path.dirname(os.path.abspath(__file__))
caminho_video = os.path.join(pasta_script, "Test_media", "videointro3.mp4")

if not os.path.exists(caminho_video):
    print(f"Vídeo não encontrado: {caminho_video}")
    exit()

model = YOLO("yolo11n.pt")
contagem = Counter()

for num_frame, result in enumerate(model.predict(
    source=caminho_video,
    save=True,
    device=0,        # use "cpu" se não tiver GPU NVIDIA
    half=True,       # remova se usar CPU
    imgsz=640,
    stream=True,
    verbose=False
), start=1):

    print(f"\n--- Frame {num_frame} ---")

    if len(result.boxes) == 0:
        print("Nenhum objeto detectado")
        continue

    for box in result.boxes:
        classe = model.names[int(box.cls)]
        confianca = float(box.conf)
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2

        contagem[classe] += 1

        print(f"{classe:<12} conf: {confianca:.2f} | "
              f"caixa: ({x1:.0f}, {y1:.0f}) → ({x2:.0f}, {y2:.0f}) | "
              f"centro: ({cx:.0f}, {cy:.0f})")

print("\n=== Resumo ===")
if contagem:
    for classe, total in contagem.most_common():
        print(f"{classe}: {total} detecções")
else:
    print("Nenhum objeto detectado no vídeo.")
















def avaliar_iluminacao(frame_gray):
    """Calcula a nota de iluminação com base na média de brilho ideal (faixa central entre 0 e 255)."""
    media_brilho = np.mean(frame_gray)
    # 128 é o brilho perfeito médio. Quanto mais distante de 128, menor a nota.
    nota = 100 - (abs(media_brilho - 128) / 128 * 100)
    return max(0, min(100, nota))


def avaliar_contraste(frame_gray):
    """Calcula a nota de contraste com base no desvio padrão dos níveis de cinza."""
    desvio_padrao = np.std(frame_gray)
    # Um desvio padrão próximo de 64 indica bom contraste distribuído.
    nota = (desvio_padrao / 64) * 100
    return max(0, min(100, nota))


def avaliar_nitidez(frame_gray):
    """Calcula a nota de nitidez utilizando a variância do operador Laplaciano."""
    variancia_laplaciano = cv2.Laplacian(frame_gray, cv2.CV_64F).var()
    # Mapeia a variância (geralmente entre 0 e 500+) para uma escala de 0 a 100.
    nota = (variancia_laplaciano / 500.0) * 100
    return max(0, min(100, nota))


def avaliar_cores(frame_bgr):
    """Calcula a nota de cores com base na média de saturação no espaço HSV."""
    frame_hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    saturacao_media = np.mean(frame_hsv[:, :, 1])  # Canal S (Saturação)
    # Mapeia a saturação média (0 a 255) para uma escala de 0 a 100.
    nota = (saturacao_media / 128.0) * 100
    return max(0, min(100, nota))


def analisar_video(caminho_video):
    cap = cv2.VideoCapture(caminho_video)

    if not cap.isOpened():
        print("Erro ao abrir o vídeo.")
        return

    frame_count = 0


    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Cálculo das notas por frame
        nota_iluminacao = avaliar_iluminacao(frame_gray)
        nota_contraste = avaliar_contraste(frame_gray)
        nota_nitidez = avaliar_nitidez(frame_gray)
        nota_cores = avaliar_cores(frame)

        # Exibe no terminal as notas do frame atual
        print(f"--- Frame {frame_count} ---")
        print(f"Iluminação: {nota_iluminacao:.1f}/100")
        print(f"Contraste:   {nota_contraste:.1f}/100")
        print(f"Nitidez:     {nota_nitidez:.1f}/100")
        print(f"Cores:       {nota_cores:.1f}/100")

        # Exibe as notas na janela do vídeo
        cv2.putText(
            frame,
            f"Iluminacao: {nota_iluminacao:.1f}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
        )
        cv2.putText(
            frame,
            f"Contraste: {nota_contraste:.1f}",
            (10, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
        )
        cv2.putText(
            frame,
            f"Nitidez: {nota_nitidez:.1f}",
            (10, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
        )
        cv2.putText(
            frame,
            f"Cores: {nota_cores:.1f}",
            (10, 120),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
        )

        cv2.imshow("Análise de Qualidade de Vídeo", frame)

        # Pressione 'q' para encerrar a exibição
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


# Para testar, substitua pelo caminho do seu vídeo ou use 0 para webcam:
# analisar_video(0)
pasta_script = os.path.dirname(os.path.abspath(__file__))
caminho = os.path.join(pasta_script, "Test_media", "videointro3.mp4")
analisar_video(caminho)