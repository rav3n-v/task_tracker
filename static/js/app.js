const state = {
  tasks: [],
  settings: {},
  syllabus: {},
  progress: null,
  timerSeconds: 0,
  timerHandle: null,
  search: '',
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
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return response.json();
}

function todayKey() {
  return new Date().toISOString().slice(0, 10);
}

function readJson(key, fallback) {
  const value = localStorage.getItem(key);
  return value ? JSON.parse(value) : fallback;
}

function writeJson(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function getRoutineState() {
  return readJson('routineState', {});
}

function setRoutineState(next) {
  writeJson('routineState', next);
}

function getDailyLog() {
  return readJson('dailyStudyLog', {});
}

function setDailyLog(next) {
  writeJson('dailyStudyLog', next);
}

function formatDuration(totalSeconds) {
  const h = String(Math.floor(totalSeconds / 3600)).padStart(2, '0');
  const m = String(Math.floor((totalSeconds % 3600) / 60)).padStart(2, '0');
  const s = String(totalSeconds % 60).padStart(2, '0');
  return `${h}:${m}:${s}`;
}

function setRoute(route) {
  const active = Object.hasOwn(el.views, route) ? route : 'dashboard';
  Object.values(el.views).forEach((view) => view.classList.remove('active'));
  el.views[active].classList.add('active');

  el.navLinks.forEach((link) => {
    link.classList.toggle('active', link.dataset.route === active);
  });
}

function handleRoute() {
  const route = window.location.hash.replace('#', '') || 'dashboard';
  setRoute(route);
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

  el.dashboardCards.innerHTML = cards.map((card) => `
    <article class="metric-card">
      <h3>${card.value}</h3>
      <p>${card.label}</p>
      <div class="metric-bar"><span style="width:${card.percent}%"></span></div>
    </article>
  `).join('');

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
    if ((log[key] || 0) > 0) streak += 1;
    else break;
  }
  el.streakText.textContent = `Study Streak: ${streak} days`;
}

function renderCountdown() {
  const targetText = state.settings.exam_date;
  const fallbackYear = new Date().getFullYear();
  const target = targetText ? new Date(targetText) : new Date(`${fallbackYear}-12-15T00:00:00`);

  const diff = Math.max(0, target.getTime() - Date.now());
  const minutesTotal = Math.floor(diff / 60000);
  const days = Math.floor(minutesTotal / (60 * 24));
  const hours = Math.floor((minutesTotal % (60 * 24)) / 60);
  const minutes = minutesTotal % 60;

  el.countDays.textContent = String(days).padStart(2, '0');
  el.countHours.textContent = String(hours).padStart(2, '0');
  el.countMinutes.textContent = String(minutes).padStart(2, '0');

  el.targetDate.textContent = `Target Exam: ${target.toLocaleDateString(undefined, { month: 'long', day: 'numeric', year: 'numeric' })}`;
}

function calculateDayMinutes(day) {
  const routine = getRoutineState()[day] || {};
  return routineTemplate.reduce((sum, item) => sum + (routine[item.id] ? item.minutes : 0), 0);
}

function renderRoutine() {
  const key = todayKey();
  const stateByDay = getRoutineState();
  const checkedToday = stateByDay[key] || {};

  el.routineList.innerHTML = routineTemplate.map((item) => `
    <article class="routine-item">
      <input type="checkbox" data-id="${item.id}" ${checkedToday[item.id] ? 'checked' : ''} />
      <div class="routine-time">${item.time}</div>
      <label>${item.task}</label>
      <div class="routine-tag">${item.tag}</div>
    </article>
  `).join('');

  el.routineList.querySelectorAll('input[type="checkbox"]').forEach((input) => {
    input.addEventListener('change', () => {
      const current = getRoutineState();
      const dayState = current[key] || {};
      dayState[input.dataset.id] = input.checked;
      current[key] = dayState;
      setRoutineState(current);
      updateStudyLog();
      renderRoutineStats();
      renderHeaderBits();
      renderAnalytics();
    });
  });

  renderRoutineStats();
}

