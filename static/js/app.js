const state = {
  timerSeconds: 0,
  timerHandle: null,
};

const el = {
  navLinks: document.querySelectorAll('.nav-links a'),
  views: {
    dashboard: document.getElementById('dashboardView'),
    plan: document.getElementById('planView'),
    routine: document.getElementById('routineView'),
    session: document.getElementById('sessionView'),
    tests: document.getElementById('testsView'),
    downloads: document.getElementById('downloadsView'),
    analytics: document.getElementById('analyticsView'),
    resources: document.getElementById('resourcesView'),
    settings: document.getElementById('settingsView'),
    syllabus: document.getElementById('syllabusView'),
    'score-predictor': document.getElementById('scorePredictorView'),
  },
};

async function api(url, options = {}) {
  const response = await fetch(url, {
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return response.json();
}

function setRoute(route) {
  const active = Object.hasOwn(el.views, route) ? route : 'dashboard';
  Object.values(el.views).forEach((view) => view?.classList.remove('active'));
  el.views[active]?.classList.add('active');
  el.navLinks.forEach((link) => link.classList.toggle('active', link.dataset.route === active));
  if (active === 'routine') loadDailyRoutine();
  if (active === 'plan') loadDailyPlanner();
  if (active === 'tests') loadMockTests();
  if (active === 'analytics' || active === 'score-predictor') loadAnalyticsSummary();
}

function initNavigation() {
  el.navLinks.forEach((link) => {
    link.addEventListener('click', (event) => {
      event.preventDefault();
      const route = link.dataset.route;
      if (!route) return;
      setRoute(route);
      history.pushState(null, '', `/${route}`);
    });
  });
}

async function loadDailyRoutine() {
  const data = await api('/api/daily-routine');
  const list = document.getElementById('routineList');
  const subtitle = document.getElementById('routineProgress');
  const progressBar = document.getElementById('routineProgressBar');
  if (!list || !subtitle || !progressBar) return;

  subtitle.textContent = `${data.completed_count}/${data.total_count} completed · ${data.completion_percentage}%`;
  progressBar.style.width = `${data.completion_percentage}%`;

  list.innerHTML = data.items.map((item) => `
    <article class="routine-item">
      <input type="checkbox" data-routine-id="${item.id}" ${item.completed ? 'checked' : ''}>
      <span class="routine-time">${item.time_label}</span>
      <label>${item.title}</label>
      <span class="routine-tag">Fixed</span>
    </article>
  `).join('');

  list.querySelectorAll('input[type="checkbox"]').forEach((checkbox) => {
    checkbox.addEventListener('change', async () => {
      await api('/api/daily-routine', {
        method: 'POST',
        body: JSON.stringify({ routine_id: Number(checkbox.dataset.routineId) }),
      });
      loadDailyRoutine();
    });
  });
}

async function loadDailyPlanner() {
  const data = await api('/api/daily-planner');
  const list = document.getElementById('dailyPlannerList');
  const meta = document.getElementById('dailyPlannerMeta');
  const streak = document.getElementById('dailyPlannerStreak');
  const bar = document.getElementById('dailyPlannerProgressBar');
  if (!list || !meta || !streak || !bar) return;

  meta.textContent = `${data.completed_count}/${data.total_count} completed · ${data.completion_percentage}% complete`;
  streak.textContent = `Streak: ${data.streak} days`;
  bar.style.width = `${data.completion_percentage}%`;

  list.innerHTML = data.items.map((task) => `
    <article class="task-item">
      <input type="checkbox" data-task-id="${task.id}" ${task.completed ? 'checked' : ''}>
      <div><strong>${task.title}</strong></div>
      <div class="task-actions"><button type="button" data-delete-id="${task.id}">Delete</button></div>
    </article>
  `).join('');

  list.querySelectorAll('[data-task-id]').forEach((node) => {
    node.addEventListener('change', async () => {
      await api(`/api/daily-planner/${node.dataset.taskId}`, { method: 'PATCH' });
      loadDailyPlanner();
    });
  });
  list.querySelectorAll('[data-delete-id]').forEach((node) => {
    node.addEventListener('click', async () => {
      await api(`/api/daily-planner/${node.dataset.deleteId}`, { method: 'DELETE' });
      loadDailyPlanner();
    });
  });
}

function initDailyPlannerCreate() {
  const input = document.getElementById('dailyTaskTitle');
  const button = document.getElementById('addDailyTaskBtn');
  if (!input || !button) return;
  button.addEventListener('click', async () => {
    const title = input.value.trim();
    if (!title) return;
    await api('/api/daily-planner', { method: 'POST', body: JSON.stringify({ title }) });
    input.value = '';
    loadDailyPlanner();
  });
}

async function loadMockTests() {
  const data = await api('/api/mock-tests');
  const stats = document.getElementById('mockStats');
  const list = document.getElementById('mockTestsList');
  if (!stats || !list) return;

  stats.innerHTML = `
    <article><h3>${data.attempted_count}/${data.total_count}</h3><p>Attempted</p></article>
    <article><h3>${data.average_score}</h3><p>Average Score</p></article>
    <article><h3>${data.best_score}</h3><p>Best Score</p></article>
  `;

  list.innerHTML = data.items.map((test) => `
    <article class="task-item">
      <input type="checkbox" data-test-number="${test.test_number}" ${test.attempted ? 'checked' : ''}>
      <div>
        <strong>Mock Test ${test.test_number}</strong>
        <input type="number" min="0" max="200" step="0.1" placeholder="Score" value="${test.score ?? ''}" data-score-number="${test.test_number}">
      </div>
      <div class="task-meta">${test.attempt_date || 'Not attempted yet'}</div>
    </article>
  `).join('');

  list.querySelectorAll('[data-test-number]').forEach((node) => {
    node.addEventListener('change', async () => {
      await api(`/api/mock-tests/${node.dataset.testNumber}`, {
        method: 'PATCH',
        body: JSON.stringify({ attempted: node.checked, attempt_date: node.checked ? new Date().toISOString().slice(0, 10) : null }),
      });
      loadMockTests();
    });
  });

  list.querySelectorAll('[data-score-number]').forEach((node) => {
    node.addEventListener('change', async () => {
      await api(`/api/mock-tests/${node.dataset.scoreNumber}`, {
        method: 'PATCH',
        body: JSON.stringify({ score: node.value === '' ? null : Number(node.value), attempted: true, attempt_date: new Date().toISOString().slice(0, 10) }),
      });
      loadMockTests();
    });
  });
}

async function loadAnalyticsSummary() {
  const data = await api('/api/analytics-summary');
  const analyticsGrid = document.getElementById('analyticsSummaryGrid');
  if (analyticsGrid) {
    analyticsGrid.innerHTML = `
      <article class="metric-card"><h3>${data.total_hours_studied}</h3><p>Total Hours Studied</p></article>
      <article class="metric-card"><h3>${data.average_daily_hours}</h3><p>Average Daily Hours</p></article>
      <article class="metric-card"><h3>${data.daily_planner_completion_percent}%</h3><p>Daily Planner Completion</p></article>
      <article class="metric-card"><h3>${data.routine_consistency_percent}%</h3><p>Routine Consistency</p></article>
      <article class="metric-card"><h3>${data.mock_test_attempt_percent}%</h3><p>Mock Test Attempt</p></article>
      <article class="metric-card"><h3>${data.average_mock_score}</h3><p>Average Mock Score</p></article>
      <article class="metric-card"><h3>${data.predicted_score}</h3><p>Predicted Readiness Score</p></article>
      <article class="metric-card"><h3>${data.confidence_level}</h3><p>Confidence Level</p></article>
    `;
  }

  const predictorScore = document.getElementById('predictorLiveScore');
  const predictorConfidence = document.getElementById('predictorConfidence');
  if (predictorScore) predictorScore.textContent = data.predicted_score;
  if (predictorConfidence) predictorConfidence.textContent = data.confidence_level;
}

function formatTime(seconds) {
  const hrs = String(Math.floor(seconds / 3600)).padStart(2, '0');
  const mins = String(Math.floor((seconds % 3600) / 60)).padStart(2, '0');
  const secs = String(seconds % 60).padStart(2, '0');
  return `${hrs}:${mins}:${secs}`;
}

function initTimer() {
  const display = document.getElementById('timerDisplay');
  const start = document.getElementById('timerStart');
  const pause = document.getElementById('timerPause');
  const reset = document.getElementById('timerReset');
  const render = () => { if (display) display.textContent = formatTime(state.timerSeconds); };

  start?.addEventListener('click', () => {
    if (state.timerHandle) return;
    state.timerHandle = setInterval(() => { state.timerSeconds += 1; render(); }, 1000);
  });
  pause?.addEventListener('click', () => {
    clearInterval(state.timerHandle);
    state.timerHandle = null;
  });
  reset?.addEventListener('click', () => {
    clearInterval(state.timerHandle);
    state.timerHandle = null;
    state.timerSeconds = 0;
    render();
  });
}

function initSyllabusListeners() {
  document.addEventListener('change', async (event) => {
    const target = event.target;
    if (!target.classList?.contains('syllabus-toggle')) return;
    await api('/api/syllabus-progress', {
      method: 'POST',
      body: JSON.stringify({
        topic_id: Number(target.dataset.topicId),
        field: target.dataset.field,
        value: target.checked,
      }),
    });
  });
}

function bootstrap() {
  const initialRoute = document.body?.dataset.initialRoute || 'dashboard';
  setRoute(initialRoute);
  initNavigation();
  initDailyPlannerCreate();
  initSyllabusListeners();
  initTimer();
}

document.addEventListener('DOMContentLoaded', bootstrap);
