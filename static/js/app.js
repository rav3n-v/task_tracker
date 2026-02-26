const state = {
  tasks: [],
  settings: {},
  syllabus: {},
  progress: null,
  timerSeconds: 0,
  timerHandle: null,
  search: '',
  user: null,
};

const routineTemplate = [
  { id: 'r1', time: '5:00 AM - 5:30 AM', task: 'Wake up, Exercise, Wash up', tag: 'Physical', minutes: 30 },
  { id: 'r2', time: '6:00 AM - 7:00 AM', task: 'Practise General / Part A', tag: 'Study', minutes: 60 },
  { id: 'r3', time: '7:00 AM - 8:30 AM', task: 'Fresh up, Breakfast', tag: 'Nutrition', minutes: 90 },
  { id: 'r4', time: '8:30 AM - 9:30 AM', task: 'Previous day revision', tag: 'Study', minutes: 60 },
  { id: 'r5', time: '9:30 AM - 12:30 PM', task: 'Core Study Session 1', tag: 'Study', minutes: 180 },
  { id: 'r6', time: '12:30 PM - 1:30 PM', task: 'Lunch Break', tag: 'Break', minutes: 60 },
  { id: 'r7', time: '1:30 PM - 4:30 PM', task: 'Core Study Session 2', tag: 'Study', minutes: 180 },
];

const resourceLinks = [
  { title: 'NPTEL Mathematics Lectures', url: 'https://nptel.ac.in/course.html' },
  { title: 'IIT JAM / CSIR Previous Papers', url: 'https://archive.org' },
  { title: 'MIT OpenCourseWare Mathematics', url: 'https://ocw.mit.edu/search/?d=Mathematics' },
];

const el = {
  authGate: document.getElementById('authGate'),
  appLayout: document.getElementById('appLayout'),
  userDisplay: document.getElementById('userDisplay'),
  logoutBtn: document.getElementById('logoutBtn'),
  authMessage: document.getElementById('authMessage'),
  loginForm: document.getElementById('loginForm'),
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
  },
  dashboardCards: document.getElementById('dashboardCards'),
  currentDate: document.getElementById('currentDate'),
  streakText: document.getElementById('streakText'),
  countDays: document.getElementById('countDays'),
  countHours: document.getElementById('countHours'),
  countMinutes: document.getElementById('countMinutes'),
  targetDate: document.getElementById('targetDate'),
  daysComplete: document.getElementById('daysComplete'),
  trackedMinutes: document.getElementById('trackedMinutes'),
  routineList: document.getElementById('routineList'),
  hoursToday: document.getElementById('hoursToday'),
  hoursWeek: document.getElementById('hoursWeek'),
  analyticsStats: document.getElementById('analyticsStats'),
  hoursTrend: document.getElementById('hoursTrend'),
  consistencyTrend: document.getElementById('consistencyTrend'),
  timerDisplay: document.getElementById('timerDisplay'),
  timerStart: document.getElementById('timerStart'),
  timerPause: document.getElementById('timerPause'),
  timerReset: document.getElementById('timerReset'),
  taskForm: document.getElementById('taskForm'),
  taskTitle: document.getElementById('taskTitle'),
  taskUnit: document.getElementById('taskUnit'),
  taskTopic: document.getElementById('taskTopic'),
  taskPriority: document.getElementById('taskPriority'),
  taskDueDate: document.getElementById('taskDueDate'),
  taskNotes: document.getElementById('taskNotes'),
  taskSearch: document.getElementById('taskSearch'),
  taskList: document.getElementById('taskList'),
  testStats: document.getElementById('testStats'),
  downloadList: document.getElementById('downloadList'),
  resourceList: document.getElementById('resourceList'),
  settingsForm: document.getElementById('settingsForm'),
  settingExamDate: document.getElementById('settingExamDate'),
  settingDailyGoal: document.getElementById('settingDailyGoal'),
  settingTheme: document.getElementById('settingTheme'),
  settingsMessage: document.getElementById('settingsMessage'),
};

