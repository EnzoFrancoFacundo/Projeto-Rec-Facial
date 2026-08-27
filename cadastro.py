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
        
        for (top, right, bottom, left) in rostos:
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            
            if agora - ultima_captura >= INTERVALO_CAPTURA:
                amostras_coletadas += 1
                
                margem = int((bottom - top) * 0.15)
                y1, y2 = max(0, top - margem), bottom + margem
                x1, x2 = max(0, left - margem), right + margem
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
        
        cv2.putText(frame, f"Fotos: {amostras_coletadas}/{TOTAL_AMOSTRAS}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        cv2.imshow("Cadastro - Capturando...", frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    print(f"\n✅ Cadastro concluído! Dados salvos no SQLite.")

if __name__ == "__main__":
    main()
