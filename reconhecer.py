import os
import cv2
import numpy as np
import face_recognition
from database import FaceDatabase

XML_LOCAL = "haarcascade_frontalface_default.xml"
TOLERANCIA = 0.5
INDEX_CAMERA = 0

def reconhecer():
    db = FaceDatabase()
    
    if not os.path.exists(XML_LOCAL):
        print(f"❌ Arquivo {XML_LOCAL} não encontrado!")
        return
    
    # Carrega dados do banco
    encodings_conhecidos, nomes_conhecidos, user_ids = db.get_all_encodings()
    
    if not encodings_conhecidos:
        print("❌ Nenhum rosto cadastrado no banco! Cadastre alguém primeiro.")
        return
    
    print(f"✅ Carregados {len(encodings_conhecidos)} encodings de {len(set(nomes_conhecidos))} usuários")
    
    classificador_rosto = cv2.CascadeClassifier(XML_LOCAL)
    cap = cv2.VideoCapture(INDEX_CAMERA)
    
    if not cap.isOpened():
        print(f"❌ Câmera não encontrada!")
        return
    
    print("\n🔍 Reconhecimento ATIVO. Pressione 'q' para sair.")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_pequeno = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        cinza = cv2.cvtColor(frame_pequeno, cv2.COLOR_BGR2GRAY)
        
        faces_detectadas = classificador_rosto.detectMultiScale(
            cinza, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
        )
        
        if len(faces_detectadas) > 0:
            boxes = []
            for (x, y, w, h) in faces_detectadas:
                boxes.append((y, x + w, y + h, x))
            
            frame_rgb = cv2.cvtColor(frame_pequeno, cv2.COLOR_BGR2RGB)
            encodings_frame = face_recognition.face_encodings(frame_rgb, boxes)
            
            for (top, right, bottom, left), encoding_atual in zip(boxes, encodings_frame):
                top, right, bottom, left = top * 2, right * 2, bottom * 2, left * 2
                
                nome = "Desconhecido"
                cor = (0, 0, 255)
                user_id = None
                
                if encodings_conhecidos:
                    distancias = face_recognition.face_distance(encodings_conhecidos, encoding_atual)
                    melhor_indice = int(np.argmin(distancias))
                    melhor_distancia = distancias[melhor_indice]
                    
                    if melhor_distancia <= TOLERANCIA:
                        nome = nomes_conhecidos[melhor_indice]
                        user_id = user_ids[melhor_indice]
                        cor = (0, 255, 0)
                        confidence = 1 - melhor_distancia
                        nome = f"{nome} ({confidence:.2f})"
                        
                        # Registra no log
                        db.add_recognition_log(user_id, confidence)
                
                cv2.rectangle(frame, (left, top), (right, bottom), cor, 2)
                cv2.putText(frame, nome, (left, top - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, cor, 2)
        
        cv2.imshow("Reconhecimento Facial - SQLite", frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    reconhecer()
