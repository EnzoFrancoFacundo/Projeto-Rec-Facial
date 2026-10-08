import os
import cv2
import base64
import sqlite3
import re
import unicodedata
import warnings
import shutil
import time
import numpy as np
import face_recognition
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps

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

# Chave secreta e configurações de sessão
app.secret_key = "sua_chave_secreta_super_segura_aqui"
app.config['SESSION_PERMANENT'] = False

DATASET_DIR = os.path.join(BASE_DIR, "dataset")
DB_FILE = os.path.join(BASE_DIR, "faces.db")
MINIMO_FOTOS_REQUERIDO = 30
TOLERANCIA = 0.48

# Haar Cascade Fallback
XML_LOCAL = os.path.join(BASE_DIR, "haarcascade_frontalface_default.xml")
if not os.path.exists(XML_LOCAL):
    XML_LOCAL = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")

face_cascade = cv2.CascadeClassifier(XML_LOCAL)

os.makedirs(DATASET_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

app.config['TEMPLATES_AUTO_RELOAD'] = True


@app.context_processor
def injetar_assets():
    # Acrescenta ?v=<data de modificação> nos arquivos estáticos para evitar cache velho
    def asset(filename):
        try:
            v = int(os.path.getmtime(os.path.join(STATIC_DIR, filename)))
        except OSError:
            v = 0
        return url_for('static', filename=filename, v=v)
    return {"asset": asset}


ENCODINGS_CACHE = {"nomes": [], "vecs": [], "matriz": None}
ULTIMOS_ACESSOS = {}


def normalizar_nome(nome):
    if not nome:
        return ""
    nome_limpo = unicodedata.normalize('NFKD', str(nome)).encode('ASCII', 'ignore').decode('ASCII')
    nome_limpo = nome_limpo.lower().strip().replace(" ", "_")
    return re.sub(r'[^a-z0-9_]', '', nome_limpo)


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            pasta TEXT NOT NULL,
            senha TEXT DEFAULT '123456',
            role TEXT DEFAULT 'user',
            funcao TEXT DEFAULT 'Pesquisador',
            ativo INTEGER DEFAULT 1
        )
    """)

    cursor.execute("PRAGMA table_info(usuarios)")
    colunas = [col[1] for col in cursor.fetchall()]
    if "senha" not in colunas:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN senha TEXT DEFAULT '123456'")
    if "role" not in colunas:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN role TEXT DEFAULT 'user'")
    if "funcao" not in colunas:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN funcao TEXT DEFAULT 'Pesquisador'")
    if "ativo" not in colunas:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN ativo INTEGER DEFAULT 1")

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

    # Usuário admin padrão
    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE nome = 'admin'")
    if cursor.fetchone()[0] == 0:
        pasta_admin = os.path.join(DATASET_DIR, "admin")
        os.makedirs(pasta_admin, exist_ok=True)
        cursor.execute(
            "INSERT INTO usuarios (nome, pasta, senha, role, funcao) VALUES ('admin', ?, 'admin123', 'admin', 'Administrador')",
            (pasta_admin,)
        )
    else:
        cursor.execute("UPDATE usuarios SET role = 'admin', ativo = 1 WHERE nome = 'admin'")

    conn.commit()
    conn.close()


def recarregar_cache_encodings():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Usuários inativos não entram no cache, então não são reconhecidos
    cursor.execute("""
        SELECT e.nome, e.encoding
        FROM encodings e
        JOIN usuarios u ON u.nome = e.nome
        WHERE COALESCE(u.ativo, 1) = 1
    """)
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
    ENCODINGS_CACHE["matriz"] = np.array(vecs, dtype=np.float64) if vecs else None


def adicionar_ao_cache(nome, vec):
    vec = np.asarray(vec, dtype=np.float64)
    ENCODINGS_CACHE["nomes"].append(nome)
    ENCODINGS_CACHE["vecs"].append(vec)
    if ENCODINGS_CACHE["matriz"] is None:
        ENCODINGS_CACHE["matriz"] = vec.reshape(1, -1)
    else:
        ENCODINGS_CACHE["matriz"] = np.vstack([ENCODINGS_CACHE["matriz"], vec])


init_db()
recarregar_cache_encodings()


# --- DECORADORES DE SEGURANÇA ---

FUNCAO_PADRAO = "Pesquisador"


def limpar_funcao(valor):
    funcao = (valor or "").strip()[:60]
    return funcao or FUNCAO_PADRAO


def usuario_esta_ativo(nome):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COALESCE(ativo, 1) FROM usuarios WHERE nome = ?", (nome,))
    row = cursor.fetchone()
    conn.close()
    return bool(row and row[0])


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            return redirect(url_for('login'))
        # Se o usuário foi inativado enquanto estava logado, derruba a sessão
        if not usuario_esta_ativo(session['usuario']):
            session.clear()
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session or session.get('role') != 'admin':
            return jsonify({"mensagem": "Acesso negado. Requer privilégios de Administrador."}), 403
        if not usuario_esta_ativo(session['usuario']):
            session.clear()
            return jsonify({"mensagem": "Sua conta está inativa."}), 403
        return f(*args, **kwargs)
    return decorated_function


# --- AUXILIARES DE PROCESSAMENTO DE IMAGEM ---

def base64_to_cv2(b64_string):
    try:
        if not b64_string or ',' not in b64_string:
            return None
        encoded_data = b64_string.split(',')[1]
        nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
        return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    except Exception:
        return None


def cv2_to_base64(img):
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
    agora = time.time()
    if nome in ULTIMOS_ACESSOS and (agora - ULTIMOS_ACESSOS[nome]) < 10:
        return
    ULTIMOS_ACESSOS[nome] = agora

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO acessos (nome) VALUES (?)", (nome,))
    conn.commit()
    conn.close()


def processar_captura(nome_raw, img_b64, permitir_criar_usuario, funcao_raw=None):
    nome = normalizar_nome(nome_raw)
    if not nome:
        return {"status": 400, "mensagem": "Nome inválido!"}

    frame = base64_to_cv2(img_b64)
    if frame is None:
        return {"status": 400, "mensagem": "Imagem inválida recebida da câmera."}

    pasta_destino = os.path.join(DATASET_DIR, nome)
    os.makedirs(pasta_destino, exist_ok=True)

    small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
    rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
    
    boxes_small = face_recognition.face_locations(rgb_small, model="hog")

    if not boxes_small:
        return {
            "status": 400,
            "mensagem": "Procurando rosto... Mantenha-se em frente à câmera.",
            "preview": cv2_to_base64(frame),
        }

    encodings = face_recognition.face_encodings(rgb_small, boxes_small)

    if not encodings:
        return {
            "status": 400,
            "mensagem": "Não foi possível extrair características faciais.",
            "preview": cv2_to_base64(frame),
        }

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    if not permitir_criar_usuario:
        cursor.execute("SELECT 1 FROM usuarios WHERE nome = ?", (nome,))
        if cursor.fetchone() is None:
            conn.close()
            return {"status": 400, "mensagem": "Usuário não encontrado no banco de dados!"}

    cursor.execute("SELECT COUNT(*) FROM encodings WHERE nome = ?", (nome,))
    total_atual = cursor.fetchone()[0]
    proximo_num = total_atual + 1

    caminho_foto = os.path.join(pasta_destino, f"{proximo_num}.jpg")
    cv2.imwrite(caminho_foto, frame)

    blob_encoding = encodings[0].tobytes()
    
    cursor.execute(
        "INSERT OR IGNORE INTO usuarios (nome, pasta, funcao) VALUES (?, ?, ?)",
        (nome, pasta_destino, limpar_funcao(funcao_raw)),
    )
    cursor.execute("SELECT COALESCE(ativo, 1) FROM usuarios WHERE nome = ?", (nome,))
    esta_ativo = bool(cursor.fetchone()[0])
    cursor.execute(
        "INSERT INTO encodings (nome, encoding, caminho_foto) VALUES (?, ?, ?)",
        (nome, blob_encoding, caminho_foto),
    )
    conn.commit()
    conn.close()

    if esta_ativo:
        adicionar_ao_cache(nome, encodings[0])

    boxes = [(top * 2, right * 2, bottom * 2, left * 2) for (top, right, bottom, left) in boxes_small]
    rotulo = f"CAPTURADA ({proximo_num}/{MINIMO_FOTOS_REQUERIDO})"
    frame_marcado = desenhar_marcador_opencv(frame, boxes, rotulo)

    return {
        "status": 200,
        "mensagem": f"Capturada foto #{proximo_num}",
        "total": proximo_num,
        "preview": cv2_to_base64(frame_marcado),
    }


# --- ROTAS DE AUTENTICAÇÃO ---

@app.route('/login', methods=['GET'])
def login():
    return render_template('login.html')


@app.route('/api/login_senha', methods=['POST'])
def login_senha():
    data = request.json or {}
    usuario_raw = data.get('usuario', '').strip()
    senha_input = data.get('senha', '')
    tipo_acesso = data.get('tipo_acesso', 'user')

    if not usuario_raw or not senha_input:
        return jsonify({"sucesso": False, "mensagem": "Preencha todos os campos!"}), 400

    usuario_input = normalizar_nome(usuario_raw)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT nome, role, COALESCE(ativo, 1) FROM usuarios WHERE (nome = ? OR nome = ?) AND senha = ?", 
        (usuario_input, usuario_raw, senha_input)
    )
    user = cursor.fetchone()
    conn.close()

    if not user:
        return jsonify({"sucesso": False, "mensagem": "Usuário ou senha inválidos!"}), 401

    user_nome, user_role, user_ativo = user

    if not user_ativo:
        return jsonify({"sucesso": False, "mensagem": "Conta inativa. Procure um administrador."}), 403

    if tipo_acesso == 'admin' and user_role != 'admin':
        return jsonify({"sucesso": False, "mensagem": "Acesso negado: conta sem permissão de administrador."}), 403

    session['usuario'] = user_nome
    session['role'] = user_role

    return jsonify({"sucesso": True, "redirect": url_for('index')})


@app.route('/api/cadastrar_usuario', methods=['POST'])
def cadastrar_usuario():
    data = request.json or {}
    usuario_raw = data.get('usuario', '').strip()
    senha = data.get('senha', '')
    confirmar_senha = data.get('confirmar_senha', '')
    role = data.get('role', 'user')
    funcao = limpar_funcao(data.get('funcao'))

    if not usuario_raw or not senha or not confirmar_senha:
        return jsonify({"sucesso": False, "mensagem": "Preencha todos os campos obrigatórios!"}), 400

    if senha != confirmar_senha:
        return jsonify({"sucesso": False, "mensagem": "As senhas não coincidem!"}), 400

    if len(senha) < 4:
        return jsonify({"sucesso": False, "mensagem": "A senha deve ter no mínimo 4 caracteres!"}), 400

    usuario_norm = normalizar_nome(usuario_raw)
    if not usuario_norm:
        return jsonify({"sucesso": False, "mensagem": "Nome de usuário inválido!"}), 400

    pasta_usuario = os.path.join(DATASET_DIR, usuario_norm)
    os.makedirs(pasta_usuario, exist_ok=True)

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM usuarios WHERE nome = ?", (usuario_norm,))
        usuario_existente = cursor.fetchone()

        if usuario_existente:
            cursor.execute(
                "UPDATE usuarios SET senha = ?, role = ?, pasta = ?, funcao = ? WHERE nome = ?",
                (senha, role, pasta_usuario, funcao, usuario_norm)
            )
        else:
            cursor.execute(
                "INSERT INTO usuarios (nome, pasta, senha, role, funcao) VALUES (?, ?, ?, ?, ?)",
                (usuario_norm, pasta_usuario, senha, role, funcao)
            )

        conn.commit()
        conn.close()
    except Exception as e:
        return jsonify({"sucesso": False, "mensagem": f"Erro no banco de dados: {str(e)}"}), 500

    return jsonify({"sucesso": True, "mensagem": f"Conta salva com sucesso!"})


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# --- ROTA PRINCIPAL DA APLICAÇÃO ---

@app.route('/')
@login_required
def index():
    user_role = session.get('role', 'user')
    return render_template(
        'index.html', 
        usuario=session.get('usuario'), 
        role=user_role,
        body_class='user-role' if user_role != 'admin' else '',
        minimo_fotos=MINIMO_FOTOS_REQUERIDO
    )


# --- ROTAS DA API INTERNA ---
@app.route('/api/editar_usuario', methods=['POST'])
@admin_required
def editar_usuario():
    data = request.json or {}
    nome = normalizar_nome(data.get('nome'))
    funcao = limpar_funcao(data.get('funcao'))

    if not nome:
        return jsonify({"mensagem": "Usuário inválido!"}), 400

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET funcao = ? WHERE nome = ?", (funcao, nome))
    alterados = cursor.rowcount
    conn.commit()
    conn.close()

    if alterados == 0:
        return jsonify({"mensagem": "Usuário não encontrado!"}), 404
    return jsonify({"mensagem": "Função atualizada com sucesso.", "funcao": funcao})


@app.route('/api/alternar_status', methods=['POST'])
@admin_required
def alternar_status():
    data = request.json or {}
    nome = normalizar_nome(data.get('nome'))
    ativo = 1 if data.get('ativo') else 0

    if not nome:
        return jsonify({"mensagem": "Usuário inválido!"}), 400
    if not ativo and (nome == 'admin' or nome == session.get('usuario')):
        return jsonify({"mensagem": "Você não pode inativar a sua própria conta nem o admin principal."}), 400

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET ativo = ? WHERE nome = ?", (ativo, nome))
    alterados = cursor.rowcount
    conn.commit()
    conn.close()

    if alterados == 0:
        return jsonify({"mensagem": "Usuário não encontrado!"}), 404

    recarregar_cache_encodings()
    estado = "ativado" if ativo else "inativado"
    return jsonify({"mensagem": f"Usuário '{nome}' {estado} com sucesso.", "ativo": bool(ativo)})


@app.route('/api/dados', methods=['GET'])
@login_required
def obter_dados():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, pasta, role, funcao, COALESCE(ativo, 1) FROM usuarios")
    usuarios_db = cursor.fetchall()

    usuarios = []
    for u in usuarios_db:
        cursor.execute("SELECT COUNT(*) FROM encodings WHERE nome = ?", (u[1],))
        qtd_fotos = cursor.fetchone()[0]
        usuarios.append([u[0], u[1], u[2], qtd_fotos, u[3], u[4], u[5]])

    cursor.execute("SELECT id, nome, datetime(data_hora, 'localtime') FROM acessos ORDER BY id DESC LIMIT 50")
    acessos = cursor.fetchall()
    conn.close()

    return jsonify({"usuarios": usuarios, "acessos": acessos})


@app.route('/api/estatisticas', methods=['GET'])
@login_required
def estatisticas():
    from datetime import date, timedelta
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM usuarios")
    total = c.fetchone()[0]
    hoje_sql = "date(data_hora,'localtime') = date('now','localtime')"
    c.execute(f"SELECT COUNT(*) FROM acessos WHERE {hoje_sql}")
    hoje = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM acessos WHERE date(data_hora,'localtime') = date('now','localtime','-1 day')")
    ontem = c.fetchone()[0]
    c.execute("SELECT nome, strftime('%H:%M', data_hora,'localtime') FROM acessos ORDER BY id DESC LIMIT 1")
    ultimo = c.fetchone()
    c.execute("SELECT date(data_hora,'localtime'), COUNT(*) FROM acessos "
              "WHERE date(data_hora,'localtime') >= date('now','localtime','-6 days') GROUP BY 1")
    por_dia = dict(c.fetchall())
    conn.close()

    nomes = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    semana = []
    for i in range(6, -1, -1):
        d = date.today() - timedelta(days=i)
        semana.append({"dia": nomes[d.weekday()], "valor": por_dia.get(d.isoformat(), 0)})

    variacao = round((hoje - ontem) / ontem * 100) if ontem else (100 if hoje else 0)
    return jsonify({
        "total_usuarios": total, "deteccoes_hoje": hoje, "variacao": variacao,
        "ultimo": {"nome": ultimo[0], "hora": ultimo[1]} if ultimo else None,
        "semana": semana,
    })


@app.route('/api/cadastrar', methods=['POST'])
@admin_required
def cadastrar():
    data = request.json or {}
    resultado = processar_captura(data.get('nome'), data.get('image'), permitir_criar_usuario=True, funcao_raw=data.get('funcao'))
    status = resultado.pop("status")
    return jsonify(resultado), status


@app.route('/api/adicionar_foto', methods=['POST'])
@admin_required
def adicionar_foto():
    data = request.json or {}
    resultado = processar_captura(data.get('nome'), data.get('image'), permitir_criar_usuario=False)
    status = resultado.pop("status")
    return jsonify(resultado), status


@app.route('/api/reconhecer', methods=['POST'])
@login_required
def reconhecer():
    data = request.json or {}
    frame = base64_to_cv2(data.get('image'))
    if frame is None:
        return jsonify({"image": None, "erro": "Imagem inválida."}), 400

    nomes_conhecidos = ENCODINGS_CACHE["nomes"]
    matriz_conhecidos = ENCODINGS_CACHE["matriz"]

    if matriz_conhecidos is None or len(matriz_conhecidos) == 0:
        return jsonify({"image": cv2_to_base64(frame), "reconhecidos": []})

    small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
    gray_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)

    faces = face_cascade.detectMultiScale(
        gray_small, scaleFactor=1.2, minNeighbors=3, minSize=(30, 30)
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

            distancias = np.linalg.norm(matriz_conhecidos - encoding_atual, axis=1)
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
@admin_required
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
    return jsonify({"mensagem": f"Nome alterado com sucesso para '{novo_nome}'."})


@app.route('/api/deletar', methods=['POST'])
@admin_required
def deletar():
    data = request.json or {}
    nome = normalizar_nome(data.get('nome'))

    if not nome:
        return jsonify({"mensagem": "Nome inválido!"}), 400

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
    return jsonify({"status": "sucesso", "mensagem": f"Usuário '{nome}' removido com sucesso."})


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000, threaded=True)