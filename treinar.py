import face_recognition
import os
import cv2
import numpy as np
from database import FaceDatabase

DATASET_DIR = "dataset"


def treinar():
    # 1. Inicializa o banco de dados SQLite
    db = FaceDatabase()

    if not os.path.isdir(DATASET_DIR):
        print(f"Erro: Pasta '{DATASET_DIR}' nao encontrada. Cadastre pessoas antes de treinar.")
        return

    # Lista e ordena todas as subpastas (pastas de usuários) dentro de dataset
    todas_pessoas = sorted([p for p in os.listdir(DATASET_DIR) if os.path.isdir(os.path.join(DATASET_DIR, p))])
    
    if not todas_pessoas:
        print("Erro: Nenhuma pessoa cadastrada no dataset. Rode o cadastro primeiro.")
        return

    # --- SISTEMA DE SELEÇÃO POR NOME OU ID ---
    print("\n--- USUARIOS ENCONTRADOS NO DATASET ---")
    for idx, pessoa in enumerate(todas_pessoas):
        print(f"[{idx}] {pessoa}")
    print("---------------------------------------")

    entrada = input("\nDigite o NOME da pessoa ou o numero do [ID] que deseja treinar (or 'todos'): ").strip()

    # Define qual pessoa será processada com base na escolha do usuário
    pessoas_para_treinar = []
    if entrada.lower() == 'todos':
        pessoas_para_treinar = todas_pessoas
    elif entrada.isdigit():
        id_escolhido = int(entrada)
        if 0 <= id_escolhido < len(todas_pessoas):
            pessoas_para_treinar = [todas_pessoas[id_escolhido]]
        else:
            print("ID invalido.")
            return
    else:
        # Busca por nome (aceita maiúsculas/minúsculas)
        match = [p for p in todas_pessoas if p.lower() == entrada.lower()]
        if match:
            pessoas_para_treinar = match
        else:
            print(f"Erro: Usuario '{entrada}' nao foi encontrado.")
            return

    # Carrega o classificador usando o arquivo local que você criou
    xml_local = "haarcascade_frontalface_default.xml"
    if not os.path.exists(xml_local):
        print(f"Erro: O arquivo '{xml_local}' nao esta na pasta do projeto.")
        return
        
    classificador_rosto = cv2.CascadeClassifier(xml_local)

    # --- PROCESSAMENTO DAS SUBPASTAS INTEGRADO AO SQLITE ---
    for nome in pessoas_para_treinar:
        pasta_pessoa = os.path.join(DATASET_DIR, nome)
        arquivos = os.listdir(pasta_pessoa)
        print(f"\nProcessando subpasta '{nome}' ({len(arquivos)} arquivos)...")

        # Verifica se o usuário já existe no SQLite ou cria um novo perfil
        usuario_existente = db.get_user_by_name(nome)
        if usuario_existente:
            # Pega o ID numérico do usuário existente (primeiro elemento da tupla)
            user_id = usuario_existente[0]
            # Limpa assinaturas antigas deste usuário específico para evitar duplicidade
            db.delete_user(nome)
            user_id = db.add_user(nome)
        else:
            user_id = db.add_user(nome)
            
        if not user_id:
            print(f"Erro ao registrar o usuario '{nome}' no banco de dados. Pulando subpasta.")
            continue

        fotos_aproveitadas = 0
        for arquivo in arquivos:
            if not arquivo.lower().endswith(('.png', '.jpg', '.jpeg', '.jfif', '.webp')):
                continue

            caminho_imagem = os.path.join(pasta_pessoa, arquivo)
            
            # Abre o arquivo via array de bytes para evitar erros de caracteres no Windows
            imagem_bgr = cv2.imdecode(np.fromfile(caminho_imagem, dtype=np.uint8), cv2.IMREAD_COLOR)
            if imagem_bgr is None:
                continue

            # Detecta a face usando OpenCV (Tons de Cinza)
            cinza = cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2GRAY)
            faces_detectadas = classificador_rosto.detectMultiScale(cinza, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

            if len(faces_detectadas) == 0:
                continue 

            # Transforma as coordenadas (x, y, w, h) do OpenCV para (top, right, bottom, left) da dlib
            boxes = []
            for (x, y, w, h) in faces_detectadas:
                boxes.append((y, x + w, y + h, x))

            # Converte de BGR para RGB antes de mandar para o face_recognition
            imagem_rgb = cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2RGB)
            
            try:
                encodings = face_recognition.face_encodings(imagem_rgb, boxes)
                for encoding in encodings:
                    # SALVAMENTO NO BANCO: Manda a matriz direto para a tabela do SQLite através da sua classe
                    db.add_encoding(user_id, encoding)
                    fotos_aproveitadas += 1
            except Exception as e:
                print(f"  [Erro na imagem {arquivo}]: {e}")
                continue

        print(f"  -> {fotos_aproveitadas} rosto(s) extraido(s) e sincronizado(s) no SQLite para '{nome}'.")

    print("\nProcesso concluido de forma bem-sucedida! Banco de dados atualizado.")


if __name__ == "__main__":
    treinar()
