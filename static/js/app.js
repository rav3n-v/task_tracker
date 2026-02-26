const state = {
  tasks: [],
  settings: {},
  syllabus: {},
};

const el = {
  taskForm: document.getElementById('taskForm'),
  settingsForm: document.getElementById('settingsForm'),
  unitSelect: document.getElementById('unitSelect'),
  topicSelect: document.getElementById('topicSelect'),
  taskList: document.getElementById('taskList'),
  taskTemplate: document.getElementById('taskItemTemplate'),
  statsGrid: document.getElementById('statsGrid'),
  taskSearch: document.getElementById('taskSearch'),
  syllabusGrid: document.getElementById('syllabusGrid'),
  themeToggle: document.getElementById('themeToggle'),
};

async function request(url, options = {}) {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return response.json();
}

function fillUnitOptions() {
  el.unitSelect.innerHTML = Object.keys(state.syllabus)
    .map((unit) => `<option value="${unit}">${unit}</option>`)
    .join('');
  fillTopicOptions();
}

function fillTopicOptions() {
  const unit = el.unitSelect.value;
  el.topicSelect.innerHTML = (state.syllabus[unit] || [])
    .map((topic) => `<option value="${topic}">${topic}</option>`)
    .join('');
}

function renderSyllabus() {
  el.syllabusGrid.innerHTML = Object.entries(state.syllabus)
    .map(([unit, topics]) => `
      <article class="syllabus-card">
        <h3>${unit}</h3>
        <ul>${topics.map((t) => `<li>${t}</li>`).join('')}</ul>
      </article>
    `).join('');
}

function renderStats(progress) {
  const cards = [
    ['Total Tasks', progress.total],
    ['Completed', progress.completed],
    ['Pending', progress.pending],
    ['Completion Rate', `${progress.completion_rate}%`],
    ['Days to Exam', progress.days_left ?? 'Set exam date'],
  ];
  el.statsGrid.innerHTML = cards
    .map(([label, value]) => `<article class="stat-card"><p>${label}</p><h3>${value}</h3></article>`)
    .join('');
}

function renderTasks() {
  const query = el.taskSearch.value.trim().toLowerCase();
  const tasks = state.tasks.filter((task) => (
    `${task.title} ${task.unit} ${task.topic}`.toLowerCase().includes(query)
  ));

  el.taskList.innerHTML = '';
  tasks.forEach((task) => {
    const node = el.taskTemplate.content.cloneNode(true);
    const li = node.querySelector('.task-item');
    li.dataset.id = task.id;
    if (task.completed) li.classList.add('done');
    node.querySelector('h3').textContent = task.title;
    node.querySelector('.meta').textContent = `${task.unit} • ${task.topic} • ${task.priority} priority${task.due_date ? ` • due ${task.due_date}` : ''}`;
    node.querySelector('.notes').textContent = task.notes || 'No notes';

    const toggle = node.querySelector('.toggle-btn');
    toggle.textContent = task.completed ? 'Mark Pending' : 'Mark Done';
    toggle.addEventListener('click', () => toggleTask(task));

    node.querySelector('.delete-btn').addEventListener('click', () => removeTask(task.id));
    el.taskList.appendChild(node);
  });
}

async function refreshProgress() {
  const progress = await request('/api/progress');
  renderStats(progress);
}

async function bootstrap() {
  const data = await request('/api/bootstrap');
  state.tasks = data.tasks;
  state.settings = data.settings;
  state.syllabus = data.syllabus;

  fillUnitOptions();
  renderSyllabus();
  renderTasks();
  await refreshProgress();

  el.settingsForm.exam_date.value = state.settings.exam_date || '';
  el.settingsForm.daily_goal.value = state.settings.daily_goal;
  el.settingsForm.theme.value = state.settings.theme;
  document.documentElement.dataset.theme = state.settings.theme;
}

el.unitSelect.addEventListener('change', fillTopicOptions);
el.taskSearch.addEventListener('input', renderTasks);

el.taskForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const formData = new FormData(el.taskForm);
  const payload = Object.fromEntries(formData.entries());
  const created = await request('/api/tasks', { method: 'POST', body: JSON.stringify(payload) });
  state.tasks.unshift(created);
  el.taskForm.reset();
  fillTopicOptions();
  renderTasks();
  await refreshProgress();
});

el.settingsForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(el.settingsForm).entries());
  payload.daily_goal = Number(payload.daily_goal || 3);
  state.settings = await request('/api/settings', { method: 'PUT', body: JSON.stringify(payload) });
  document.documentElement.dataset.theme = state.settings.theme;
  await refreshProgress();
});

el.themeToggle.addEventListener('click', async () => {
  const nextTheme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  el.settingsForm.theme.value = nextTheme;
  const payload = Object.fromEntries(new FormData(el.settingsForm).entries());
  payload.theme = nextTheme;
  payload.daily_goal = Number(payload.daily_goal || 3);
  state.settings = await request('/api/settings', { method: 'PUT', body: JSON.stringify(payload) });
  document.documentElement.dataset.theme = nextTheme;
});

async function toggleTask(task) {
  const updated = await request(`/api/tasks/${task.id}`, {
    method: 'PATCH',
    body: JSON.stringify({ completed: !task.completed }),
  });
  state.tasks = state.tasks.map((item) => (item.id === updated.id ? updated : item));
  renderTasks();
  await refreshProgress();
}

async function removeTask(taskId) {
  await request(`/api/tasks/${taskId}`, { method: 'DELETE' });
  state.tasks = state.tasks.filter((task) => task.id !== taskId);
  renderTasks();
  await refreshProgress();
}

bootstrap();
