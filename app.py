import os
import cv2
import base64
import sqlite3
import re
import unicodedata
import warnings
import shutil
import numpy as np
import face_recognition
from flask import Flask, render_template, request, jsonify

warnings.filterwarnings("ignore", category=UserWarning)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

app = Flask(
    __name__,
    static_folder=STATIC_DIR,
    static_url_path="/static",
    template_folder=TEMPLATES_DIR,
)

DATASET_DIR = os.path.join(BASE_DIR, "dataset")
DB_FILE = os.path.join(BASE_DIR, "faces.db")
MINIMO_FOTOS_REQUERIDO = 50
TOLERANCIA = 0.48

XML_LOCAL = os.path.join(BASE_DIR, "haarcascade_frontalface_default.xml")
if not os.path.exists(XML_LOCAL):
    print(f"Erro: Arquivo '{XML_LOCAL}' nao encontrado na pasta do projeto.")

face_cascade = cv2.CascadeClassifier(XML_LOCAL)

os.makedirs(DATASET_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

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
    try:
        if not b64_string or ',' not in b64_string:
            return None
        encoded_data = b64_string.split(',')[1]
        nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img
    except Exception:
        return None


def cv2_to_base64(img):
    # Otimização: Qualidade JPEG ajustada para 40 para codificação e transferência ultrarrápidas
    _, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 40])
    b64 = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/jpeg;base64,{b64}"


