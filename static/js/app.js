const config = window.APP_CONFIG || {};
const api = config.api || {};

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
  { id: 'r1', time: '5:00 AM - 5:30 AM', task: 'Wake up, Exercise, Wash up', tag: 'Physical' },
  { id: 'r2', time: '6:00 AM - 7:00 AM', task: 'Practise General / Part A', tag: 'Study' },
  { id: 'r3', time: '7:00 AM - 8:30 AM', task: 'Fresh up, Breakfast', tag: 'Nutrition' },
  { id: 'r4', time: '8:30 AM - 9:30 AM', task: 'Previous day revision', tag: 'Study' },
  { id: 'r5', time: '9:30 AM - 12:30 PM', task: 'Core Study Session 1', tag: 'Study' },
  { id: 'r6', time: '12:30 PM - 1:30 PM', task: 'Lunch Break', tag: 'Break' },
  { id: 'r7', time: '1:30 PM - 4:30 PM', task: 'Core Study Session 2', tag: 'Study' },
];

const resourceLinks = [
  { title: 'NPTEL Mathematics Lectures', url: 'https://nptel.ac.in/course.html' },
  { title: 'IIT JAM / CSIR Previous Papers', url: 'https://archive.org' },
  { title: 'MIT OpenCourseWare Mathematics', url: 'https://ocw.mit.edu/search/?d=Mathematics' },
];

const el = {
  appLayout: document.getElementById('appLayout'),
  userDisplay: document.getElementById('userDisplay'),
  logoutBtn: document.getElementById('logoutBtn'),
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
  const response = await fetch(url, { headers: { 'Content-Type': 'application/json' }, ...options });
  const data = await response.json().catch(() => ({}));
  if (response.status === 401) {
    window.location.href = config.loginUrl || '/login';
    throw new Error('Authentication required');
  }
  if (!response.ok) {
    throw new Error(data.error || `Request failed: ${response.status}`);
  }
  return data;
}

