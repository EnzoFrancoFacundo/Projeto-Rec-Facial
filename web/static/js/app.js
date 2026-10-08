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
function toast(msg) { const t = document.createElement('div'); t.className = 'toast'; t.textContent = msg; document.body.append(t); setTimeout(() => t.remove(), 2800); }
const avatar = nome => `<span class="avatar">${esc(nome.slice(0, 2).toUpperCase())}</span>`;
const recordHTML = a => `<div class="record">${avatar(a[1])}<div class="record-name"><strong>${esc(a[1])}</strong><span>Entrada principal</span></div><time>${a[2].slice(11, 16)}</time></div>`;

// useState(page, people)
const state = { page: 'dashboard', people: [], acessos: [] };

function setPage(p) {
  state.page = p;
  $$('.page').forEach(s => s.hidden = s.id !== `page-${p}`);
  $$('.nav-item').forEach(b => b.classList.toggle('active', b.dataset.go === p));
  if (p !== 'recognition') stopRecognition();
  ({ dashboard: loadDashboard, users: loadUsers, recognition: loadFeed }[p] || (() => {}))();
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
  const max = Math.max(...sem.map(d => d.valor), 1), vals = sem.map(d => d.valor / max * 100);
  const pts = vals.map((v, i) => `${20 + i * 92},${130 - v}`).join(' ');
  const top = sem.reduce((a, b) => b.valor > a.valor ? b : a);
  $('#week-chart').innerHTML = `<div class="chart-wrap">
    <div class="y-labels">${[1, .75, .5, .25, 0].map(f => `<span>${Math.round(max * f)}</span>`).join('')}</div>
    <svg class="chart" viewBox="0 0 590 150" preserveAspectRatio="none">
      <defs><linearGradient id="fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#14b89a" stop-opacity=".22"/><stop offset="1" stop-color="#14b89a" stop-opacity="0"/></linearGradient></defs>
      ${[25, 50, 75, 100, 125].map(y => `<line x1="0" x2="590" y1="${y}" y2="${y}" stroke-width="1"/>`).join('')}
      <polygon points="20,130 ${pts} 572,130" fill="url(#fill)"/>
      <polyline points="${pts}" fill="none" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
      ${vals.map((v, i) => `<circle cx="${20 + i * 92}" cy="${130 - v}" r="${sem[i] === top ? 5 : 3.5}" stroke-width="3"/>`).join('')}
    </svg><div class="x-labels">${sem.map(d => `<span>${d.dia}</span>`).join('')}</div></div>`;
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
  if (!ativar && !confirm(`Inativar ${nome}? Essa pessoa não conseguirá entrar nem será reconhecida pela câmera.`)) return;
  const { data } = await api('/api/alternar_status', { nome, ativo: ativar });
  toast(data.mensagem); loadUsers();
}
async function removeUser(nome) {
  if (!confirm(`Excluir ${nome}? Esta ação não poderá ser desfeita.`)) return;
  const { data } = await api('/api/deletar', { nome });
  toast(data.mensagem); loadUsers();
}

// ---- Recognition() ----
const rec = { on: false, stream: null };
const grab = (video, w = 480) => {
  const c = document.createElement('canvas'); c.width = w; c.height = Math.round(w * video.videoHeight / video.videoWidth) || 360;
  c.getContext('2d').drawImage(video, 0, 0, c.width, c.height); return c.toDataURL('image/jpeg', 0.6);
};
async function loadFeed() { await loadData(); $('#feed-list').innerHTML = state.acessos.slice(0, 8).map(recordHTML).join(''); }
async function startRecognition() {
  try { rec.stream = await navigator.mediaDevices.getUserMedia({ video: true }); }
  catch { return toast('Não foi possível acessar a câmera.'); }
  const v = $('#rec-video'); v.srcObject = rec.stream; await v.play();
  rec.on = true; setRecUI(true);
  while (rec.on) {
    const { ok, data } = await api('/api/reconhecer', { image: grab(v) });
    if (ok && rec.on) {
      $('#rec-img').src = data.image; $('#rec-img').hidden = false;
      const nome = data.reconhecidos[0];
      $('#rec-who').hidden = !nome;
      if (nome) {
        $('#rec-name').textContent = nome; $('#rec-time').textContent = new Date().toLocaleTimeString('pt-BR');
        if (localStorage.notify !== '0') toast(`Reconhecido: ${nome}`);
      }
    }
    await sleep(300);
  }
}
function stopRecognition() {
  rec.on = false; rec.stream?.getTracks().forEach(t => t.stop()); rec.stream = null; setRecUI(false);
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
$('#cfg-notify').checked = localStorage.notify !== '0';
$('#cfg-save').onclick = () => { localStorage.notify = $('#cfg-notify').checked ? '1' : '0'; toast('Configurações salvas.'); };

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
  if (!nome) return toast('Informe o nome antes de capturar.');
  if (!M.stream) {
    try { M.stream = await navigator.mediaDevices.getUserMedia({ video: true }); } catch { return toast('Não foi possível acessar a câmera.'); }
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
      if (!ok) return toast(data.mensagem || 'Não foi possível salvar a função. Reinicie o servidor (python app.py) para carregar o app.py atualizado.');
    }
    if (nome !== M.person.nome) {
      const { ok, data } = await api('/api/renomear', { antigo_nome: M.person.nome, novo_nome: nome });
      toast(data.mensagem); if (!ok) return;
    } else toast('Alterações salvas.');
  } else {
    // garante que a função digitada fique salva mesmo se foi alterada depois das fotos
    await api('/api/editar_usuario', { nome, funcao });
    toast('Pessoa cadastrada com sucesso.');
  }
  closeForm(); setPage('users');
};
$('#modal').onmousedown = e => e.target === e.currentTarget && closeForm();

// ---- Eventos globais (substituem os onClick do JSX) ----
document.addEventListener('click', e => {
  const t = e.target.closest('[data-go],[data-act]'); if (!t) return;
  if (t.dataset.go) return setPage(t.dataset.go);
  const { act, nome } = t.dataset;
  if (act === 'new') openForm();
  if (act === 'close') closeForm();
  if (act === 'edit') openForm(state.people.find(p => p.nome === nome));
  if (act === 'toggle') toggleUser(nome, t.dataset.ativo === '1');
  if (act === 'del') removeUser(nome);
});
$('#user-search').oninput = renderUsers;
$('#rec-btn').onclick = () => rec.on ? stopRecognition() : startRecognition();

setPage('dashboard');