function renderRoutineStats() {
  const now = new Date();
  const todayMinutes = calculateDayMinutes(todayKey());

  let weekMinutes = 0;
  for (let i = 0; i < 7; i += 1) {
    const day = new Date(now);
    day.setDate(now.getDate() - i);
    weekMinutes += calculateDayMinutes(day.toISOString().slice(0, 10));
  }

  el.hoursToday.textContent = (todayMinutes / 60).toFixed(1);
  el.hoursWeek.textContent = (weekMinutes / 60).toFixed(1);
}

function updateStudyLog() {
  const key = todayKey();
  const log = getDailyLog();
  log[key] = calculateDayMinutes(key);
  setDailyLog(log);
}

function last7Days() {
  const out = [];
  for (let i = 6; i >= 0; i -= 1) {
    const day = new Date();
    day.setDate(day.getDate() - i);
    out.push(day);
  }
  return out;
}

function renderAnalytics() {
  const log = getDailyLog();
  const series = last7Days().map((d) => {
    const key = d.toISOString().slice(0, 10);
    return { day: d.toLocaleDateString(undefined, { weekday: 'short' }), minutes: log[key] || 0 };
  });

  const avgHours = series.reduce((sum, item) => sum + item.minutes, 0) / (series.length * 60);
  const consistency = (series.filter((item) => item.minutes > 0).length / series.length) * 100;
  const predicted = Math.round((state.progress?.completion_rate || 0) * 1.1);

  el.analyticsStats.innerHTML = `
    <article><p>PERFORMANCE SCORE</p><h3>${Math.round((state.progress?.completion_rate || 0) / 10)}</h3><p>↑ +5%</p></article>
    <article><p>EFFICIENCY RATING</p><h3>${avgHours.toFixed(1)}</h3><p>→ Improving</p></article>
    <article><p>PREDICTED SCORE</p><h3>${predicted}</h3><p>Range: ${Math.max(predicted - 20, 0)}-${predicted + 10}</p></article>
  `;

  const maxMin = Math.max(...series.map((item) => item.minutes), 60);
  el.hoursTrend.innerHTML = series.map((item) => {
    const h = Math.max(6, (item.minutes / maxMin) * 160);
    return `<div class="bar" style="height:${h}px;background:#2eb8d8;"><span>${item.day}</span></div>`;
  }).join('');

  el.consistencyTrend.innerHTML = series.map((item, index) => {
    const x = (index / (series.length - 1)) * 95;
    const y = 95 - ((item.minutes > 0 ? 1 : 0) * 85);
    return `<div class="point" style="left:${x}%;top:${y}%;"></div>`;
  }).join('');

  const consistencyText = document.createElement('p');
  consistencyText.textContent = `Consistency: ${consistency.toFixed(0)}% study days this week`;
  consistencyText.style.color = '#8d98ad';
  consistencyText.style.marginTop = '1.2rem';
  el.consistencyTrend.appendChild(consistencyText);
}

function populateSyllabus() {
  const units = Object.keys(state.syllabus);
  el.taskUnit.innerHTML = units.map((unit) => `<option value="${unit}">${unit}</option>`).join('');
  updateTopicOptions();

  el.taskUnit.addEventListener('change', updateTopicOptions);
}

function updateTopicOptions() {
  const topics = state.syllabus[el.taskUnit.value] || [];
  el.taskTopic.innerHTML = topics.map((topic) => `<option value="${topic}">${topic}</option>`).join('');
}

function taskMatchesSearch(task) {
  if (!state.search) return true;
  const bag = `${task.title} ${task.unit} ${task.topic}`.toLowerCase();
  return bag.includes(state.search.toLowerCase());
}

