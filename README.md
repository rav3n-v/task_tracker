# CSIR NET Mathematics Task Tracker (Flask)

[![Lint](https://github.com/YOUR_GITHUB_USERNAME/task_tracker/actions/workflows/lint.yml/badge.svg)](https://github.com/YOUR_GITHUB_USERNAME/task_tracker/actions/workflows/lint.yml)
[![Tests](https://github.com/YOUR_GITHUB_USERNAME/task_tracker/actions/workflows/tests.yml/badge.svg)](https://github.com/YOUR_GITHUB_USERNAME/task_tracker/actions/workflows/tests.yml)
[![Format](https://github.com/YOUR_GITHUB_USERNAME/task_tracker/actions/workflows/format.yml/badge.svg)](https://github.com/YOUR_GITHUB_USERNAME/task_tracker/actions/workflows/format.yml)

A full-featured study planner and task tracker tailored to the CSIR NET Mathematics syllabus.

> Note: Replace `YOUR_GITHUB_USERNAME/task_tracker` in badge links with your actual GitHub repository path.

## Features
- User authentication (register, login, logout) with hashed passwords.
- User-specific task and settings data isolation.
- CSIR NET Mathematics syllabus included by default (unit + topic picker).
- Add tasks with priority, due date, and notes.
- Mark tasks complete/pending and delete tasks.
- Search tasks instantly.
- Dashboard cards for progress metrics and days remaining to exam.
- Settings page section for exam date, daily goal, and theme.
- Data persistence with SQLite + Flask-Migrate migrations.

## Run locally
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app app db upgrade
python main.py
```

Open `http://localhost:5000`.
