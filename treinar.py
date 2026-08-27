import face_recognition
import os
import pickle
import cv2
import numpy as np

DATASET_DIR = "dataset"
ENCODINGS_FILE = "encodings.pickle"


def treinar():
    if not os.path.isdir(DATASET_DIR):
        print(f"❌ Pasta '{DATASET_DIR}' não encontrada. Cadastre pessoas antes de treinar.")
        return

    # Lista e ordena todas as subpastas (pastas de usuários) dentro de dataset
    todas_pessoas = sorted([p for p in os.listdir(DATASET_DIR) if os.path.isdir(os.path.join(DATASET_DIR, p))])
    
    if not todas_pessoas:
        print("❌ Nenhuma pessoa cadastrada no dataset. Rode o cadastro primeiro.")
        return

    # --- SISTEMA DE SELEÇÃO POR NOME OU ID ---
    print("\n--- USUÁRIOS ENCONTRADOS NO DATASET ---")
    for idx, pessoa in enumerate(todas_pessoas):
        print(f"[{idx}] {pessoa}")
    print("---------------------------------------")

    entrada = input("\nDigite o NOME da pessoa ou o número do [ID] que deseja treinar (ou 'todos'): ").strip()

    # Define qual pessoa será processada com base na escolha do usuário
    pessoas_para_treinar = []
    if entrada.lower() == 'todos':
        pessoas_para_treinar = todas_pessoas
    elif entrada.isdigit():
        id_escolhido = int(entrada)
        if 0 <= id_escolhido < len(todas_pessoas):
            pessoas_para_treinar = [todas_pessoas[id_escolhido]]
        else:
            print("❌ ID inválido.")
            return
    else:
        # Busca por nome (aceita maiúsculas/minúsculas)
        match = [p for p in todas_pessoas if p.lower() == entrada.lower()]
        if match:
            pessoas_para_treinar = match
        else:
            print(f"❌ Usuário '{entrada}' não foi encontrado.")
            return

    # Carrega os encodings antigos para não apagar o treino de outros usuários
    dados_existentes = {"encodings": [], "names": []}
    if os.path.exists(ENCODINGS_FILE):
        try:
            with open(ENCODINGS_FILE, "rb") as f:
                dados_existentes = pickle.load(f)
        except Exception:
            pass

    encodings_finais = list(dados_existentes["encodings"])
    nomes_finais = list(dados_existentes["names"])

    # Remove os registros antigos das pessoas selecionadas para evitar dados duplicados
    for p_treinar in pessoas_para_treinar:
        indices_para_manter = [i for i, nome in enumerate(nomes_finais) if nome.lower() != p_treinar.lower()]
        encodings_finais = [encodings_finais[i] for i in indices_para_manter]
        nomes_finais = [nomes_finais[i] for i in indices_para_manter]

    # Carrega o classificador usando o arquivo local que você criou
    xml_local = "haarcascade_frontalface_default.xml"
    if not os.path.exists(xml_local):
        print(f"❌ Erro: O arquivo '{xml_local}' não está na pasta do projeto.")
        return
        
    classificador_rosto = cv2.CascadeClassifier(xml_local)

    # --- PROCESSAMENTO DAS SUBPASTAS ---
    for nome in pessoas_para_treinar:
        pasta_pessoa = os.path.join(DATASET_DIR, nome)
        arquivos = os.listdir(pasta_pessoa)
        print(f"\nProcessando subpasta '{nome}' ({len(arquivos)} arquivos)...")

        fotos_aproveitadas = 0
        for arquivo in arquivos:
            # Filtro para aceitar extensões maiúsculas ou minúsculas
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

            # CORREÇÃO CRÍTICA: Converte de BGR para RGB antes de mandar para o face_recognition
            imagem_rgb = cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2RGB)
            
            try:
                encodings = face_recognition.face_encodings(imagem_rgb, boxes)
                for encoding in encodings:
                    encodings_finais.append(encoding)
                    nomes_finais.append(nome)
                    fotos_aproveitadas += 1
            except Exception as e:
                print(f"  [Erro na imagem {arquivo}]: {e}")
                continue

        print(f"  -> {fotos_aproveitadas} rosto(s) extraído(s) com sucesso para '{nome}'.")

    if not encodings_finais:
        print("\n❌ Nenhum rosto pôde ser treinado nas pastas selecionadas.")
        return

    # Grava o arquivo .pickle final atualizado
    dados_salvar = {"encodings": encodings_finais, "names": nomes_finais}
    with open(ENCODINGS_FILE, "wb") as f:
        pickle.dump(dados_salvar, f)

    print(f"\nSucesso! O arquivo '{ENCODINGS_FILE}' foi gerado/atualizado com sucesso.")


if __name__ == "__main__":
    treinar()
