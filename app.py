import os
import cv2
import base64
import sqlite3
import re
import unicodedata
import numpy as np
import face_recognition
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
DB_FILE = os.path.join(BASE_DIR, "faces.db")
MINIMO_FOTOS_REQUERIDO = 50
TOLERANCIA = 0.48

os.makedirs(DATASET_DIR, exist_ok=True)

# Cache de encodings na memória RAM para acelerar o tempo real
ENCODINGS_CACHE = {"nomes": [], "vecs": []}

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            pasta TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS encodings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            encoding BLOB NOT NULL,
            caminho_foto TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS acessos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def recarregar_cache_encodings():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT nome, encoding FROM encodings")
    rows = cursor.fetchall()
    conn.close()

    nomes = []
    vecs = []
    for nome, raw_enc in rows:
        vec = np.frombuffer(raw_enc, dtype=np.float64)
        nomes.append(nome)
        vecs.append(vec)
    
    ENCODINGS_CACHE["nomes"] = nomes
    ENCODINGS_CACHE["vecs"] = vecs

init_db()
recarregar_cache_encodings()

def normalizar_nome(nome):
    if not nome:
        return ""
    nome_limpo = unicodedata.normalize('NFKD', str(nome)).encode('ASCII', 'ignore').decode('ASCII')
    nome_limpo = nome_limpo.lower().strip().replace(" ", "_")
    return re.sub(r'[^a-z0-9_]', '', nome_limpo)

def base64_to_cv2(b64_string):
    encoded_data = b64_string.split(',')[1]
    nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

def cv2_to_base64(img):
    _, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 70])
    b64 = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/jpeg;base64,{b64}"