const formatDuration = (seconds) => `${String(Math.floor(seconds / 3600)).padStart(2, '0')}:${String(Math.floor((seconds % 3600) / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;

function setRoute(route) {
  const active = Object.hasOwn(el.views, route) ? route : 'dashboard';
  Object.values(el.views).forEach((view) => view.classList.remove('active'));
  el.views[active].classList.add('active');
  el.navLinks.forEach((link) => link.classList.toggle('active', link.dataset.route === active));
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
  const tasks = state.tasks.filter((task) => !needle || [task.title, task.unit, task.topic].join(' ').toLowerCase().includes(needle));
  el.taskList.innerHTML = tasks.map((task) => `<article class="task-item"><input class="task-toggle" data-id="${task.id}" type="checkbox" ${task.completed ? 'checked' : ''} /><div><strong>${task.title}</strong><div class="task-meta">${task.unit} · ${task.topic}</div><div class="task-meta">Due: ${task.due_date || 'Not set'}${task.notes ? ` · ${task.notes}` : ''}</div></div><div class="task-actions"><span class="badge ${task.priority.toLowerCase()}">${task.priority}</span><button class="task-delete" data-id="${task.id}">Delete</button></div></article>`).join('');
  el.taskList.querySelectorAll('.task-toggle').forEach((box) => box.addEventListener('change', async () => { await request(`${api.tasks}/${box.dataset.id}`, { method: 'PATCH', body: JSON.stringify({ completed: box.checked }) }); await reloadData(); }));
  el.taskList.querySelectorAll('.task-delete').forEach((btn) => btn.addEventListener('click', async () => { await request(`${api.tasks}/${btn.dataset.id}`, { method: 'DELETE' }); await reloadData(); }));
}

function renderDashboard() {
  if (!state.progress) return;
  const completion = state.progress.completion_rate || 0;
  const tracked = state.progress.total_tracked_minutes || 0;
  const cards = [
    { value: `${state.progress.completed || 0}/${state.progress.total || 0}`, label: 'Completed Tasks', percent: completion },
    { value: `${tracked}m`, label: 'Total Study Time', percent: Math.min((tracked / 7200) * 100, 100) },
    { value: `${state.progress.study_streak || 0} days`, label: 'Study Streak', percent: Math.min((state.progress.study_streak || 0) * 10, 100) },
    { value: `${completion}%`, label: 'Completion Rate', percent: completion },
  ];
  el.dashboardCards.innerHTML = cards.map((card) => `<article class="metric-card"><h3>${card.value}</h3><p>${card.label}</p><div class="metric-bar"><span style="width:${card.percent}%"></span></div></article>`).join('');
  el.daysComplete.textContent = `${state.progress.completed || 0}/${state.progress.total || 0}`;
  el.trackedMinutes.textContent = `${tracked}m`;
}

function renderHeaderBits() {
  const now = new Date();
  el.currentDate.textContent = `Current Date: ${now.toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}`;
  el.streakText.textContent = `Study Streak: ${state.progress?.study_streak || 0} days`;
}

function renderCountdown() {
  const countdown = state.progress?.countdown || { days: 0, hours: 0, minutes: 0 };
  el.countDays.textContent = String(countdown.days).padStart(2, '0');
  el.countHours.textContent = String(countdown.hours).padStart(2, '0');
  el.countMinutes.textContent = String(countdown.minutes).padStart(2, '0');
  el.targetDate.textContent = `Target Exam: ${state.progress?.target_exam || 'Not set'}`;
}

function renderRoutine() {
  el.routineList.innerHTML = routineTemplate.map((item) => `<article class="routine-item"><div class="routine-time">${item.time}</div><label>${item.task}</label><div class="routine-tag">${item.tag}</div></article>`).join('');
}

function renderTests() {
  const completed = state.tasks.filter((item) => item.completed).length;
  el.testStats.innerHTML = `<article class="metric-card"><h3>${completed}</h3><p>Completed Mocks</p></article><article class="metric-card"><h3>${state.tasks.length - completed}</h3><p>Pending Mocks</p></article><article class="metric-card"><h3>${state.settings.daily_goal || 3}</h3><p>Daily Goal</p></article>`;
}

function renderDownloads() {
  el.downloadList.innerHTML = [
    { title: 'Weekly revision checklist', subtitle: 'Print-friendly checklist template', url: 'https://www.printablepaper.net/' },
    { title: 'Mock test log sheet', subtitle: 'Track score and mistakes', url: 'https://docs.google.com/spreadsheets' },
    { title: 'Important formula summary', subtitle: 'Compact formula handout', url: 'https://openstax.org/subjects/math' },
  ].map((item) => `<article class="link-card"><strong>${item.title}</strong><span class="task-meta">${item.subtitle}</span><a href="${item.url}" target="_blank" rel="noreferrer">Open</a></article>`).join('');
}

function renderResources() {
  const syllabusRows = Object.entries(state.syllabus).slice(0, 6).map(([unit, topics]) => `<article class="link-card"><strong>${unit}</strong><span class="task-meta">${topics.slice(0, 2).join(' • ')}</span></article>`).join('');
  const links = resourceLinks.map((item) => `<article class="link-card"><strong>${item.title}</strong><a href="${item.url}" target="_blank" rel="noreferrer">Open resource</a></article>`).join('');
  el.resourceList.innerHTML = `${syllabusRows}${links}`;
}

function renderAnalytics() {
  const completion = state.progress?.completion_rate || 0;
  const pending = state.progress?.pending || 0;
  const done = state.progress?.completed || 0;
  el.analyticsStats.innerHTML = `<article><h3>${completion}%</h3><p>Completion Rate</p></article><article><h3>${done}</h3><p>Completed</p></article><article><h3>${pending}</h3><p>Pending</p></article>`;
  el.hoursTrend.innerHTML = `<p class="subtitle">Tracked study minutes: ${state.progress?.total_tracked_minutes || 0}</p>`;
  el.consistencyTrend.innerHTML = `<p class="subtitle">Current streak: ${state.progress?.study_streak || 0} days</p>`;
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme || 'dark');
}

function renderSettingsForm() {
  el.settingExamDate.value = state.settings.exam_date || '';
  el.settingDailyGoal.value = state.settings.daily_goal || 3;
  el.settingTheme.value = state.settings.theme || 'dark';
  applyTheme(state.settings.theme);
}

async function reloadData() {
  const data = await request(api.bootstrap);
  state.tasks = data.tasks;
  state.settings = data.settings;
  state.syllabus = data.syllabus;
  state.user = data.user;
  state.progress = await request(api.progress);
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
}

function wireForms() {
  el.logoutBtn.addEventListener('click', async () => {
    await request(api.logout, { method: 'POST' });
    window.location.href = config.logoutPageUrl;
  });

  el.taskUnit.addEventListener('change', updateTopicOptions);
  el.taskForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    await request(api.tasks, {
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
    state.settings = await request(api.settings, { method: 'PUT', body: JSON.stringify({ exam_date: el.settingExamDate.value || null, daily_goal: Number(el.settingDailyGoal.value || 3), theme: el.settingTheme.value }) });
    applyTheme(state.settings.theme);
    el.settingsMessage.textContent = 'Settings saved successfully.';
    await reloadData();
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

  el.timerPause.addEventListener('click', () => {
    if (state.timerHandle) {
      clearInterval(state.timerHandle);
      state.timerHandle = null;
    }
  });

  el.timerReset.addEventListener('click', () => {
    if (state.timerHandle) {
      clearInterval(state.timerHandle);
      state.timerHandle = null;
    }
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
  await reloadData();
  setRoute(document.body?.dataset.initialRoute || 'dashboard');
  setInterval(renderCountdown, 60 * 1000);
}

bootstrap().catch((error) => {
  console.error(error);
});
