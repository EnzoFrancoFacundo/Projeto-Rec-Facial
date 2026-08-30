import cv2
import face_recognition
import os
import time
import unicodedata
import re
from database import FaceDatabase

TOTAL_AMOSTRAS = 50
INTERVALO_CAPTURA = 0.75
INDEX_CAMERA = 0
DATASET_DIR = "dataset"
MODELO_DETECCAO = "hog"

def normalizar_nome(nome):
    nome_limpo = unicodedata.normalize('NFKD', nome).encode('ASCII', 'ignore').decode('ASCII')
    nome_limpo = nome_limpo.lower().strip().replace(" ", "_")
    nome_limpo = re.sub(r'[^a-z0-9_]', '', nome_limpo)
    return nome_limpo

def main():
    db = FaceDatabase()
    
    nome_usuario = input("Digite o Nome da pessoa a ser cadastrada: ").strip()
    if not nome_usuario:
        print("❌ Nome inválido!")
        return
    
    usuario_id = normalizar_nome(nome_usuario)
    
    # Verifica se já existe no banco
    usuario_existente = db.get_user_by_name(usuario_id)
    if usuario_existente:
        print(f"\n❌ Usuário '{usuario_id}' já está cadastrado!")
        opcao = input("Deseja adicionar mais fotos? (s/n): ").strip().lower()
        if opcao != 's':
            return
        
        user_id = usuario_existente[0]
        db.delete_encodings_by_user(user_id)  # Remove encodings antigos

        # Pega o ID numérico que veio do banco (tupla)
        user_id = usuario_existente[0]
        
        # Correção da função: remove os encodings antigos via CASCADE ao apagar e recriar o usuário
        db.delete_user(usuario_id)
        user_id = db.add_user(usuario_id)

    else:
        user_id = db.add_user(usuario_id)
        if not user_id:
            print("❌ Erro ao criar usuário!")
            return
    
    # Cria pasta para fotos
    pasta_destino = os.path.join(DATASET_DIR, usuario_id)
    os.makedirs(pasta_destino, exist_ok=True)
    
    cap = cv2.VideoCapture(INDEX_CAMERA)
    if not cap.isOpened():
        print(f"❌ Erro ao abrir a câmera!")
        return
    
    print("\nPressione [ESPAÇO] para começar a capturar (ou 'q' para sair)")
    
    em_preview = True
    while em_preview:
        ret, frame = cap.read()
        if not ret:
            break
        

        # Reduz pela metade para detecção super rápida no preview

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
    
    print("\nCapturando fotos...")
    amostras_coletadas = 0
    ultima_captura = time.time()
    
    while amostras_coletadas < TOTAL_AMOSTRAS:
        ret, frame = cap.read()
        if not ret:
            break
        

        rgb = frame[:, :, ::-1]
        rostos = face_recognition.face_locations(rgb, model=MODELO_DETECCAO)
        agora = time.time()
        

        # Reduz a escala durante a captura também (elimina o delay do retângulo)
        rgb_pequeno = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)[:, :, ::-1]
        rostos = face_recognition.face_locations(rgb_pequeno, model=MODELO_DETECCAO)
        agora = time.time()
        
        # Desenha caixas multiplicando os valores de volta para o tamanho original do frame

        for (top, right, bottom, left) in rostos:
            top, right, bottom, left = top * 2, right * 2, bottom * 2, left * 2
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            
            if agora - ultima_captura >= INTERVALO_CAPTURA:
                amostras_coletadas += 1
                


                # Recorta o rosto com uma margem de segurança na imagem original (alta resolução)

                margem = int((bottom - top) * 0.15)
                y1, y2 = max(0, top - margem), min(frame.shape[0], bottom + margem)
                x1, x2 = max(0, left - margem), min(frame.shape[1], right + margem)
                rosto_recortado = frame[y1:y2, x1:x2]
                
                caminho_foto = os.path.join(pasta_destino, f"{amostras_coletadas}.jpg")
                cv2.imwrite(caminho_foto, rosto_recortado)
                

                # Extrai e salva encoding imediatamente
                try:
                    encoding = face_recognition.face_encodings(rgb, [(top, right, bottom, left)])[0]
                    db.add_encoding(user_id, encoding)
                except:
                    pass
                
                ultima_captura = agora
                print(f"📸 Foto {amostras_coletadas}/{TOTAL_AMOSTRAS}")

                ultima_captura = agora
                print(f"Foto salva: {amostras_coletadas}/{TOTAL_AMOSTRAS}")

        
        cv2.putText(frame, f"Fotos: {amostras_coletadas}/{TOTAL_AMOSTRAS}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        cv2.imshow("Cadastro - Capturando...", frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    

    cap.release()
    cv2.destroyAllWindows()
    print(f"\n✅ Cadastro concluído! Dados salvos no SQLite.")

    # Fecha a janela e desliga a câmera imediatamente para liberar processamento
    cap.release()
    cv2.destroyAllWindows()
    
    #  PROCESSAMENTO ASSÍNCRONO / EM SEGUNDO PLANO
    print("\n" + "="*50)
    print("Captura encerrada com sucesso!")
    print("Iniciando mapeamento facial em lote (Batch Processing)...")
    print("="*50)
    
        #  BLOCO CORRIGIDO DO PROCESSAMENTO EM LOTE (BATE COM O SEU DATABASE)
    encodings_gerados = 0
    for i in range(1, amostras_coletadas + 1):
        caminho_foto = os.path.join(pasta_destino, f"{i}.jpg")
        if not os.path.exists(caminho_foto):
            continue
            
        frame_salvo = cv2.imread(caminho_foto)
        if frame_salvo is None:
            continue
            
        # Converte para RGB (padrão obrigatório da dlib / face_recognition)
        rgb_salvo = cv2.cvtColor(frame_salvo, cv2.COLOR_BGR2RGB)
        
        # Como a foto salva já é o recorte do rosto, o detector 'hog' acha facilmente
        localizacao_rosto = face_recognition.face_locations(rgb_salvo, model=MODELO_DETECCAO)
        
        if localizacao_rosto:
            try:
                # CORREÇÃO DA SINTAXE: Passamos a lista pura retornada pelo face_locations
                # e pegamos o primeiro índice [0] do resultado retornado pelo face_encodings
                encoding = face_recognition.face_encodings(rgb_salvo, known_face_locations=localizacao_rosto)[0]
                
                # Salva os bytes binários no SQLite
                db.add_encoding(user_id, encoding)
                encodings_gerados += 1
                print(f" Mapeado com sucesso: foto {i}/{amostras_coletadas}")
            except Exception as e:
                print(f"⚠️ Erro ao gerar biometria para a foto {i}: {e}")
        else:
            # Se o recorte ficou muito próximo e o 'hog' falhou, tenta extrair de forma direta da imagem
            try:
                encoding = face_recognition.face_encodings(rgb_salvo)[0]
                db.add_encoding(user_id, encoding)
                encodings_gerados += 1
                print(f" Mapeado de forma direta: foto {i}/{amostras_coletadas}")
            except Exception as e:
                print(f"❌ Rosto não identificado na foto {i}. Ignorando frame.")

    print("\n" + "="*50)
    print(f"Processo Concluído!")
    print(f"Imagens armazenadas na pasta: {pasta_destino}")
    print(f"Biometrias salvas com sucesso no SQLite: {encodings_gerados}/{amostras_coletadas}")
    print("="*50)


if __name__ == "__main__":
    main()