def desenhar_marcador_opencv(frame, boxes, rotulo="ROSTO DETECTADO"):
    img = frame.copy()
    for (top, right, bottom, left) in boxes:
        cv2.rectangle(img, (left, top), (right, bottom), (0, 255, 0), 2)

        d = 15
        cv2.line(img, (left, top), (left + d, top), (0, 255, 255), 3)
        cv2.line(img, (left, top), (left, top + d), (0, 255, 255), 3)
        cv2.line(img, (right, top), (right - d, top), (0, 255, 255), 3)
        cv2.line(img, (right, top), (right, top + d), (0, 255, 255), 3)

        cv2.rectangle(img, (left, top - 25), (right, top), (0, 255, 0), cv2.FILLED)
        cv2.putText(img, rotulo, (left + 5, top - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
    return img


def registrar_acesso(nome):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO acessos (nome) VALUES (?)", (nome,))
    conn.commit()
    conn.close()


def processar_captura(nome_raw, img_b64, permitir_criar_usuario):
    nome = normalizar_nome(nome_raw)
    if not nome:
        return {"status": 400, "mensagem": "Nome invalido!"}

    frame = base64_to_cv2(img_b64)
    if frame is None:
        return {"status": 400, "mensagem": "Imagem invalida recebida da camera."}

    pasta_destino = os.path.join(DATASET_DIR, nome)
    os.makedirs(pasta_destino, exist_ok=True)

    # 1. Redução do frame para aceleração do reconhecimento (50% do tamanho)
    small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
    rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
    
    boxes_small = face_recognition.face_locations(rgb_small, model="hog")

    if not boxes_small:
        return {
            "status": 400,
            "mensagem": "Procurando rosto... Mantenha-se em frente a camera.",
            "preview": cv2_to_base64(frame),
        }

    # 2. Otimização Crítica: Extração dos encodings no frame reduzido
    encodings = face_recognition.face_encodings(rgb_small, boxes_small)

    if not encodings:
        return {
            "status": 400,
            "mensagem": "Nao foi possivel extrair as caracteristicas do rosto. Tente novamente.",
            "preview": cv2_to_base64(frame),
        }

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    if not permitir_criar_usuario:
        cursor.execute("SELECT 1 FROM usuarios WHERE nome = ?", (nome,))
        if cursor.fetchone() is None:
            conn.close()
            return {"status": 400, "mensagem": "Usuario nao encontrado no faces.db!"}

    cursor.execute("SELECT COUNT(*) FROM encodings WHERE nome = ?", (nome,))
    total_atual = cursor.fetchone()[0]
    proximo_num = total_atual + 1

    caminho_foto = os.path.join(pasta_destino, f"{proximo_num}.jpg")
    cv2.imwrite(caminho_foto, frame)

    blob_encoding = encodings[0].tobytes()
    cursor.execute("INSERT OR REPLACE INTO usuarios (nome, pasta) VALUES (?, ?)", (nome, pasta_destino))
    cursor.execute(
        "INSERT INTO encodings (nome, encoding, caminho_foto) VALUES (?, ?, ?)",
        (nome, blob_encoding, caminho_foto),
    )
    conn.commit()
    conn.close()

    # 3. Otimização: Recarrega o cache do SQLite apenas quando atingir a meta do lote ou finalizar
    if proximo_num >= MINIMO_FOTOS_REQUERIDO:
        recarregar_cache_encodings()

    boxes = [(top * 2, right * 2, bottom * 2, left * 2) for (top, right, bottom, left) in boxes_small]
    rotulo = f"CAPTURADA ({proximo_num}/{MINIMO_FOTOS_REQUERIDO})"
    frame_marcado = desenhar_marcador_opencv(frame, boxes, rotulo)

    return {
        "status": 200,
        "mensagem": f"Capturada foto #{proximo_num}",
        "total": proximo_num,
        "preview": cv2_to_base64(frame_marcado),
    }


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
    data = request.json or {}
    resultado = processar_captura(data.get('nome'), data.get('image'), permitir_criar_usuario=True)
    status = resultado.pop("status")
    return jsonify(resultado), status


@app.route('/api/adicionar_foto', methods=['POST'])
def adicionar_foto():
    data = request.json or {}
    resultado = processar_captura(data.get('nome'), data.get('image'), permitir_criar_usuario=False)
    status = resultado.pop("status")
    return jsonify(resultado), status


@app.route('/api/reconhecer', methods=['POST'])
def reconhecer():
    data = request.json or {}
    frame = base64_to_cv2(data.get('image'))
    if frame is None:
        return jsonify({"image": None, "erro": "Imagem invalida."}), 400

    nomes_conhecidos = ENCODINGS_CACHE["nomes"]
    encodings_conhecidos = ENCODINGS_CACHE["vecs"]

    if not encodings_conhecidos:
        return jsonify({"image": cv2_to_base64(frame)})

    small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
    gray_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)

    faces = face_cascade.detectMultiScale(
        gray_small, scaleFactor=1.1, minNeighbors=3, minSize=(30, 30)
    )

    nomes_reconhecidos = []

    if len(faces) > 0:
        boxes_small = [(y, x + w, y + h, x) for (x, y, w, h) in faces]
        rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        encodings_frame = face_recognition.face_encodings(rgb_small, boxes_small)

        for (top, right, bottom, left), encoding_atual in zip(boxes_small, encodings_frame):
            top_full, right_full, bottom_full, left_full = top * 2, right * 2, bottom * 2, left * 2

            nome = "Desconhecido"
            cor = (0, 0, 255)

            distancias = face_recognition.face_distance(encodings_conhecidos, encoding_atual)
            if len(distancias) > 0:
                melhor_indice = int(np.argmin(distancias))
                if distancias[melhor_indice] <= TOLERANCIA:
                    nome = nomes_conhecidos[melhor_indice]
                    cor = (0, 255, 0)
                    registrar_acesso(nome)
                    nomes_reconhecidos.append(nome)

            cv2.rectangle(frame, (left_full, top_full), (right_full, bottom_full), cor, 2)
            cv2.putText(frame, nome, (left_full, top_full - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, cor, 2)

    return jsonify({"image": cv2_to_base64(frame), "reconhecidos": nomes_reconhecidos})


@app.route('/api/renomear', methods=['POST'])
def renomear():
    data = request.json or {}
    nome_antigo = normalizar_nome(data.get('antigo_nome'))
    novo_nome = normalizar_nome(data.get('novo_nome'))

    if not novo_nome or not nome_antigo:
        return jsonify({"mensagem": "Nomes inválidos fornecidos!"}), 400

    caminho_antigo = os.path.join(DATASET_DIR, nome_antigo)
    caminho_novo = os.path.join(DATASET_DIR, novo_nome)

    if os.path.exists(caminho_novo) and nome_antigo != novo_nome:
        return jsonify({"mensagem": f"Já existe cadastro para '{novo_nome}'!"}), 400

    if os.path.exists(caminho_antigo):
        try:
            os.rename(caminho_antigo, caminho_novo)
        except Exception as e:
            return jsonify({"mensagem": f"Erro ao renomear pasta: {str(e)}"}), 500

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET nome = ?, pasta = ? WHERE nome = ?", (novo_nome, caminho_novo, nome_antigo))
    cursor.execute("UPDATE encodings SET nome = ? WHERE nome = ?", (novo_nome, nome_antigo))
    cursor.execute("UPDATE acessos SET nome = ? WHERE nome = ?", (novo_nome, nome_antigo))
    conn.commit()
    conn.close()

    recarregar_cache_encodings()
    return jsonify({"mensagem": f"Nome alterado de '{nome_antigo}' para '{novo_nome}' no faces.db."})


@app.route('/api/deletar', methods=['POST'])
def deletar():
    data = request.json or {}
    nome = normalizar_nome(data.get('nome'))

    if not nome:
        return jsonify({"mensagem": "Nome invalido!"}), 400

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM usuarios WHERE nome = ?", (nome,))
    cursor.execute("DELETE FROM encodings WHERE nome = ?", (nome,))
    cursor.execute("DELETE FROM acessos WHERE nome = ?", (nome,))
    conn.commit()
    conn.close()

    pasta_usuario = os.path.join(DATASET_DIR, nome)
    if os.path.exists(pasta_usuario):
        shutil.rmtree(pasta_usuario)

    recarregar_cache_encodings()
    return jsonify({"status": "sucesso"})


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000, threaded=True)
