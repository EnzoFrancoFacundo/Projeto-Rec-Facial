import os
import cv2
import numpy as np
import face_recognition
from multiprocessing import Process, Queue
from database import FaceDatabase

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
XML_LOCAL = os.path.join(BASE_DIR, "haarcascade_frontalface_default.xml")
TOLERANCIA = 0.45 
INDEX_CAMERA = 0 

def processo_ia(fila_entrada, fila_saida, encodings_conhecidos, nomes_conhecidos):
    """
    Roda em um PROCESSO SEPARADO (outro núcleo da CPU).
    Não afeta em nada a taxa de quadros (FPS) da câmera.
    """
    while True:
        dados = fila_entrada.get()
        if dados is None: # Sinal para encerrar
            break

        frame_rgb, boxes = dados
        
        try:
            encodings_frame = face_recognition.face_encodings(frame_rgb, boxes)
            resultados = []

            for (top, right, bottom, left), encoding_atual in zip(boxes, encodings_frame):
                nome = "Desconhecido"
                cor = (0, 0, 255)

                if len(encodings_conhecidos) > 0:
                    distancias = face_recognition.face_distance(encodings_conhecidos, encoding_atual)
                    melhor_indice = int(np.argmin(distancias))
                    melhor_distancia = distancias[melhor_indice]

                    if melhor_distancia <= TOLERANCIA:
                        nome = nomes_conhecidos[melhor_indice]
                        cor = (0, 255, 0)
                        nome = f"{nome} ({melhor_distancia:.2f})"

                resultados.append((nome, cor))

            # Envia os nomes prontos de volta para o processo principal
            fila_saida.put(resultados)
        except Exception as e:
            print(f"❌ Erro no processo de IA: {e}")
            fila_saida.put([])

def reconhecer():
    db = FaceDatabase()

    if not os.path.exists(XML_LOCAL):
        print(f"❌ Erro: Arquivo XML '{XML_LOCAL}' não encontrado!")
        return

    print(" Carregando encodings...")
    encodings_originais, nomes_conhecidos, _ = db.get_all_encodings()

    if not encodings_originais:
        print(" Aviso: Nenhum rosto cadastrado.")
        return

    encodings_conhecidos = [np.array(enc) for enc in encodings_originais]

    # Filas para comunicação entre processos
    fila_entrada = Queue(maxsize=1)
    fila_saida = Queue(maxsize=1)

    # Inicia o processo isolado da IA
    p_ia = Process(
        target=processo_ia, 
        args=(fila_entrada, fila_saida, encodings_conhecidos, nomes_conhecidos)
    )
    p_ia.daemon = True
    p_ia.start()

    classificador_rosto = cv2.CascadeClassifier(XML_LOCAL)
    cap = cv2.VideoCapture(INDEX_CAMERA)

    if not cap.isOpened():
        cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("❌ Erro fatal: Câmera não encontrada.")
        return

    print("\n Reconhecimento Facial de ALTA PERFORMANCE Ativo. Pressione 'q' para sair.")

    contador_frames = 0
    INTERVALO_DETECCAO = 5  # Detecta rosto a cada 5 frames
    boxes_atuais = []
    dados_ia_cache = []
    ia_aguardando_resposta = False

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        contador_frames += 1

        # Reduz a imagem para 25% do tamanho original
        frame_pequeno = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

        # 1. Busca rápida de retângulos (Haar Cascade) a cada 5 frames
        if contador_frames % INTERVALO_DETECCAO == 0:
            cinza = cv2.cvtColor(frame_pequeno, cv2.COLOR_BGR2GRAY)
            faces_detectadas = classificador_rosto.detectMultiScale(
                cinza, scaleFactor=1.2, minNeighbors=4, minSize=(20, 20)
            )

            if len(faces_detectadas) > 0:
                boxes_atuais = [(y, x + w, y + h, x) for (x, y, w, h) in faces_detectadas]

                # Se o outro processo estiver livre, envia a imagem para reconhecimento
                if not ia_aguardando_resposta and fila_entrada.empty():
                    frame_rgb = cv2.cvtColor(frame_pequeno, cv2.COLOR_BGR2RGB)
                    fila_entrada.put((frame_rgb, boxes_atuais))
                    ia_aguardando_resposta = True
            else:
                boxes_atuais = []

        # 2. Recebe o resultado da IA sem bloquear o loop do vídeo
        if ia_aguardando_resposta and not fila_saida.empty():
            dados_ia_cache = fila_saida.get()
            ia_aguardando_resposta = False

        # 3. Desenho síncrono ultra-rápido no frame principal
        if len(boxes_atuais) > 0:
            for i, (y, x_w, y_h, x) in enumerate(boxes_atuais):
                w = x_w - x
                h = y_h - y

                if i < len(dados_ia_cache):
                    nome, cor = dados_ia_cache[i]
                else:
                    nome, cor = "Identificando...", (255, 165, 0)

                # Reescalona (* 4) para desenhar na resolução total da câmera
                box_top, box_right, box_bottom, box_left = y * 4, (x + w) * 4, (y + h) * 4, x * 4

                cv2.rectangle(frame, (box_left, box_top), (box_right, box_bottom), cor, 2)
                cv2.putText(frame, nome, (box_left, box_top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, cor, 2)

        # Exibe o frame na janela
        cv2.imshow("Reconhecimento Facial em Tempo Real", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Encerra o processo secundário limpadamente
    fila_entrada.put(None)
    p_ia.join()
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    reconhecer()