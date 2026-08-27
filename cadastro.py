import cv2
import face_recognition
import os
import time
import unicodedata
import re

TOTAL_AMOSTRAS = 50      # com embeddings, menos fotos já bastam (o modelo de reconhecimento já vem pré-treinado)
INTERVALO_CAPTURA = 0.75  # segundos entre capturas
INDEX_CAMERA = 0        # altere para 1 se estiver usando câmera USB externa
DATASET_DIR = "dataset"
MODELO_DETECCAO = "hog"  # "hog" = rápido, roda bem em CPU | "cnn" = mais preciso, precisa de GPU (dlib compilado com CUDA)


def normalizar_nome(nome):
    """
    Remove acentos, caracteres especiais, substitui espaços por '_' 
    e transforma tudo em letras minúsculas para evitar erros no S.O.
    Exemplo: "João Sávio!" -> "joao_savio"
    """
    # Remove acentos
    nome_limpo = unicodedata.normalize('NFKD', nome).encode('ASCII', 'ignore').decode('ASCII')
    # Transforma em minúsculo e troca espaços por underline
    nome_limpo = nome_limpo.lower().strip().replace(" ", "_")
    # Remove qualquer caractere que não seja letra, número ou underline
    nome_limpo = re.sub(r'[^a-z0-9_]', '', nome_limpo)
    return nome_limpo


def main():
    nome_usuario = input("Digite o Nome da pessoa a ser cadastrada: ").strip()
    if not nome_usuario:
        print("Nome inválido!")
        return

    # Normaliza o nome para criar a pasta com segurança
    usuario_id = normalizar_nome(nome_usuario)
    pasta_destino = os.path.join(DATASET_DIR, usuario_id)

    if os.path.exists(pasta_destino):
        print(f"\n[ERRO] O nome/ID '{usuario_id}' já está cadastrado no sistema!")
        print("Para cadastrar novamente essa pessoa, apague o cadastro antigo pelo gerenciar.py.")
        return

    os.makedirs(pasta_destino, exist_ok=True)

    cap = cv2.VideoCapture(INDEX_CAMERA)
    if not cap.isOpened():
        print(f"Erro ao abrir a câmera no índice {INDEX_CAMERA}.")
        return

    print("\n--- FASE 1: PREVIEW DA CÂMERA ---")
    print("Posicione-se em frente à câmera.")
    print("Pressione a tecla [ESPAÇO] para começar a capturar as fotos (ou 'q' para sair).\n")

    em_preview = True
    while em_preview:
        ret, frame = cap.read()
        if not ret:
            break

        # Reduz o frame pela metade só para a detecção ficar mais rápida no preview
        rgb_pequeno = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)[:, :, ::-1]
        rostos = face_recognition.face_locations(rgb_pequeno, model=MODELO_DETECCAO)

        for (top, right, bottom, left) in rostos:
            top, right, bottom, left = top * 2, right * 2, bottom * 2, left * 2
            cv2.rectangle(frame, (left, top), (right, bottom), (255, 0, 0), 2)

        cv2.putText(frame, "Pressione ESPACO para iniciar", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow("Cadastro - Preview", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord(' '):
            em_preview = False
        elif key == ord('q'):
            cap.release()
            cv2.destroyAllWindows()
            return

    cv2.destroyWindow("Cadastro - Preview")

    print("--- FASE 2: CAPTURA DE FOTOS ---")
    print("Vire suavemente a cabeça para os lados/cima/baixo e varie um pouco a distância da câmera...")

    amostras_coletadas = 0
    ultima_captura = time.time()

    while amostras_coletadas < TOTAL_AMOSTRAS:
        ret, frame = cap.read()
        if not ret:
            break

        rgb = frame[:, :, ::-1]
        rostos = face_recognition.face_locations(rgb, model=MODELO_DETECCAO)
        agora = time.time()

        for (top, right, bottom, left) in rostos:
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

            if agora - ultima_captura >= INTERVALO_CAPTURA:
                amostras_coletadas += 1

                # Salva com uma margem ao redor do rosto (ajuda o modelo de embedding a alinhar melhor)
                margem = int((bottom - top) * 0.15)
                y1, y2 = max(0, top - margem), bottom + margem
                x1, x2 = max(0, left - margem), right + margem
                rosto_recortado = frame[y1:y2, x1:x2]

                caminho_foto = os.path.join(pasta_destino, f"{amostras_coletadas}.jpg")
                cv2.imwrite(caminho_foto, rosto_recortado)
                ultima_captura = agora
                print(f"Foto {amostras_coletadas}/{TOTAL_AMOSTRAS} salva com sucesso!")

        cv2.putText(frame, f"Fotos: {amostras_coletadas}/{TOTAL_AMOSTRAS}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        cv2.imshow("Cadastro - Capturando...", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("\nCaptura interrompida pelo usuário.")
            break

    cap.release()
    cv2.destroyAllWindows()
    print(f"\nCadastro concluído! {amostras_coletadas} imagens foram salvas em '{pasta_destino}'.")
    print("Rode 'python treinar.py' para atualizar o modelo com essa pessoa.")


if __name__ == "__main__":
    main()