function renderTasks() {
  const ordered = [...state.tasks].sort((a, b) => Number(a.completed) - Number(b.completed));
  const filtered = ordered.filter(taskMatchesSearch);
  el.taskList.innerHTML = filtered.map((task) => `
    <article class="task-item">
      <input class="task-toggle" data-id="${task.id}" type="checkbox" ${task.completed ? 'checked' : ''} />
      <div>
        <strong>${task.title}</strong>
        <div class="task-meta">${task.unit} · ${task.topic}</div>
        <div class="task-meta">Due: ${task.due_date || 'Not set'}${task.notes ? ` · ${task.notes}` : ''}</div>
      </div>
      <div class="task-actions">
        <span class="badge ${task.priority.toLowerCase()}">${task.priority}</span>
        <button class="task-delete" data-id="${task.id}">Delete</button>
      </div>
    </article>
  `).join('');

  el.taskList.querySelectorAll('.task-toggle').forEach((checkbox) => {
    checkbox.addEventListener('change', async () => {
      await request(`/api/tasks/${checkbox.dataset.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ completed: checkbox.checked }),
      });
      await reloadData();
    });
  });

  el.taskList.querySelectorAll('.task-delete').forEach((button) => {
    button.addEventListener('click', async () => {
      await request(`/api/tasks/${button.dataset.id}`, { method: 'DELETE' });
      await reloadData();
    });
  });
}

function renderTests() {
  const total = state.tasks.length;
  const completed = state.tasks.filter((item) => item.completed).length;
  const pending = total - completed;
  el.testStats.innerHTML = `
    <article class="metric-card"><h3>${completed}</h3><p>Completed Mocks</p></article>
    <article class="metric-card"><h3>${pending}</h3><p>Pending Mocks</p></article>
    <article class="metric-card"><h3>${state.settings.daily_goal || 3}</h3><p>Daily Goal</p></article>
  `;
}

function renderDownloads() {
  el.downloadList.innerHTML = [
    { title: 'Weekly revision checklist', subtitle: 'Print-friendly checklist template', url: '#' },
    { title: 'Mock test log sheet', subtitle: 'Track score and mistakes', url: '#' },
    { title: 'Important formula summary', subtitle: 'Compact formula handout', url: '#' },
  ].map((item) => `
    <article class="link-card">
      <strong>${item.title}</strong>
      <span class="task-meta">${item.subtitle}</span>
      <a href="${item.url}">Download</a>
    </article>
  `).join('');
}

function renderResources() {
  const syllabusRows = Object.entries(state.syllabus).slice(0, 6).map(([unit, topics]) => `
    <article class="link-card">
      <strong>${unit}</strong>
      <span class="task-meta">${topics.slice(0, 2).join(' • ')}</span>
    </article>
  `).join('');

  const links = resourceLinks.map((item) => `
    <article class="link-card">
      <strong>${item.title}</strong>
      <a href="${item.url}" target="_blank" rel="noreferrer">Open resource</a>
    </article>
  `).join('');

  el.resourceList.innerHTML = `${syllabusRows}${links}`;
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

function wireForms() {
  el.taskForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    await request('/api/tasks', {
      method: 'POST',
      body: JSON.stringify({
        title: el.taskTitle.value,
        unit: el.taskUnit.value,
        topic: el.taskTopic.value,
        priority: el.taskPriority.value,
        due_date: el.taskDueDate.value || null,
        notes: el.taskNotes.value,
      }),
    });
    el.taskForm.reset();
    updateTopicOptions();
    await reloadData();
  });

  el.taskSearch.addEventListener('input', () => {
    state.search = el.taskSearch.value;
    renderTasks();
  });

  el.settingsForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    state.settings = await request('/api/settings', {
      method: 'PUT',
      body: JSON.stringify({
        exam_date: el.settingExamDate.value || null,
        daily_goal: Number(el.settingDailyGoal.value || 3),
        theme: el.settingTheme.value,
      }),
    });
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

  el.timerPause.addEventListener('click', () => {
    if (!state.timerHandle) return;
    clearInterval(state.timerHandle);
    state.timerHandle = null;
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

async function reloadData() {
  const data = await request('/api/bootstrap');
  state.tasks = data.tasks;
  state.settings = data.settings;
  state.syllabus = data.syllabus;
  state.progress = await request('/api/progress');

  renderDashboard();
  renderCountdown();
  renderTasks();
  renderTests();
  renderSettingsForm();
  renderAnalytics();
}

async function bootstrap() {
  await reloadData();

  state.timerSeconds = Number(localStorage.getItem('studyTimerSeconds') || 0);
  el.timerDisplay.textContent = formatDuration(state.timerSeconds);

  populateSyllabus();
  renderHeaderBits();
  renderRoutine();
  renderDownloads();
  renderResources();
  wireForms();

  setInterval(renderCountdown, 60 * 1000);
}

window.addEventListener('hashchange', handleRoute);
el.navLinks.forEach((link) => link.addEventListener('click', () => setRoute(link.dataset.route)));

wireTimer();
handleRoute();
bootstrap();
