import os
import cv2
import pickle
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
ENCODINGS_FILE = os.path.join(BASE_DIR, "encodings.pickle")
DB_FILE = os.path.join(BASE_DIR, "banco.db")
TOLERANCIA = 0.5

os.makedirs(DATASET_DIR, exist_ok=True)

# -----------------------------------------------------------------------------
# BANCO DE DADOS (SQLite)
# -----------------------------------------------------------------------------
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
        CREATE TABLE IF NOT EXISTS acessos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# -----------------------------------------------------------------------------
# AUXILIARES DE IMAGEM E NOME
# -----------------------------------------------------------------------------
def normalizar_nome(nome):
    nome_limpo = unicodedata.normalize('NFKD', nome).encode('ASCII', 'ignore').decode('ASCII')
    nome_limpo = nome_limpo.lower().strip().replace(" ", "_")
    return re.sub(r'[^a-z0-9_]', '', nome_limpo)

def base64_to_cv2(b64_string):
    encoded_data = b64_string.split(',')[1]
    nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

def cv2_to_base64(img):
    _, buffer = cv2.imencode('.jpg', img)
    b64 = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/jpeg;base64,{b64}"

# -----------------------------------------------------------------------------
# ROTAS E API
# -----------------------------------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/dados', methods=['GET'])
def obter_dados():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, pasta FROM usuarios")
    usuarios = cursor.fetchall()
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
    pasta_destino = os.path.join(DATASET_DIR, usuario_id)
    os.makedirs(pasta_destino, exist_ok=True)

    frame = base64_to_cv2(img_b64)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Extrai o encoding da imagem
    boxes = face_recognition.face_locations(rgb, model="hog")
    encodings = face_recognition.face_encodings(rgb, boxes)

    if not encodings:
        return jsonify({"mensagem": "❌ Nenhuma face foi detectada na foto!"}), 400

    # Salva a imagem no disco
    caminho_foto = os.path.join(pasta_destino, "1.jpg")
    cv2.imwrite(caminho_foto, frame)

    # Carrega/Atualiza o arquivo encodings.pickle
    dados = {"encodings": [], "names": []}
    if os.path.exists(ENCODINGS_FILE):
        with open(ENCODINGS_FILE, "rb") as f:
            dados = pickle.load(f)

    dados["encodings"].append(encodings[0])
    dados["names"].append(usuario_id)

    with open(ENCODINGS_FILE, "wb") as f:
        pickle.dump(dados, f)

    # Registra no SQLite
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO usuarios (nome, pasta) VALUES (?, ?)", (usuario_id, pasta_destino))
    conn.commit()
    conn.close()

    return jsonify({"mensagem": f" Cadastrado com sucesso como '{usuario_id}'!"})

@app.route('/api/reconhecer', methods=['POST'])
def reconhecer():
    data = request.json
    frame = base64_to_cv2(data.get('image'))
    
    if not os.path.exists(ENCODINGS_FILE):
        return jsonify({"image": cv2_to_base64(frame)})

    with open(ENCODINGS_FILE, "rb") as f:
        dados_conhecidos = pickle.load(f)

    encodings_conhecidos = dados_conhecidos["encodings"]
    nomes_conhecidos = dados_conhecidos["names"]

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    boxes = face_recognition.face_locations(rgb, model="hog")
    encodings_frame = face_recognition.face_encodings(rgb, boxes)

    for (top, right, bottom, left), encoding_atual in zip(boxes, encodings_frame):
        nome = "Desconhecido"
        cor = (0, 0, 255)

        if encodings_conhecidos:
            distancias = face_recognition.face_distance(encodings_conhecidos, encoding_atual)
            melhor_indice = int(np.argmin(distancias))
            
            if distancias[melhor_indice] <= TOLERANCIA:
                nome = nomes_conhecidos[melhor_indice]
                cor = (0, 255, 0)
                
                # Registra o acesso no banco de dados
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO acessos (nome) VALUES (?)", (nome,))
                conn.commit()
                conn.close()

        cv2.rectangle(frame, (left, top), (right, bottom), cor, 2)
        cv2.putText(frame, nome, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, cor, 2)

    return jsonify({"image": cv2_to_base64(frame)})

@app.route('/api/deletar', methods=['POST'])
def deletar():
    nome = request.json.get('nome')
    
    # 1. Remove do SQLite
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM usuarios WHERE nome = ?", (nome,))
    conn.commit()
    conn.close()

    # 2. Atualiza Pickle
    if os.path.exists(ENCODINGS_FILE):
        with open(ENCODINGS_FILE, "rb") as f:
            dados = pickle.load(f)

        indices = [i for i, n in enumerate(dados["names"]) if n.lower() != nome.lower()]
        dados_atualizados = {
            "encodings": [dados["encodings"][i] for i in indices],
            "names": [dados["names"][i] for i in indices]
        }
        with open(ENCODINGS_FILE, "wb") as f:
            pickle.dump(dados_atualizados, f)

    return jsonify({"status": "sucesso"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)