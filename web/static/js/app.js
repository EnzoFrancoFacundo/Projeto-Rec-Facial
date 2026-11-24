// ===== Equivalente ao App.tsx: estado + navegação + componentes =====
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const sleep = ms => new Promise(r => setTimeout(r, ms));
const MIN = window.MIN_FOTOS;
const ico = (n, s = 20) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><use href="#i-${n}"/></svg>`;
const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const api = async (url, body) => {
  const r = await fetch(url, body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {});
  return { ok: r.ok, data: await r.json().catch(() => ({})) };
};

const avatar = nome => `<span class="avatar">${esc(nome.slice(0, 2).toUpperCase())}</span>`;
const recordHTML = a => `<div class="record">${avatar(a[1])}<div class="record-name"><strong>${esc(a[1])}</strong><span>Entrada principal</span></div><time>${a[2].slice(11, 16)}</time></div>`;

// ===== Pop-up padronizado =====
const POPUP_ICONS = { success: 'check', error: 'error', warn: 'warn', info: 'info' };
const POPUP_TITLES = { success: 'Sucesso', error: 'Erro', warn: 'Atenção', info: 'Informação' };

function popup(msg, tipo = 'info', titulo = null) {
  return new Promise(resolve => {
    const el = $('#popup');
    const box = el.querySelector('.popup');
    $('#popup-icon').innerHTML = ico(POPUP_ICONS[tipo] || 'info', 22);
    $('#popup-title').textContent = titulo || POPUP_TITLES[tipo] || 'Aviso';
    $('#popup-msg').textContent = msg;

    const ok = $('#popup-ok');
    const cancel = $('#popup-cancel');

    cancel.style.display = 'none';
    ok.textContent = 'OK';

    box.className = 'popup ' + tipo;
    el.hidden = false;
    el.style.display = 'grid';

    const fechar = () => {
      el.hidden = true;
      el.style.display = '';
      ok.onclick = null;
      resolve(true);
    };
    ok.onclick = fechar;
    ok.focus();
  });
}

function confirmar(msg, titulo = 'Confirmar') {
  return new Promise(resolve => {
    const el = $('#popup');
    const box = el.querySelector('.popup');
    $('#popup-icon').innerHTML = ico('warn', 22);
    $('#popup-title').textContent = titulo;
    $('#popup-msg').textContent = msg;

    const ok = $('#popup-ok');
    const cancel = $('#popup-cancel');

    cancel.style.display = '';
    ok.textContent = 'Confirmar';
    cancel.textContent = 'Cancelar';

    box.className = 'popup warn';
    el.hidden = false;
    el.style.display = 'grid';

    const fim = v => {
      el.hidden = true;
      el.style.display = '';
      ok.onclick = cancel.onclick = null;
      resolve(v);
    };
    ok.onclick = () => fim(true);
    cancel.onclick = () => fim(false);
    cancel.focus();
  });
}

// ESC fecha popup
document.addEventListener('keydown', e => {
  const el = document.getElementById('popup');
  if (!el || el.hidden) return;
  if (e.key === 'Escape') {
    const cancel = $('#popup-cancel');
    const ok = $('#popup-ok');
    if (cancel && cancel.style.display !== 'none' && cancel.onclick) cancel.onclick();
    else if (ok && ok.onclick) ok.onclick();
  }
});
// Clique no backdrop fecha popup
document.addEventListener('click', e => {
  const el = document.getElementById('popup');
  if (el && !el.hidden && e.target === el) {
    const cancel = $('#popup-cancel');
    const ok = $('#popup-ok');
    if (cancel && cancel.style.display !== 'none' && cancel.onclick) cancel.onclick();
    else if (ok && ok.onclick) ok.onclick();
  }
});

// ===== Tema (claro / escuro) =====
// ===== Tema (claro / escuro / automático) =====
const mqClaro = window.matchMedia('(prefers-color-scheme: light)');
const temaDoSistema = () => (mqClaro.matches ? 'light' : 'dark');
function modoTema() {
  try { return localStorage.getItem('tema_modo') || localStorage.getItem('tema') || 'dark'; } catch (e) { return 'dark'; }
}
function pintarBotoesTema(tema) {
  const html = tema === 'light' ? ico('moon', 18) : ico('sun', 18);
  $$('.theme-toggle').forEach(btn => { btn.innerHTML = html; });
}
function aplicarTema(tema) {
  document.documentElement.setAttribute('data-theme', tema);
  try { localStorage.setItem('tema', tema); } catch (e) {}
  pintarBotoesTema(tema);
}
let _temaTimer;
function definirModoTema(modo) {
  try { localStorage.setItem('tema_modo', modo); } catch (e) {}
  const root = document.documentElement;
  root.classList.add('theme-transition');
  aplicarTema(modo === 'auto' ? temaDoSistema() : modo);
  clearTimeout(_temaTimer);
  _temaTimer = setTimeout(() => root.classList.remove('theme-transition'), 500);
  marcarOpcoes();
}
// Botão do topo: alterna entre claro e escuro (e sai do modo automático)
function alternarTema() {
  const atual = document.documentElement.getAttribute('data-theme') || 'dark';
  definirModoTema(atual === 'light' ? 'dark' : 'light');
}
// No modo automático, acompanha o sistema em tempo real
mqClaro.addEventListener?.('change', () => { if (modoTema() === 'auto') aplicarTema(temaDoSistema()); });
document.addEventListener('click', e => {
  const btn = e.target.closest('.theme-toggle');
  if (btn) { e.preventDefault(); alternarTema(); }
});
document.addEventListener('DOMContentLoaded', () => {
  aplicarTema(document.documentElement.getAttribute('data-theme') || 'dark');
});

// useState(page, people)
const state = { page: 'dashboard', people: [], acessos: [] };

function setPage(p) {
  state.page = p;
  $$('.page').forEach(s => s.hidden = s.id !== `page-${p}`);
  $$('.nav-item').forEach(b => b.classList.toggle('active', b.dataset.go === p));
  if (p !== 'recognition') stopRecognition();
  ({ dashboard: loadDashboard, users: loadUsers, recognition: loadFeed, registros: loadRegistros }[p] || (() => {}))();
  pintarBotoesTema(document.documentElement.getAttribute('data-theme') || 'dark');
}

async function loadData() {
  const { data } = await api('/api/dados');
  state.people = (data.usuarios || []).map(u => ({ id: u[0], nome: u[1], fotos: u[3], funcao: u[5] || 'Pesquisador', ativo: u[6] !== 0 }));
  state.acessos = data.acessos || [];
}

// ---- Dashboard() + WeekChart() ----
async function loadDashboard() {
  const [{ data: s }] = await Promise.all([api('/api/estatisticas'), loadData()]);
  $('#s-users').textContent = s.total_usuarios;
  $('#s-users-note').textContent = 'usuários no banco';
  $('#s-today').textContent = s.deteccoes_hoje;
  $('#s-today-note').textContent = `${s.variacao >= 0 ? '+' : ''}${s.variacao}% comparado a ontem`;
  $('#s-last').textContent = s.ultimo ? s.ultimo.hora : '–';
  $('#s-last-note').textContent = s.ultimo ? s.ultimo.nome : 'Sem registros';
  $('#recent-list').innerHTML = state.acessos.slice(0, 4).map(recordHTML).join('') || '<p class="muted">Nenhum registro ainda.</p>';
  weekChart(s.semana);
}

function weekChart(sem) {
  const max = Math.max(...sem.map(d => d.valor), 1);
  const top = sem.reduce((a, b) => b.valor > a.valor ? b : a);
  const barras = sem.map(d => {
    const alturaPct = (d.valor / max) * 100;
    const destaque = d === top && top.valor > 0;
    return `<div class="bar-col">
        <span class="bar-value">${d.valor}</span>
        <div class="bar-track">
          <div class="bar-fill${destaque ? ' peak' : ''}" style="height:${alturaPct}%"></div>
        </div>
        <span class="bar-label">${d.dia}</span>
      </div>`;
  }).join('');
  $('#week-chart').innerHTML = `<div class="bar-chart">${barras}</div>`;
  $('#peak-title').textContent = top.valor ? `Maior pico: ${top.dia}` : 'Sem detecções na semana';
  $('#peak-sub').textContent = top.valor ? `${top.valor} detecções` : '';
}
// ---- Registros() ----
const regState = { filtro: 'recentes', dados: [] };

async function loadRegistros() {
  const { data } = await api(`/api/registros?filtro=${regState.filtro}`);
  regState.dados = data.registros || [];
  renderRegistros();
}

function renderRegistros() {
  const q = ($('#reg-search').value || '').toLowerCase().trim();
  const list = regState.dados.filter(r => r[1].toLowerCase().includes(q));
  
  $('#reg-count').textContent = `${list.length} registro(s) exibido(s)`;
  $('#reg-empty').hidden = list.length > 0;
  $('#reg-rows').innerHTML = list.map(r => {
    const [id, nome, dataHora] = r;
    const data = dataHora.slice(0, 10);
    const hora = dataHora.slice(11, 16);
    const [ano, mes, dia] = data.split('-');
    const dataFmt = `${dia}/${mes}/${ano}`;
    return `<tr>
      <td><div class="user-cell">${avatar(nome)}<strong>${esc(nome)}</strong></div></td>
      <td class="muted">#${id}</td>
      <td class="muted">${dataFmt}</td>
      <td><time>${hora}</time></td>
    </tr>`;
  }).join('');
}

// ---- Users() ----
async function loadUsers() { await loadData(); renderUsers(); }
function renderUsers() {
  const q = $('#user-search').value.toLowerCase();
  const list = state.people.filter(p => `${p.nome} ${p.id}`.toLowerCase().includes(q));
  $('#user-count').textContent = `${list.length} de ${state.people.length} registros exibidos`;
  $('#user-empty').hidden = list.length > 0;
  $('#user-rows').innerHTML = list.map(p => {
    const protegido = p.nome === 'admin' || p.nome === window.USUARIO;
    return `<tr${p.ativo ? '' : ' class="inactive-row"'}><td><div class="user-cell">${avatar(p.nome)}<strong>${esc(p.nome)}</strong></div></td>
      <td class="muted">#${p.id}</td><td class="muted">${p.fotos}/${MIN}</td>
      <td>${esc(p.funcao)}</td>
      <td><span class="status ${p.ativo ? 'on' : 'off'}"><i></i>${p.ativo ? 'Ativo' : 'Inativo'}</span></td>
      <td class="admin-only"><div class="row-actions"><button title="Ver fotos" data-act="gallery" data-nome="${esc(p.nome)}">${ico('image', 17)}</button><button title="Editar" data-act="edit" data-nome="${esc(p.nome)}">${ico('edit', 17)}</button>
      <button title="${protegido ? 'Não é possível inativar esta conta' : (p.ativo ? 'Inativar' : 'Ativar')}" data-act="toggle" data-nome="${esc(p.nome)}" data-ativo="${p.ativo ? 1 : 0}"${protegido ? ' disabled' : ''}>${ico('power', 17)}</button>
      <button class="danger" title="Excluir" data-act="del" data-nome="${esc(p.nome)}">${ico('trash', 17)}</button></div></td></tr>`;
  }).join('');
}

async function toggleUser(nome, ativoAtual) {
  const ativar = !ativoAtual;
  if (!ativar) {
    const ok = await confirmar(`Inativar ${nome}? Essa pessoa não conseguirá entrar nem será reconhecida pela câmera.`, 'Inativar usuário');
    if (!ok) return;
  }
  const { data } = await api('/api/alternar_status', { nome, ativo: ativar });
  popup(data.mensagem, 'success');
  loadUsers();
}
async function removeUser(nome) {
  const ok = await confirmar(`Excluir ${nome}? Esta ação não poderá ser desfeita.`, 'Excluir usuário');
  if (!ok) return;
  const { data } = await api('/api/deletar', { nome });
  popup(data.mensagem, 'success');
  loadUsers();
}

// ---- Galeria de fotos ----
const G = { nome: null };

async function abrirGaleria(nome) {
  G.nome = nome;
  $('#g-title').textContent = nome;
  $('#g-grid').innerHTML = '';
  $('#g-count').textContent = 'Carregando...';
  $('#g-empty').hidden = true;
  $('#gallery-modal').hidden = false;
  await carregarGaleria();
}
function fecharGaleria() {
  $('#g-zoom').hidden = true;
  $('#gallery-modal').hidden = true;
  G.nome = null;
}
async function carregarGaleria() {
  if (!G.nome) return;
  const { ok, data } = await api(`/api/fotos?nome=${encodeURIComponent(G.nome)}`);
  if (!ok) return popup(data.mensagem || 'Não foi possível carregar as fotos.', 'error');
  const fotos = data.fotos || [];
  $('#g-count').textContent = `${fotos.length} foto(s) · recomendado: ${MIN}`;
  $('#g-empty').hidden = fotos.length > 0;
  $('#g-grid').innerHTML = fotos.map(f => `<figure class="gallery-item">
    <button type="button" class="gallery-thumb" data-act="zoom-foto" data-id="${f.id}" title="Ampliar">
      <img src="/api/foto/${f.id}" loading="lazy" alt="Foto ${f.numero}" onerror="this.parentElement.classList.add('missing')">
    </button>
        <figcaption>
      <div class="photo-meta">
        <span>#${f.numero}</span>
        <small>${f.data ? `${f.data} · ${f.hora}` : 'Data indisponível'}</small>
      </div>
      <button type="button" title="Excluir foto" data-act="del-foto" data-id="${f.id}">${ico('trash', 15)}</button>
    </figcaption></figure>`).join('');
}
function abrirZoom(id) {
  $('#g-zoom-img').src = `/api/foto/${id}?full=1`;
  $('#g-zoom').hidden = false;
}
async function removerFoto(id) {
  const ok = await confirmar('Excluir esta foto? Ela deixará de ser usada no reconhecimento e não poderá ser recuperada.', 'Excluir foto');
  if (!ok) return;
  const { ok: sucesso, data } = await api('/api/deletar_foto', { id });
  if (!sucesso) return popup(data.mensagem || 'Não foi possível excluir a foto.', 'error');
  await carregarGaleria();
  loadData().then(() => { if (state.page === 'users') renderUsers(); });
  if (data.total < MIN) {
    popup(`${data.nome} agora tem ${data.total} foto(s). O recomendado é ter ${MIN} para um bom reconhecimento.`, 'warn');
  } else {
    popup(data.mensagem, 'success');
  }
}
// Fecha só ao clicar no fundo escuro
$('#gallery-modal').onmousedown = e => { if (e.target === e.currentTarget) fecharGaleria(); };
// ESC: fecha primeiro o zoom, depois a galeria (o popup de confirmação tem prioridade)
document.addEventListener('keydown', e => {
  if (e.key !== 'Escape') return;
  const pop = document.getElementById('popup');
  if (pop && !pop.hidden) return;
  if (!$('#g-zoom').hidden) $('#g-zoom').hidden = true;
  else if (!$('#gallery-modal').hidden) fecharGaleria();
});

// ---- Recognition() ----
const rec = { on: false, stream: null, faces: [] };
const _grabCanvas = document.createElement('canvas');
const grab = (video, w = 480) => {
  const c = _grabCanvas; c.width = w; c.height = Math.round(w * video.videoHeight / video.videoWidth) || 360;
  c.getContext('2d').drawImage(video, 0, 0, c.width, c.height); return c.toDataURL('image/jpeg', 0.6);
};
async function loadFeed() { await loadData(); $('#feed-list').innerHTML = state.acessos.slice(0, 8).map(recordHTML).join(''); }

function drawFaces() {
  const v = $('#rec-video'), cv = $('#rec-canvas'), ctx = cv.getContext('2d');
  const W = cv.clientWidth, H = cv.clientHeight, dpr = window.devicePixelRatio || 1;
  if (cv.width !== W * dpr || cv.height !== H * dpr) { cv.width = W * dpr; cv.height = H * dpr; }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H);
  if (!rec.on || !v.videoWidth) return;
  const sc = Math.max(W / v.videoWidth, H / v.videoHeight);
  const dw = v.videoWidth * sc, dh = v.videoHeight * sc, ox = (W - dw) * 0.5, oy = (H - dh) * 0.2;
  const now = performance.now();
  rec.faces = rec.faces.filter(f => now - f.visto < 500);
  for (const f of rec.faces) {
    f.cur = f.cur.map((c, i) => c + (f.alvo[i] - c) * 0.35);
    const [x, y, w, h] = f.cur, cor = f.ok ? '#00ff00' : '#ff0000';
    ctx.strokeStyle = cor; ctx.lineWidth = 2; ctx.strokeRect(ox + x * dw, oy + y * dh, w * dw, h * dh);
    ctx.fillStyle = cor; ctx.font = '600 14px sans-serif';
    const rotulo = (f.ok && f.funcao) ? `${f.nome} · ${f.funcao}` : f.nome;
    ctx.fillText(rotulo, ox + x * dw, oy + y * dh - 8);
  }
}
function atualizarFaces(novas) {
  const now = performance.now(), usadas = new Set();
  for (const n of novas) {
    const cx = n.box[0] + n.box[2] / 2, cy = n.box[1] + n.box[3] / 2;
    let melhor = null, dist = 0.2;
    for (const f of rec.faces) {
      if (usadas.has(f)) continue;
      const d = Math.hypot(f.alvo[0] + f.alvo[2] / 2 - cx, f.alvo[1] + f.alvo[3] / 2 - cy);
      if (d < dist) { dist = d; melhor = f; }
    }
    if (melhor) {
      melhor.alvo = n.box;
      melhor.nome = n.nome;
      melhor.funcao = n.funcao;
      melhor.ok = n.ok;
      melhor.visto = now;
      usadas.add(melhor);
    } else {
      const f = { cur: n.box.slice(), alvo: n.box, nome: n.nome, funcao: n.funcao, ok: n.ok, visto: now };
      rec.faces.push(f);
      usadas.add(f);
    }
  }
}
function loopDesenho() { if (!rec.on) return; drawFaces(); requestAnimationFrame(loopDesenho); }

async function startRecognition() {
  try { rec.stream = await navigator.mediaDevices.getUserMedia({ video: true }); }
  catch { return popup('Não foi possível acessar a câmera.', 'error'); }
  const v = $('#rec-video'); v.srcObject = rec.stream; await v.play(); v.classList.add('on');
  rec.on = true; rec.faces = []; setRecUI(true); loopDesenho();
  while (rec.on) {
    const { ok, data } = await api('/api/reconhecer', { image: grab(v) });
    if (ok && rec.on) {
      atualizarFaces(data.faces || []);
      const reconhecido = (data.faces || []).find(f => f.ok);
      $('#rec-who').hidden = !reconhecido;
      if (reconhecido) {
        $('#rec-name').textContent = reconhecido.nome;
        const funcao = reconhecido.funcao || '';
        $('#rec-funcao').textContent = funcao;
        $('#rec-sep').hidden = !funcao;
        $('#rec-time').textContent = new Date().toLocaleTimeString('pt-BR');
      }
    } else if (!ok) await sleep(300);
  }
}
function stopRecognition() {
  rec.on = false; rec.faces = []; rec.stream?.getTracks().forEach(t => t.stop()); rec.stream = null; setRecUI(false);
  const cv = $('#rec-canvas'); cv.getContext('2d').clearRect(0, 0, cv.width, cv.height);
}
function setRecUI(on) {
  $('#rec-view').classList.toggle('paused', !on);
  $('#rec-state').className = on ? 'live' : ''; $('#rec-state').innerHTML = `<i></i>${on ? 'AO VIVO' : 'PAUSADO'}`;
  $('#rec-cam').textContent = on ? 'Câmera conectada' : 'Câmera desconectada';
  $('#rec-btn').className = on ? 'stop-button' : 'primary-button';
  $('#rec-btn').textContent = on ? 'Pausar reconhecimento' : 'Iniciar reconhecimento';
  if (!on) $('#rec-who').hidden = true;
}
setInterval(() => state.page === 'recognition' && rec.on && loadFeed(), 5000);

// ---- Settings() ----
const PREFS = {
  get(k, pad) { try { const v = localStorage.getItem(k); return v === null ? pad : v; } catch (e) { return pad; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} },
};

function aplicarFonte(v) {
  const root = document.documentElement;
  if (v === 'grande' || v === 'muito-grande') root.setAttribute('data-fonte', v);
  else root.removeAttribute('data-fonte');
  PREFS.set('fonte', v);
}
function aplicarContraste(on) {
  const root = document.documentElement;
  if (on) root.setAttribute('data-contraste', 'alto'); else root.removeAttribute('data-contraste');
  PREFS.set('contraste', on ? '1' : '0');
}
function marcarOpcoes() {
  const fonte = PREFS.get('fonte', 'normal');
  $$('[data-setting="fonte"] button').forEach(b => b.classList.toggle('active', b.dataset.v === fonte));
  const modo = modoTema();
  $$('[data-setting="tema"] button').forEach(b => b.classList.toggle('active', b.dataset.v === modo));
}

document.addEventListener('click', e => {
  const b = e.target.closest('[data-setting] button');
  if (!b) return;
  const tipo = b.closest('[data-setting]').dataset.setting;
  if (tipo === 'fonte') { aplicarFonte(b.dataset.v); marcarOpcoes(); }
  if (tipo === 'tema') definirModoTema(b.dataset.v);
});

$('#cfg-contraste').checked = PREFS.get('contraste', '0') === '1';
$('#cfg-contraste').onchange = e => aplicarContraste(e.target.checked);

$('#cfg-notify').checked = PREFS.get('notify', '1') !== '0';
$('#cfg-notify').onchange = e => PREFS.set('notify', e.target.checked ? '1' : '0');

$('#cfg-backup').onclick = () => popup('Preparando o backup. O download começa em instantes; com muitas fotos pode levar um pouco mais.', 'info', 'Backup');

marcarOpcoes();

// ---- Notificações em tempo real ----
const _avisados = new Map();
function notificarReconhecido(nome, funcao) {
  if (PREFS.get('notify', '1') === '0') return;
  const agora = Date.now();
  if (agora - (_avisados.get(nome) || 0) < 10000) return;   // no máximo 1 aviso a cada 10 s por pessoa
  _avisados.set(nome, agora);

  let pilha = $('#toast-stack');
  if (!pilha) {
    pilha = document.createElement('div');
    pilha.id = 'toast-stack';
    pilha.className = 'toast-stack';
    pilha.setAttribute('aria-live', 'polite');
    document.body.appendChild(pilha);
  }
  const t = document.createElement('div');
  t.className = 'toast-item';
  t.innerHTML = `<span class="toast-ico">${ico('check', 16)}</span><div><strong>${esc(nome)}</strong><small>${esc(funcao || 'Reconhecido')}</small></div>`;
  pilha.appendChild(t);
  while (pilha.children.length > 4) pilha.firstChild.remove();
  setTimeout(() => { t.classList.add('saindo'); setTimeout(() => t.remove(), 300); }, 4000);
}

// Normaliza o nome do mesmo jeito que o servidor (normalizar_nome)
const norm = s => String(s).normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
  .toLowerCase().trim().replace(/ /g, '_').replace(/[^a-z0-9_]/g, '');

// ---- PersonModal() ----
const M = { person: null, n: 0, run: false, stream: null, uploading: false, criados: new Set(), voo: 0, cancelando: false };
const getFuncao = () => ($('#f-funcao').value || '').trim() || 'Pesquisador';

function dots() {
  const cap = Math.min(M.n, MIN);
  const label = M.n >= MIN ? `${M.n} fotos ✓` : `${M.n}/${MIN} fotos`;
  $('#cap-dots').innerHTML = Array.from({ length: 10 }, (_, i) =>
    `<i class="${cap >= (i + 1) * MIN / 10 ? 'done' : ''}"></i>`
  ).join('') + `<span>${label}</span>`;
  $('#m-submit').disabled = !($('#f-name').value.trim() && (M.person || M.n >= MIN));
}
// Guia de centralização: só aparece quando o rosto NÃO está centralizado
const POS = { timer: null, busy: false, ok: false };
const setGuide = show => $('#cap-view').classList.toggle('off-center', show);

function iniciarChecagemPosicao() {
  if (POS.timer) return;
  POS.timer = setInterval(async () => {
    const v = $('#cap-video');
    if (POS.busy || !M.stream || !v.videoWidth) return;
    POS.busy = true;
    try {
      const { ok, data } = await api('/api/posicao_rosto', { image: grab(v, 320) });
      if (ok && M.stream) {
        POS.ok = !!data.centralizado;
        setGuide(!POS.ok);
      }
    } finally { POS.busy = false; }
  }, 500);
}
function pararChecagemPosicao() {
  clearInterval(POS.timer); POS.timer = null; POS.busy = false; POS.ok = false; setGuide(false);
}

function openForm(person) {
  Object.assign(M, {
    person: person || null,
    n: person ? Number(person.fotos || 0) : 0,
    run: false,
    uploading: false,
    criados: new Set(),
    voo: 0,
    cancelando: false,
  });
  const edit = !!person;
  $('#m-kicker').textContent = edit ? 'EDITAR USUÁRIO' : 'NOVO CADASTRO';
  $('#m-title').textContent = edit ? 'Editar informações' : 'Cadastrar pessoa';
  $('#m-sub').textContent = edit
    ? 'Atualize o nome, a função, ou adicione fotos.'
    : 'Adicione o nome, capture fotos ou envie arquivos do computador.';
  $('#m-submit').textContent = edit ? 'Salvar alterações' : 'Cadastrar pessoa';
  $('#f-name').value = person ? person.nome : ''; $('#f-name').readOnly = false;
  Object.assign($('#f-funcao'), { value: person ? person.funcao : '', readOnly: false, disabled: false });
  $('#capture').hidden = edit;
  $('#cap-btn').innerHTML = `${ico('scan', 16)} Iniciar captura`;
  $('#upload-progress').hidden = true;
  $('#upload-progress').textContent = '';
  $('#upload-input').disabled = false;
  $('#modal').hidden = false; dots();
  if (edit) { $('#f-funcao').focus(); $('#f-funcao').select(); } else $('#f-name').focus();
}

function closeForm() {
  M.run = false; pararChecagemPosicao(); M.stream?.getTracks().forEach(t => t.stop()); M.stream = null; $('#modal').hidden = true;
}
// Registra que este nome foi criado nesta sessão (só se ele ainda não existia)
function marcarCriado(nome) {
  if (M.person) return;
  if (state.people.some(p => p.nome === norm(nome))) return;
  M.criados.add(nome);
}

// Cancelar: fecha o modal e apaga o que foi criado durante este cadastro
async function cancelarForm() {
  if (M.cancelando) return;
  if (M.criados.size) {
    const ok = await confirmar('Cancelar o cadastro? As fotos já capturadas serão apagadas.', 'Cancelar cadastro');
    if (!ok) return;
  }
  M.cancelando = true;
  M.run = false;
  while (M.voo > 0) await sleep(100);   // espera requisições de foto em andamento terminarem
  const nomes = [...M.criados];
  closeForm();
  for (const n of nomes) await api('/api/deletar', { nome: n });
  M.criados.clear();
  M.cancelando = false;
  if (nomes.length) setPage(state.page);
}

async function capture() {
  if (M.run) { M.run = false; return; }
  const nome = $('#f-name').value.trim();
  if (!nome) return popup('Informe o nome antes de capturar.', 'warn');
  marcarCriado(nome);   // <-- novo (passo 5)
  if (!M.stream) {
    try { M.stream = await navigator.mediaDevices.getUserMedia({ video: true }); } catch { return popup('Não foi possível acessar a câmera.', 'error'); }
    $('#cap-video').srcObject = M.stream; await $('#cap-video').play();
    iniciarChecagemPosicao();
  }
  M.run = true; $('#f-name').readOnly = true; $('#cap-btn').textContent = 'Parar captura';
  while (M.run && M.n < MIN) {
    if (!POS.ok) {
      $('#cap-msg').textContent = 'Aguardando o rosto ser detectado e centralizado...';
      await sleep(200);
      continue;
    }
    M.voo++;   // <-- novo (passo 5)
    let resp;
    try { resp = await api('/api/cadastrar', { nome, funcao: getFuncao(), image: grab($('#cap-video')) }); }
    finally { M.voo--; }
    const { ok, data } = resp;
    $('#cap-msg').textContent = data.mensagem || '';
    if (ok) { M.n = data.total; dots(); }
    await sleep(350);
  }
  M.run = false;
  $('#cap-btn').innerHTML = M.n >= MIN
    ? `${ico('check', 16)} Captura concluída`
    : `${ico('scan', 16)} Continuar captura`;
}

// Upload de fotos do computador
async function enviarFotos(arquivos) {
  if (M.uploading) return;
  const nome = $('#f-name').value.trim();
  if (!nome) return popup('Informe o nome antes de enviar as fotos.', 'warn');marcarCriado(nome);

  M.uploading = true;
  const inp = $('#upload-input');
  const prog = $('#upload-progress');
  inp.disabled = true;
  prog.hidden = false;
  prog.textContent = `Enviando ${arquivos.length} foto(s)...`;

  try {
    const fd = new FormData();
    fd.append('nome', nome);
    fd.append('funcao', getFuncao());
    arquivos.forEach(a => fd.append('fotos', a));

        M.voo++;
    const r = await fetch('/api/upload_fotos', { method: 'POST', body: fd });
    const data = await r.json().catch(() => ({}));

    if (typeof data.total === 'number') {
      M.n = data.total;
      dots();
    }

    if (data.sucesso > 0) {
      prog.textContent = `✓ ${data.mensagem}`;
      setTimeout(() => { if (!M.uploading) prog.hidden = true; }, 4000);
      const total = arquivos.length;
      const falhas = total - data.sucesso;
      if (falhas > 0) {
        popup(`${data.sucesso} foto(s) adicionada(s). ${falhas} ignorada(s) (sem rosto ou arquivo inválido).`, 'warn');
      } else {
        popup(data.mensagem, 'success');
      }
    } else {
      prog.hidden = true;
      popup(data.mensagem || 'Nenhuma foto pôde ser processada.', 'error');
    }
  } catch (err) {
    prog.hidden = true;
    popup('Erro ao enviar as fotos.', 'error');
  } finally {
    M.voo--;
    M.uploading = false;
    inp.disabled = false;
  }
}

$('#cap-btn').onclick = capture;
$('#f-name').oninput = dots;

// Input file
$('#upload-input').onchange = e => {
  const arquivos = [...e.target.files].filter(f => f.type.startsWith('image/'));
  e.target.value = '';
  if (arquivos.length) enviarFotos(arquivos);
};

// Drag & drop
(() => {
  const dz = $('#upload-dropzone');
  if (!dz) return;
  ['dragenter', 'dragover'].forEach(ev =>
    dz.addEventListener(ev, e => { e.preventDefault(); e.stopPropagation(); dz.classList.add('dragover'); })
  );
  ['dragleave', 'dragend'].forEach(ev =>
    dz.addEventListener(ev, e => { e.preventDefault(); e.stopPropagation(); dz.classList.remove('dragover'); })
  );
  dz.addEventListener('drop', e => {
    e.preventDefault(); e.stopPropagation();
    dz.classList.remove('dragover');
    const arquivos = [...e.dataTransfer.files].filter(f => f.type.startsWith('image/'));
    if (arquivos.length) enviarFotos(arquivos);
  });
})();

$('#person-form').onsubmit = async e => {
  e.preventDefault();
  const nome = $('#f-name').value.trim();
  const funcao = getFuncao();
  if (M.person) {
    if (funcao !== M.person.funcao) {
      const { ok, data } = await api('/api/editar_usuario', { nome: M.person.nome, funcao });
      if (!ok) return popup(data.mensagem || 'Não foi possível salvar a função.', 'error');
    }
    if (nome !== M.person.nome) {
      const { ok, data } = await api('/api/renomear', { antigo_nome: M.person.nome, novo_nome: nome });
      popup(data.mensagem, ok ? 'success' : 'error'); if (!ok) return;
    } else popup('Alterações salvas.', 'success');
  } else {
    await api('/api/editar_usuario', { nome, funcao });
    popup('Pessoa cadastrada com sucesso.', 'success');
  }
  closeForm(); setPage('users');
};
// Fecha só ao clicar no fundo escuro. Não pode "retornar false": isso cancelaria o foco dos campos.
$('#modal').onmousedown = e => { if (e.target === e.currentTarget) cancelarForm(); };

// ---- Eventos globais ----
document.addEventListener('click', async e => {
  const t = e.target.closest('[data-go],[data-act]');
  if (!t) return;
  if (e.target.closest('#popup')) return;
  if (t.dataset.go) return setPage(t.dataset.go);
  const { act, nome } = t.dataset;
  if (act === 'new') openForm();
  if (act === 'close') cancelarForm();
  if (act === 'edit') openForm(state.people.find(p => p.nome === nome));
  if (act === 'gallery') abrirGaleria(nome);
  if (act === 'close-gallery') fecharGaleria();
  if (act === 'zoom-foto') abrirZoom(t.dataset.id);
  if (act === 'close-zoom') $('#g-zoom').hidden = true;
  if (act === 'del-foto') await removerFoto(Number(t.dataset.id));
  if (act === 'toggle') await toggleUser(nome, t.dataset.ativo === '1');
  if (act === 'del') await removeUser(nome);
});
$('#user-search').oninput = renderUsers;
$('#rec-btn').onclick = () => rec.on ? stopRecognition() : startRecognition();

// Filtros de registros
document.addEventListener('click', e => {
  const btn = e.target.closest('.filter-button');
  if (!btn) return;
  $$('.filter-button').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  regState.filtro = btn.dataset.filtro;
  loadRegistros();
});

// Busca em registros
$('#reg-search').oninput = renderRegistros;

setPage('dashboard');