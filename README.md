# CSIR NET Mathematics Task Tracker (Flask)

A full-featured study planner and task tracker tailored to the CSIR NET Mathematics syllabus.

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
