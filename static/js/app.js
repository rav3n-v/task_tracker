// ======================================
// CSIR NET Tracker - SPA Controller
// ======================================

// -----------------------------
// STATE
// -----------------------------
const state = {
  timerSeconds: 0,
  timerHandle: null,
};

// -----------------------------
// DOM REFERENCES
// -----------------------------
const el = {
  navLinks: document.querySelectorAll(".nav-links a"),

  views: {
    dashboard: document.getElementById("dashboardView"),
    plan: document.getElementById("planView"),
    routine: document.getElementById("routineView"),
    session: document.getElementById("sessionView"),
    tests: document.getElementById("testsView"),
    downloads: document.getElementById("downloadsView"),
    analytics: document.getElementById("analyticsView"),
    resources: document.getElementById("resourcesView"),
    settings: document.getElementById("settingsView"),
    syllabus: document.getElementById("syllabusView"),
    "score-predictor": document.getElementById("scorePredictorView"),
  },

  timerDisplay: document.getElementById("timerDisplay"),
  timerStart: document.getElementById("timerStart"),
  timerPause: document.getElementById("timerPause"),
  timerReset: document.getElementById("timerReset"),
};

// ======================================
// ROUTING (SPA)
// ======================================

function setRoute(route) {
  const active = Object.hasOwn(el.views, route) ? route : "dashboard";

  Object.values(el.views).forEach((v) =>
    v?.classList.remove("active")
  );

  el.views[active]?.classList.add("active");

  el.navLinks.forEach((link) => {
    link.classList.toggle(
      "active",
      link.dataset.route === active
    );
  });
}

function initNavigation() {
  el.navLinks.forEach((link) => {
    link.addEventListener("click", (e) => {
      e.preventDefault();

      const route = link.dataset.route;
      if (!route) return;

      setRoute(route);
      history.pushState(null, "", `/${route}`);
    });
  });

  window.addEventListener("popstate", () => {
    const path = window.location.pathname.replace("/", "");
    setRoute(path || "dashboard");
  });
}

// ======================================
// SYLLABUS (Aligned with your backend)
// ======================================

async function updateSyllabus(topicId, field, value) {
  try {
    const res = await fetch("/api/syllabus-progress", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({
        topic_id: topicId,
        field: field,
        value: value,
      }),
    });

    if (!res.ok) {
      console.error("Update failed");
      return;
    }

    await refreshSyllabusProgress();

  } catch (err) {
    console.error("Syllabus update error:", err);
  }
}

async function refreshSyllabusProgress() {
  try {
    const res = await fetch("/api/syllabus-progress", {
      credentials: "same-origin",
    });

    if (!res.ok) return;

    const data = await res.json();

    // Update top progress cards
    const cards = document.querySelectorAll(".metric-card");

    if (cards.length >= 4) {
      cards[0].querySelector("h3").textContent =
        data.theory_percent + "%";
      cards[1].querySelector("h3").textContent =
        data.pyq_percent + "%";
      cards[2].querySelector("h3").textContent =
        data.revision_1_percent + "%";
      cards[3].querySelector("h3").textContent =
        data.revision_2_percent + "%";
    }

  } catch (err) {
    console.error("Refresh error:", err);
  }
}

function initSyllabusListeners() {
  document.addEventListener("change", (event) => {
    const target = event.target;

    if (!target.classList.contains("syllabus-toggle"))
      return;

    const topicId = Number(target.dataset.topicId);
    const field = target.dataset.field;
    const value = target.checked;

    updateSyllabus(topicId, field, value);
  });
}

// ======================================
// TIMER
// ======================================

function formatTime(seconds) {
  const hrs = Math.floor(seconds / 3600)
    .toString()
    .padStart(2, "0");
  const mins = Math.floor((seconds % 3600) / 60)
    .toString()
    .padStart(2, "0");
  const secs = (seconds % 60)
    .toString()
    .padStart(2, "0");

  return `${hrs}:${mins}:${secs}`;
}

function updateTimerDisplay() {
  if (el.timerDisplay) {
    el.timerDisplay.textContent = formatTime(
      state.timerSeconds
    );
  }
}

function startTimer() {
  if (state.timerHandle) return;

  state.timerHandle = setInterval(() => {
    state.timerSeconds++;
    updateTimerDisplay();
  }, 1000);
}

function pauseTimer() {
  clearInterval(state.timerHandle);
  state.timerHandle = null;
}

function resetTimer() {
  pauseTimer();
  state.timerSeconds = 0;
  updateTimerDisplay();
}

function initTimer() {
  el.timerStart?.addEventListener("click", startTimer);
  el.timerPause?.addEventListener("click", pauseTimer);
  el.timerReset?.addEventListener("click", resetTimer);
}

// ======================================
// BOOTSTRAP
// ======================================

function bootstrap() {
  const initialRoute =
    document.body?.dataset.initialRoute || "dashboard";

  setRoute(initialRoute);
  initNavigation();
  initSyllabusListeners();
  initTimer();
}

document.addEventListener("DOMContentLoaded", bootstrap);