async function request(url, options = {}) {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `Request failed: ${response.status}`);
  return data;
}

const todayKey = () => new Date().toISOString().slice(0, 10);
const readJson = (k, f) => (localStorage.getItem(k) ? JSON.parse(localStorage.getItem(k)) : f);
const writeJson = (k, v) => localStorage.setItem(k, JSON.stringify(v));
const getRoutineState = () => readJson('routineState', {});
const setRoutineState = (next) => writeJson('routineState', next);
const getDailyLog = () => readJson('dailyStudyLog', {});
const formatDuration = (s) => `${String(Math.floor(s / 3600)).padStart(2, '0')}:${String(Math.floor((s % 3600) / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;

function setRoute(route) {
  const active = Object.hasOwn(el.views, route) ? route : 'dashboard';
  Object.values(el.views).forEach((view) => view.classList.remove('active'));
  el.views[active].classList.add('active');
  el.navLinks.forEach((link) => link.classList.toggle('active', link.dataset.route === active));
}

function renderAuthState() {
  const loggedIn = Boolean(state.user);
  el.authGate.hidden = loggedIn;
  el.appLayout.hidden = !loggedIn;
  el.userDisplay.textContent = loggedIn ? `@${state.user.username}` : '';
}

function populateSyllabus() {
  const units = Object.keys(state.syllabus);
  el.taskUnit.innerHTML = units.map((u) => `<option>${u}</option>`).join('');
  updateTopicOptions();
}

function updateTopicOptions() {
  const topics = state.syllabus[el.taskUnit.value] || [];
  el.taskTopic.innerHTML = topics.map((t) => `<option>${t}</option>`).join('');
}

function renderTasks() {
  const needle = state.search.trim().toLowerCase();
  const tasks = state.tasks.filter((task) => {
    if (!needle) return true;
    return [task.title, task.unit, task.topic].join(' ').toLowerCase().includes(needle);
  });

  el.taskList.innerHTML = tasks.map((task) => `
    <article class="task-item">
      <input class="task-toggle" data-id="${task.id}" type="checkbox" ${task.completed ? 'checked' : ''} />
      <div><strong>${task.title}</strong><div class="task-meta">${task.unit} · ${task.topic}</div><div class="task-meta">Due: ${task.due_date || 'Not set'}${task.notes ? ` · ${task.notes}` : ''}</div></div>
      <div class="task-actions"><span class="badge ${task.priority.toLowerCase()}">${task.priority}</span><button class="task-delete" data-id="${task.id}">Delete</button></div>
    </article>`).join('');

  el.taskList.querySelectorAll('.task-toggle').forEach((checkbox) => checkbox.addEventListener('change', async () => {
    await request(`/api/tasks/${checkbox.dataset.id}`, { method: 'PATCH', body: JSON.stringify({ completed: checkbox.checked }) });
    await reloadData();
  }));
  el.taskList.querySelectorAll('.task-delete').forEach((button) => button.addEventListener('click', async () => {
    await request(`/api/tasks/${button.dataset.id}`, { method: 'DELETE' });
    await reloadData();
  }));
}

function renderDashboard() {
  if (!state.progress) return;
  const completion = state.progress.completion_rate || 0;
  const studyMinutes = Math.round((state.progress.completed || 0) * 45);
  const cards = [
    { value: `${state.progress.completed || 0}/60`, label: 'Study Plan Progress', percent: Math.min((state.progress.completed / 60) * 100, 100) },
    { value: `${Math.floor(studyMinutes / 60)}h`, label: 'Total Study Time', percent: Math.min((studyMinutes / 3600) * 100, 100) },
    { value: String(state.progress.completed || 0), label: 'Mock Tests Completed', percent: Math.min((state.progress.completed / 20) * 100, 100) },
    { value: `${completion}%`, label: 'Success Probability', percent: completion },
  ];
  el.dashboardCards.innerHTML = cards.map((card) => `<article class="metric-card"><h3>${card.value}</h3><p>${card.label}</p><div class="metric-bar"><span style="width:${card.percent}%"></span></div></article>`).join('');
  el.daysComplete.textContent = `${Math.min(state.progress.completed || 0, 60)}/60`;
  el.trackedMinutes.textContent = `${studyMinutes}m`;
}

function renderHeaderBits() {
  const now = new Date();
  el.currentDate.textContent = `Current Date: ${now.toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}`;
  const log = getDailyLog();
  let streak = 0;
  for (let i = 0; i < 365; i += 1) {
    const day = new Date();
    day.setDate(now.getDate() - i);
    const key = day.toISOString().slice(0, 10);
    if ((log[key] || 0) > 0) streak += 1; else break;
  }
  el.streakText.textContent = `Study Streak: ${streak} days`;
}

function renderCountdown() {
  const target = state.settings.exam_date ? new Date(state.settings.exam_date) : new Date(`${new Date().getFullYear()}-12-15T00:00:00`);
  const diff = Math.max(0, target.getTime() - Date.now());
  const minutesTotal = Math.floor(diff / 60000);
  el.countDays.textContent = String(Math.floor(minutesTotal / (60 * 24))).padStart(2, '0');
  el.countHours.textContent = String(Math.floor((minutesTotal % (60 * 24)) / 60)).padStart(2, '0');
  el.countMinutes.textContent = String(minutesTotal % 60).padStart(2, '0');
  el.targetDate.textContent = `Target Exam: ${target.toLocaleDateString(undefined, { month: 'long', day: 'numeric', year: 'numeric' })}`;
}

function renderRoutine() {
  const key = todayKey();
  const checkedToday = getRoutineState()[key] || {};
  el.routineList.innerHTML = routineTemplate.map((item) => `<article class="routine-item"><input type="checkbox" data-id="${item.id}" ${checkedToday[item.id] ? 'checked' : ''} /><div class="routine-time">${item.time}</div><label>${item.task}</label><div class="routine-tag">${item.tag}</div></article>`).join('');
  el.routineList.querySelectorAll('input[type="checkbox"]').forEach((input) => input.addEventListener('change', () => {
    const current = getRoutineState();
    const dayState = current[key] || {};
    dayState[input.dataset.id] = input.checked;
    current[key] = dayState;
    setRoutineState(current);
  }));
}

function renderTests() {
  const completed = state.tasks.filter((item) => item.completed).length;
  el.testStats.innerHTML = `<article class="metric-card"><h3>${completed}</h3><p>Completed Mocks</p></article><article class="metric-card"><h3>${state.tasks.length - completed}</h3><p>Pending Mocks</p></article><article class="metric-card"><h3>${state.settings.daily_goal || 3}</h3><p>Daily Goal</p></article>`;
}

function renderDownloads() {
  el.downloadList.innerHTML = [
    { title: 'Weekly revision checklist', subtitle: 'Print-friendly checklist template', url: '#' },
    { title: 'Mock test log sheet', subtitle: 'Track score and mistakes', url: '#' },
    { title: 'Important formula summary', subtitle: 'Compact formula handout', url: '#' },
  ].map((item) => `<article class="link-card"><strong>${item.title}</strong><span class="task-meta">${item.subtitle}</span><a href="${item.url}">Download</a></article>`).join('');
}

function renderResources() {
  const syllabusRows = Object.entries(state.syllabus).slice(0, 6).map(([unit, topics]) => `<article class="link-card"><strong>${unit}</strong><span class="task-meta">${topics.slice(0, 2).join(' • ')}</span></article>`).join('');
  const links = resourceLinks.map((item) => `<article class="link-card"><strong>${item.title}</strong><a href="${item.url}" target="_blank" rel="noreferrer">Open resource</a></article>`).join('');
  el.resourceList.innerHTML = `${syllabusRows}${links}`;
}

function renderAnalytics() {
  el.analyticsStats.innerHTML = `<article><h3>${state.progress?.completion_rate || 0}%</h3><p>Completion Rate</p></article>`;
  el.hoursTrend.innerHTML = '';
  el.consistencyTrend.innerHTML = '';
}

function applyTheme(theme) { document.documentElement.setAttribute('data-theme', theme || 'dark'); }
function renderSettingsForm() {
  el.settingExamDate.value = state.settings.exam_date || '';
  el.settingDailyGoal.value = state.settings.daily_goal || 3;
  el.settingTheme.value = state.settings.theme || 'dark';
  applyTheme(state.settings.theme);
}

async function reloadData() {
  const data = await request('/api/bootstrap');
  state.tasks = data.tasks;
  state.settings = data.settings;
  state.syllabus = data.syllabus;
  state.user = data.user;
  state.progress = await request('/api/progress');
  populateSyllabus();
  renderDashboard();
  renderCountdown();
  renderTasks();
  renderTests();
  renderSettingsForm();
  renderAnalytics();
  renderHeaderBits();
  renderRoutine();
  renderDownloads();
  renderResources();
  renderAuthState();
}

function wireForms() {
  el.loginForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = new FormData(el.loginForm);
    try {
      await request('/api/login', { method: 'POST', body: JSON.stringify({ username: form.get('username'), password: form.get('password') }) });
      el.authMessage.textContent = '';
      await reloadData();
    } catch (error) { el.authMessage.textContent = error.message; }
  });
  el.logoutBtn.addEventListener('click', async () => {
    await request('/api/logout', { method: 'POST' });
    state.user = null;
    renderAuthState();
  });

  el.taskUnit.addEventListener('change', updateTopicOptions);
  el.taskForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    await request('/api/tasks', {
      method: 'POST',
      body: JSON.stringify({ title: el.taskTitle.value, unit: el.taskUnit.value, topic: el.taskTopic.value, priority: el.taskPriority.value, due_date: el.taskDueDate.value || null, notes: el.taskNotes.value }),
    });
    el.taskForm.reset();
    updateTopicOptions();
    await reloadData();
  });
  el.taskSearch.addEventListener('input', () => { state.search = el.taskSearch.value; renderTasks(); });
  el.settingsForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    state.settings = await request('/api/settings', { method: 'PUT', body: JSON.stringify({ exam_date: el.settingExamDate.value || null, daily_goal: Number(el.settingDailyGoal.value || 3), theme: el.settingTheme.value }) });
    applyTheme(state.settings.theme);
    el.settingsMessage.textContent = 'Settings saved successfully.';
    renderCountdown();
    renderTests();
  });
}

function wireTimer() {
  el.timerStart.addEventListener('click', () => {
    if (state.timerHandle) return;
    state.timerHandle = setInterval(() => {
      state.timerSeconds += 1;
      localStorage.setItem('studyTimerSeconds', String(state.timerSeconds));
      el.timerDisplay.textContent = formatDuration(state.timerSeconds);
    }, 1000);
  });
  el.timerPause.addEventListener('click', () => { if (state.timerHandle) clearInterval(state.timerHandle); state.timerHandle = null; });
  el.timerReset.addEventListener('click', () => {
    if (state.timerHandle) clearInterval(state.timerHandle);
    state.timerHandle = null;
    state.timerSeconds = 0;
    localStorage.setItem('studyTimerSeconds', '0');
    el.timerDisplay.textContent = formatDuration(0);
  });
}

async function bootstrap() {
  wireForms();
  wireTimer();
  state.timerSeconds = Number(localStorage.getItem('studyTimerSeconds') || 0);
  el.timerDisplay.textContent = formatDuration(state.timerSeconds);

  const me = await request('/api/me');
  state.user = me.user;
  renderAuthState();
  if (state.user) await reloadData();

  window.addEventListener('hashchange', () => setRoute(window.location.hash.replace('#', '') || 'dashboard'));
  el.navLinks.forEach((link) => link.addEventListener('click', () => setRoute(link.dataset.route)));
  setRoute(window.location.hash.replace('#', '') || 'dashboard');
  setInterval(renderCountdown, 60 * 1000);
}

bootstrap();