def desenhar_marcador_opencv(frame, boxes, rotulo="ROSTO DETECTADO"):
    img = frame.copy()
    for (top, right, bottom, left) in boxes:
        # Moldura principal
        cv2.rectangle(img, (left, top), (right, bottom), (0, 255, 0), 2)
        
        # Caixas de canto para destaque do indicador
        d = 15
        cv2.line(img, (left, top), (left + d, top), (0, 255, 255), 3)
        cv2.line(img, (left, top), (left, top + d), (0, 255, 255), 3)
        cv2.line(img, (right, top), (right - d, top), (0, 255, 255), 3)
        cv2.line(img, (right, top), (right, top + d), (0, 255, 255), 3)
        
        # Etiqueta
        cv2.rectangle(img, (left, top - 25), (right, top), (0, 255, 0), cv2.FILLED)
        cv2.putText(img, rotulo, (left + 5, top - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
    return img

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/dados', methods=['GET'])
def obter_dados():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, pasta FROM usuarios")
    usuarios_db = cursor.fetchall()
    
    usuarios = []
    for u in usuarios_db:
        cursor.execute("SELECT COUNT(*) FROM encodings WHERE nome = ?", (u[1],))
        qtd_fotos = cursor.fetchone()[0]
        usuarios.append([u[0], u[1], u[2], qtd_fotos])

    cursor.execute("SELECT id, nome, datetime(data_hora, 'localtime') FROM acessos ORDER BY id DESC LIMIT 10")
    acessos = cursor.fetchall()
    conn.close()
    return jsonify({"usuarios": usuarios, "acessos": acessos})

@app.route('/api/cadastrar', methods=['POST'])
def cadastrar():
    data = request.json
    nome_raw = data.get('nome')
    img_b64 = data.get('image')

    usuario_id = normalizar_nome(nome_raw)
    if not usuario_id:
        return jsonify({"mensagem": "❌ Nome inválido!"}), 400

    pasta_destino = os.path.join(DATASET_DIR, usuario_id)
    os.makedirs(pasta_destino, exist_ok=True)

    frame = base64_to_cv2(img_b64)
    
    # Otimização de Performance: Redução da resolução para detecção rápida
    small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
    rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

    boxes_small = face_recognition.face_locations(rgb_small, model="hog")
    
    if not boxes_small:
        preview_b64 = cv2_to_base64(frame)
        return jsonify({"mensagem": "⚠️ Procurando rosto... Mantenha-se em frente à câmera.", "preview": preview_b64}), 400

    # Ajusta as coordenadas para a escala original do frame
    boxes = [(top*2, right*2, bottom*2, left*2) for (top, right, bottom, left) in boxes_small]

    rgb_full = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    encodings = face_recognition.face_encodings(rgb_full, boxes)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM encodings WHERE nome = ?", (usuario_id,))
    total_atual = cursor.fetchone()[0]
    proximo_num = total_atual + 1

    caminho_foto = os.path.join(pasta_destino, f"{proximo_num}.jpg")
    cv2.imwrite(caminho_foto, frame)

    blob_encoding = encodings[0].tobytes()
    cursor.execute("INSERT OR REPLACE INTO usuarios (nome, pasta) VALUES (?, ?)", (usuario_id, pasta_destino))
    cursor.execute("INSERT INTO encodings (nome, encoding, caminho_foto) VALUES (?, ?, ?)", 
                   (usuario_id, blob_encoding, caminho_foto))
    
    conn.commit()
    conn.close()

    recarregar_cache_encodings()

    rotulo = f"ROSTO CAPTURADO ({proximo_num}/{MINIMO_FOTOS_REQUERIDO})"
    frame_marcado = desenhar_marcador_opencv(frame, boxes, rotulo)
    preview_b64 = cv2_to_base64(frame_marcado)

    return jsonify({
        "mensagem": f" Capturada foto #{proximo_num}",
        "total": proximo_num,
        "preview": preview_b64
    })

@app.route('/api/adicionar_foto', methods=['POST'])
def adicionar_foto():
    data = request.json
    nome = normalizar_nome(data.get('nome'))
    img_b64 = data.get('image')

    if not nome:
        return jsonify({"mensagem": "❌ Nome não fornecido!"}), 400

    pasta_destino = os.path.join(DATASET_DIR, nome)
    os.makedirs(pasta_destino, exist_ok=True)

    frame = base64_to_cv2(img_b64)
    small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
    rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

    boxes_small = face_recognition.face_locations(rgb_small, model="hog")

    if not boxes_small:
        return jsonify({"mensagem": "⚠️ Procurando rosto...", "preview": cv2_to_base64(frame)}), 400

    boxes = [(top*2, right*2, bottom*2, left*2) for (top, right, bottom, left) in boxes_small]
    rgb_full = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    encodings = face_recognition.face_encodings(rgb_full, boxes)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM encodings WHERE nome = ?", (nome,))
    total_atual = cursor.fetchone()[0]
    proximo_num = total_atual + 1

    caminho_foto = os.path.join(pasta_destino, f"{proximo_num}.jpg")
    cv2.imwrite(caminho_foto, frame)

    blob_encoding = encodings[0].tobytes()
    cursor.execute("INSERT INTO encodings (nome, encoding, caminho_foto) VALUES (?, ?, ?)", 
                   (nome, blob_encoding, caminho_foto))
    conn.commit()
    conn.close()

    recarregar_cache_encodings()

    rotulo = f"ADICIONADA (#{proximo_num})"
    frame_marcado = desenhar_marcador_opencv(frame, boxes, rotulo)

    return jsonify({
        "mensagem": f" Foto #{proximo_num} salva!",
        "preview": cv2_to_base64(frame_marcado)
    })

@app.route('/api/reconhecer', methods=['POST'])
def reconhecer():
    data = request.json
    frame = base64_to_cv2(data.get('image'))
    
    nomes_conhecidos = ENCODINGS_CACHE["nomes"]
    encodings_conhecidos = ENCODINGS_CACHE["vecs"]

    if not encodings_conhecidos:
        return jsonify({"image": cv2_to_base64(frame)})

    # Otimização de Performance: Processamento em baixa resolução
    small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
    rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

    boxes_small = face_recognition.face_locations(rgb_small, model="hog")
    encodings_frame = face_recognition.face_encodings(rgb_small, boxes_small)

    for (top, right, bottom, left), encoding_atual in zip(boxes_small, encodings_frame):
        # Re-escalando para o tamanho original
        top *= 2
        right *= 2
        bottom *= 2
        left *= 2

        nome = "Desconhecido"
        cor = (0, 0, 255)

        distancias = face_recognition.face_distance(encodings_conhecidos, encoding_atual)
        if len(distancias) > 0:
            melhor_indice = int(np.argmin(distancias))
            if distancias[melhor_indice] <= TOLERANCIA:
                nome = nomes_conhecidos[melhor_indice]
                cor = (0, 255, 0)
                
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO acessos (nome) VALUES (?)", (nome,))
                conn.commit()
                conn.close()

        cv2.rectangle(frame, (left, top), (right, bottom), cor, 2)
        cv2.putText(frame, nome, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, cor, 2)

    return jsonify({"image": cv2_to_base64(frame)})

@app.route('/api/renomear', methods=['POST'])
def renomear():
    data = request.json
    nome_antigo = normalizar_nome(data.get('nome_antigo'))
    novo_nome = normalizar_nome(data.get('novo_nome'))

    if not novo_nome or not nome_antigo:
        return jsonify({"mensagem": "❌ Nomes inválidos fornecidos!"}), 400

    caminho_antigo = os.path.join(DATASET_DIR, nome_antigo)
    caminho_novo = os.path.join(DATASET_DIR, novo_nome)

    if os.path.exists(caminho_novo) and nome_antigo != novo_nome:
        return jsonify({"mensagem": f"❌ Já existe cadastro para '{novo_nome}'!"}), 400

    if os.path.exists(caminho_antigo):
        os.rename(caminho_antigo, caminho_novo)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET nome = ?, pasta = ? WHERE nome = ?", (novo_nome, caminho_novo, nome_antigo))
    cursor.execute("UPDATE encodings SET nome = ? WHERE nome = ?", (novo_nome, nome_antigo))
    cursor.execute("UPDATE acessos SET nome = ? WHERE nome = ?", (novo_nome, nome_antigo))
    conn.commit()
    conn.close()

    recarregar_cache_encodings()
    return jsonify({"mensagem": f" Nome alterado de '{nome_antigo}' para '{novo_nome}' no faces.db."})

@app.route('/api/deletar', methods=['POST'])
def deletar():
    nome = normalizar_nome(request.json.get('nome'))
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM usuarios WHERE nome = ?", (nome,))
    cursor.execute("DELETE FROM encodings WHERE nome = ?", (nome,))
    cursor.execute("DELETE FROM acessos WHERE nome = ?", (nome,))
    conn.commit()
    conn.close()

    recarregar_cache_encodings()
    return jsonify({"status": "sucesso"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)