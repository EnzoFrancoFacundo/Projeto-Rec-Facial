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
function pintarBotoesTema(tema) {
  const html = tema === 'light' ? ico('moon', 18) : ico('sun', 18);
  $$('.theme-toggle').forEach(btn => { btn.innerHTML = html; });
}
function aplicarTema(tema) {
  document.documentElement.setAttribute('data-theme', tema);
  try { localStorage.setItem('tema', tema); } catch (e) {}
  pintarBotoesTema(tema);
}
function alternarTema() {
  const atual = document.documentElement.getAttribute('data-theme') || 'dark';
  aplicarTema(atual === 'light' ? 'dark' : 'light');
}
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
  ({ dashboard: loadDashboard, users: loadUsers, recognition: loadFeed }[p] || (() => {}))();
  pintarBotoesTema(document.documentElement.getAttribute('data-theme') || 'dark');
}

async function loadData() {
  const { data } = await api('/api/dados');
  state.people = (data.usuarios || []).map(u => ({ id: u[0], nome: u[1], fotos: u[3], role: u[4] || 'user', funcao: u[5] || 'Pesquisador', ativo: u[6] !== 0 }));
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
      <td>${p.role === 'admin' ? 'Administrador' : 'Usuário'}</td>
      <td><span class="status ${p.ativo ? 'on' : 'off'}"><i></i>${p.ativo ? 'Ativo' : 'Inativo'}</span></td>
      <td class="admin-only"><div class="row-actions"><button title="Editar" data-act="edit" data-nome="${esc(p.nome)}">${ico('edit', 17)}</button>
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
    ctx.fillStyle = cor; ctx.font = '600 14px sans-serif'; ctx.fillText(f.nome, ox + x * dw, oy + y * dh - 8);
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
    if (melhor) { melhor.alvo = n.box; melhor.nome = n.nome; melhor.ok = n.ok; melhor.visto = now; usadas.add(melhor); }
    else { const f = { cur: n.box.slice(), alvo: n.box, nome: n.nome, ok: n.ok, visto: now }; rec.faces.push(f); usadas.add(f); }
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
      const nome = data.reconhecidos[0];
      $('#rec-who').hidden = !nome;
      if (nome) {
        $('#rec-name').textContent = nome;
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
// O aviso "Notificações em tempo real" continua existindo para o cadastro de pessoas.
// Nada mais é disparado na tela de reconhecimento.
$('#cfg-notify').checked = localStorage.notify !== '0';
$('#cfg-save').onclick = () => {
  localStorage.notify = $('#cfg-notify').checked ? '1' : '0';
  popup('Configurações salvas.', 'success');
};

// ---- PersonModal() ----
const M = { person: null, n: 0, run: false, stream: null };
const getFuncao = () => ($('#f-funcao').value || '').trim() || 'Pesquisador';
function dots() {
  $('#cap-dots').innerHTML = Array.from({ length: 10 }, (_, i) => `<i class="${M.n >= (i + 1) * MIN / 10 ? 'done' : ''}"></i>`).join('') + `<span>${M.n}/${MIN} fotos</span>`;
  $('#m-submit').disabled = !($('#f-name').value.trim() && (M.person || M.n >= MIN));
}
function openForm(person) {
  Object.assign(M, { person: person || null, n: 0, run: false });
  const edit = !!person;
  $('#m-kicker').textContent = edit ? 'EDITAR USUÁRIO' : 'NOVO CADASTRO';
  $('#m-title').textContent = edit ? 'Editar informações' : 'Cadastrar pessoa';
  $('#m-sub').textContent = edit ? 'Atualize o nome e a função do usuário.' : 'Adicione o nome e capture as fotos para reconhecimento.';
  $('#m-submit').textContent = edit ? 'Salvar alterações' : 'Cadastrar pessoa';
  $('#f-name').value = person ? person.nome : ''; $('#f-name').readOnly = false;
  Object.assign($('#f-funcao'), { value: person ? person.funcao : '', readOnly: false, disabled: false });
  $('#capture').hidden = edit; $('#cap-btn').innerHTML = `${ico('scan', 16)} Iniciar captura`;
  $('#modal').hidden = false; dots();
  if (edit) { $('#f-funcao').focus(); $('#f-funcao').select(); } else $('#f-name').focus();
}
function closeForm() {
  M.run = false; M.stream?.getTracks().forEach(t => t.stop()); M.stream = null; $('#modal').hidden = true;
}
async function capture() {
  if (M.run) { M.run = false; return; }
  const nome = $('#f-name').value.trim();
  if (!nome) return popup('Informe o nome antes de capturar.', 'warn');
  if (!M.stream) {
    try { M.stream = await navigator.mediaDevices.getUserMedia({ video: true }); } catch { return popup('Não foi possível acessar a câmera.', 'error'); }
    $('#cap-video').srcObject = M.stream; await $('#cap-video').play();
  }
  M.run = true; $('#f-name').readOnly = true; $('#cap-btn').textContent = 'Parar captura';
  while (M.run && M.n < MIN) {
    const { ok, data } = await api('/api/cadastrar', { nome, funcao: getFuncao(), image: grab($('#cap-video')) });
    $('#cap-msg').textContent = data.mensagem || '';
    if (ok) { M.n = data.total; dots(); }
    await sleep(350);
  }
  M.run = false; $('#cap-btn').innerHTML = M.n >= MIN ? `${ico('check', 16)} Captura concluída` : `${ico('scan', 16)} Continuar captura`;
}
$('#cap-btn').onclick = capture;
$('#f-name').oninput = dots;
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
$('#modal').onmousedown = e => e.target === e.currentTarget && closeForm();

// ---- Eventos globais ----
document.addEventListener('click', async e => {
  const t = e.target.closest('[data-go],[data-act]');
  if (!t) return;
  if (e.target.closest('#popup')) return;
  if (t.dataset.go) return setPage(t.dataset.go);
  const { act, nome } = t.dataset;
  if (act === 'new') openForm();
  if (act === 'close') closeForm();
  if (act === 'edit') openForm(state.people.find(p => p.nome === nome));
  if (act === 'toggle') await toggleUser(nome, t.dataset.ativo === '1');
  if (act === 'del') await removeUser(nome);
});
$('#user-search').oninput = renderUsers;
$('#rec-btn').onclick = () => rec.on ? stopRecognition() : startRecognition();

setPage('dashboard');