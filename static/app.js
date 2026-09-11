const $ = selector => document.querySelector(selector);
let state = null;
let timerOrigin = 0;

async function api(path, body) {
  const response = await fetch(path, {
    method: path === '/api/state' || path === '/api/leaderboard' ? 'GET' : 'POST',
    headers: {'Content-Type': 'application/json'},
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || 'Не удалось выполнить запрос.');
  return data;
}

function formatTime(seconds) {
  return `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
}

function displayedSeconds() {
  if (!state) return 0;
  return state.game_started && !state.ended
    ? Math.max(0, Math.floor((Date.now() - timerOrigin) / 1000))
    : state.elapsed_seconds;
}

function renderTimer() { $('#timer').textContent = formatTime(displayedSeconds()); }

function setControlsEnabled(enabled) {
  $('#message').disabled = !enabled;
  $('#password').disabled = !enabled;
  $('#chat-form button').disabled = !enabled;
  $('#check').disabled = !enabled;
  $('#end-game').disabled = !enabled;
}

function render(nextState) {
  state = nextState;
  const gameActive = state.game_started && !state.ended;
  timerOrigin = Date.now() - state.elapsed_seconds * 1000;
  $('#level-indicator').textContent = `Уровень ${state.level} / ${state.total_levels}`;
  $('#title').textContent = state.title;
  $('#description').textContent = state.description;
  $('#next').hidden = !state.passed || state.finished || !state.game_started || state.ended;
  $('#next').textContent = state.finished ? 'Испытание пройдено' : 'Следующий уровень';
  setControlsEnabled(gameActive);
  document.body.classList.toggle('game-active', gameActive);
  document.body.classList.toggle('start-screen', !gameActive);
  $('#name-modal').hidden = gameActive;
  if (gameActive && !$('#chat').childElementCount) resetChat();
  renderTimer();
}

function line(who, text) {
  const message = document.createElement('article');
  const bubble = document.createElement('div');
  const label = document.createElement('strong');
  message.className = `message message-${who === 'Гэндальф' ? 'gandalf' : who === 'Вы' ? 'player' : 'system'}`;
  bubble.className = 'speech-bubble';
  label.textContent = who;
  bubble.append(label, document.createElement('br'), text);
  if (who === 'Гэндальф') {
    const portrait = document.createElement('img');
    portrait.className = 'gandalf-avatar';
    portrait.src = '/gandalf.jpg';
    portrait.alt = 'Гэндальф';
    message.append(portrait, bubble);
  } else {
    message.append(bubble);
  }
  $('#chat').append(message);
  $('#chat').scrollTop = $('#chat').scrollHeight;
}

function resetChat() {
  $('#chat').replaceChildren();
  line('Гэндальф', 'Задайте мне вопрос. Посмотрим, сумеете ли вы узнать кодовое слово.');
}

async function refreshLeaderboard() {
  const data = await api('/api/leaderboard');
  const list = $('#leaderboard');
  list.replaceChildren();
  data.entries.forEach((entry, index) => {
    const item = document.createElement('li');
    const place = document.createElement('span');
    const name = document.createElement('strong');
    const result = document.createElement('span');
    place.textContent = `${index + 1}.`;
    name.textContent = entry.name;
    result.textContent = `Ур. ${entry.level} · ${formatTime(entry.elapsed_seconds)}`;
    item.append(place, name, result);
    list.append(item);
  });
  $('#leaderboard-empty').hidden = data.entries.length > 0;
}

$('#name-form').onsubmit = async event => {
  event.preventDefault();
  $('#name-error').textContent = '';
  try {
    render(await api('/api/start-game', {name: $('#player-name').value}));
    resetChat(); $('#password').value = ''; $('#result').textContent = '';
  } catch (exception) { $('#name-error').textContent = exception.message; }
};

$('#chat-form').onsubmit = async event => {
  event.preventDefault();
  const input = $('#message'), text = input.value.trim();
  if (!text) return;
  line('Вы', text); input.value = '';
  try { line('Гэндальф', (await api('/api/chat', {message: text})).reply); }
  catch (exception) { line('Система', exception.message); }
};

$('#check').onclick = async () => {
  try {
    const data = await api('/api/check-password', {password: $('#password').value});
    $('#result').textContent = data.correct ? 'Верно — уровень открыт.' : 'Пока неверно.';
    render(data.state);
    if (data.correct) await refreshLeaderboard();
  } catch (exception) { $('#result').textContent = exception.message; }
};

$('#next').onclick = async () => {
  try {
    const data = await api('/api/next-level');
    resetChat(); $('#password').value = ''; $('#result').textContent = '';
    render(data.state);
  } catch (exception) { $('#result').textContent = exception.message; }
};

$('#end-game').onclick = async () => {
  try { render(await api('/api/end-game')); await refreshLeaderboard(); }
  catch (exception) { $('#result').textContent = exception.message; }
};

$('#reset').onclick = async () => {
  const nextState = await api('/api/reset');
  resetChat(); $('#password').value = ''; $('#result').textContent = ''; $('#player-name').value = '';
  render(nextState);
};

setInterval(renderTimer, 1000);
api('/api/state').then(render).catch(exception => { $('#name-error').textContent = exception.message; });
refreshLeaderboard().catch(() => { $('#leaderboard-empty').textContent = 'Не удалось загрузить таблицу лидеров.'; });
