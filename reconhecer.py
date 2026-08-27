import os
import cv2
import pickle
import numpy as np
import face_recognition

# Descobre automaticamente a pasta onde o script está rodando
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENCODINGS_FILE = os.path.join(BASE_DIR, "encodings.pickle")
XML_LOCAL = os.path.join(BASE_DIR, "haarcascade_frontalface_default.xml")

TOLERANCIA = 0.5  # Menor = mais rigoroso. Maior = mais permissivo.
INDEX_CAMERA = 0  # Altere para 1 se tiver mais de uma câmera e não abrir


def reconhecer():
    # 1. Verifica se o banco de dados de rostos existe
    if not os.path.exists(ENCODINGS_FILE):
        print(f"❌ Arquivo '{ENCODINGS_FILE}' não encontrado. Execute o treinar.py primeiro.")
        return

    # 2. Verifica se o classificador facial local existe
    if not os.path.exists(XML_LOCAL):
        print(f"❌ Arquivo '{XML_LOCAL}' não encontrado na pasta do projeto.")
        return

    # 3. Carrega os rostos conhecidos na memória
    print("Carregando banco de dados de rostos...")
    with open(ENCODINGS_FILE, "rb") as f:
        dados = pickle.load(f)

    encodings_conhecidos = dados["encodings"]
    nomes_conhecidos = dados["names"]

    # 4. Inicializa o detector de faces local do OpenCV
    classificador_rosto = cv2.CascadeClassifier(XML_LOCAL)

    # 5. Liga a webcam
    cap = cv2.VideoCapture(INDEX_CAMERA)
    if not cap.isOpened():
        print(f"Câmera no índice {INDEX_CAMERA} não encontrada. Tentando o índice 0...")
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Erro fatal: Não foi possível acessar nenhuma câmera.")
            return

    print("\nReconhecimento Facial ATIVO. Pressione 'q' na janela da câmera para sair.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Falha ao receber frame da câmera.")
            break

        # Processa uma versão menor em tons de cinza para detectar a posição do rosto rapidamente
        frame_pequeno = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        cinza = cv2.cvtColor(frame_pequeno, cv2.COLOR_BGR2GRAY)
        
        # Detecta rostos no frame atual
        faces_detectadas = classificador_rosto.detectMultiScale(cinza, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        if len(faces_detectadas) > 0:
            # Converte as coordenadas do OpenCV (x, y, w, h) para o formato do face_recognition (top, right, bottom, left)
            boxes = []
            for (x, y, w, h) in faces_detectadas:
                boxes.append((y, x + w, y + h, x))

            # Converte o frame reduzido para RGB para a dlib extrair os dados faciais
            frame_rgb = cv2.cvtColor(frame_pequeno, cv2.COLOR_BGR2RGB)
            encodings_frame = face_recognition.face_encodings(frame_rgb, boxes)

            # Compara cada rosto detectado na câmera com o banco de dados
            for (top, right, bottom, left), encoding_atual in zip(boxes, encodings_frame):
                # Reeescala as coordenadas de volta para o tamanho original do frame (já que reduzimos pela metade com fx=0.5)
                top, right, bottom, left = top * 2, right * 2, bottom * 2, left * 2

                nome = "Desconhecido"
                cor = (0, 0, 255)  # Vermelho para desconhecidos

                if encodings_conhecidos:
                    # Calcula a distância matemática entre o rosto da câmera e os rostos salvos
                    distancias = face_recognition.face_distance(encodings_conhecidos, encoding_atual)
                    melhor_indice = int(np.argmin(distancias))
                    melhor_distancia = distancias[melhor_indice]

                    # Se a distância for menor ou igual à tolerância, identificamos a pessoa
                    if melhor_distancia <= TOLERANCIA:
                        nome = nomes_conhecidos[melhor_indice]
                        cor = (0, 255, 0)  # Verde para conhecidos
                        nome = f"{nome} ({melhor_distancia:.2f})"

                # Desenha o quadrado ao redor do rosto
                cv2.rectangle(frame, (left, top), (right, bottom), cor, 2)
                # Escreve o nome acima do quadrado
                cv2.putText(frame, nome, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, cor, 2)

        # Exibe o resultado na janela
        cv2.imshow("Reconhecimento Facial em Tempo Real", frame)

        # Fecha o programa se o usuário apertar a tecla 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Libera recursos do sistema
    cap.release()
    cv2.destroyAllWindows()
    print("Programa encerrado.")


if __name__ == "__main__":
    reconhecer()
