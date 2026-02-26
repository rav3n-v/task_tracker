const state = {
  tasks: [],
  settings: {},
  progress: null,
  timerSeconds: 0,
  timerHandle: null,
};

const routineTemplate = [
  { id: 'r1', time: '5:00 AM - 5:30 AM', task: 'Wake up, Exercise, Wash up', tag: 'Physical', minutes: 30 },
  { id: 'r2', time: '6:00 AM - 7:00 AM', task: 'Practise General/ Part A', tag: 'Study', minutes: 60 },
  { id: 'r3', time: '7:00 AM - 8:30 AM', task: 'Fresh up, Breakfast', tag: 'Nutrition', minutes: 90 },
  { id: 'r4', time: '8:30 AM - 9:30 AM', task: 'Previous day revision', tag: 'Study', minutes: 60 },
  { id: 'r5', time: '9:30 AM - 12:30 PM', task: 'Core Study Session 1', tag: 'Study', minutes: 180 },
  { id: 'r6', time: '12:30 PM - 1:30 PM', task: 'Lunch Break', tag: 'Break', minutes: 60 },
  { id: 'r7', time: '1:30 PM - 4:30 PM', task: 'Core Study Session 2', tag: 'Study', minutes: 180 },
];

const el = {
  navLinks: document.querySelectorAll('.nav-links a'),
  views: {
    dashboard: document.getElementById('dashboardView'),
    routine: document.getElementById('routineView'),
    analytics: document.getElementById('analyticsView'),
    placeholder: document.getElementById('placeholderView'),
  },
  placeholderTitle: document.getElementById('placeholderTitle'),
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
  const active = ['dashboard', 'routine', 'analytics'].includes(route) ? route : 'placeholder';
  Object.values(el.views).forEach((view) => view.classList.remove('active'));
  el.views[active].classList.add('active');

  el.navLinks.forEach((link) => {
    link.classList.toggle('active', link.dataset.route === route);
  });

  if (active === 'placeholder') {
    const link = [...el.navLinks].find((item) => item.dataset.route === route);
    el.placeholderTitle.textContent = link ? link.textContent : 'Module';
  }
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
    const h = Math.max(6, (item.minutes / maxMin) * 180);
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

async function bootstrap() {
  const data = await request('/api/bootstrap');
  state.tasks = data.tasks;
  state.settings = data.settings;
  state.progress = await request('/api/progress');

  state.timerSeconds = Number(localStorage.getItem('studyTimerSeconds') || 0);
  el.timerDisplay.textContent = formatDuration(state.timerSeconds);

  renderDashboard();
  renderHeaderBits();
  renderCountdown();
  renderRoutine();
  renderAnalytics();

  setInterval(renderCountdown, 60 * 1000);
}

window.addEventListener('hashchange', handleRoute);
el.navLinks.forEach((link) => link.addEventListener('click', () => setRoute(link.dataset.route)));

wireTimer();
handleRoute();
bootstrap();
