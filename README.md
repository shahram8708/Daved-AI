# Daved AI

Daved AI is a Flask-based platform for AI-assisted software project generation and management. Users can submit a project idea prompt, the system improves the prompt, breaks the build into structured steps, generates source files using Google Generative AI, tracks progress, stores project history, and packages the final output as downloadable ZIP files.

The application includes authentication, user dashboards, admin controls, feature flags, monitoring metrics, background task handling, and a modern web UI.

---

## Overview

Daved AI provides an end-to-end workflow for turning a project concept into an organized codebase:

* Secure user authentication and session handling
* AI-powered multi-step project generation
* Improved prompt processing
* Step-by-step project execution with database persistence
* Source file creation and storage
* One-click project ZIP export
* Project resume and recovery from database
* Activity tracking and admin auditing
* System monitoring and Prometheus metrics
* Feature flag controls
* Background scheduled maintenance
* Theming and localization preferences

The platform is built using Flask, SQLAlchemy, Flask-Migrate, Flask-Login, Google Generative AI, Prometheus monitoring, and supporting utilities.

---

## Features

* User registration, login, logout
* Profile management with theme and language preferences
* Create and manage multiple AI projects
* Prompt improvement engine
* AI-backed code generation using Google Generative AI
* Structured project steps with tracking
* Automatic file creation and hierarchical storage
* Download generated projects as ZIP archives
* Regenerate ZIPs or recreate from stored database state
* Progress pages and status feedback
* Admin dashboard
* User and project management
* Activity logging and admin action history
* Feature flag management
* CSV export utilities in admin
* Prometheus-based metrics and request monitoring
* Background cleanup jobs
* CSRF protection
* Session security

---

## Tech Stack

**Backend**

* Flask
* Flask-Login
* Flask-SQLAlchemy
* Flask-Migrate
* Flask-WTF CSRF
* APScheduler
* Prometheus Client
* Google Generative AI (`google.generativeai`)

**Database**

* SQLite (default)
* Supports PostgreSQL or other SQLAlchemy-supported databases via configuration

**Frontend**

* Jinja2 templates
* HTML / CSS / JavaScript
* Bootstrap-based UI

**Utilities**

* dotenv
* Zip handling services
* Monitoring and metrics utilities
* Prompt improvement tools
* Intent safety checks

Dependencies are listed in `requirements.txt`.

---

## Project Structure

```
Daved-AI/
│
├── app/
│   ├── __init__.py                # App factory and setup
│   ├── models.py                  # Database models
│   ├── auth/                      # Authentication routes & forms
│   ├── main/                      # Main user-facing routes
│   ├── admin/                     # Admin dashboard & tools
│   ├── codegen/                   # AI project generation workflow
│   ├── services/                  # Codegen and ZIP services
│   ├── utils/                     # Monitoring, flags, decorators, prompts
│   ├── static/                    # CSS, JS, assets
│   └── templates/                 # Full web UI
│
├── static/zips/                   # Generated project ZIPs
├── temp_projects/                 # Temporary build output
├── config.py                      # Configuration setup
├── create_admin.py                # Helper to create admin account
├── run.py                         # Application entry
├── requirements.txt
└── daved_ai.db                    # Default SQLite database
```

---

## Installation

1. Extract or clone the repository.
2. Ensure Python is installed.
3. Install project dependencies:

```
pip install -r requirements.txt
```

4. Initialize the database:

```
flask db upgrade
```

5. (Optional) Create an admin user:

```
python create_admin.py
```

---

## Configuration

Configuration values are loaded through `config.py` and `.env`.

Key settings:

```
SECRET_KEY=
DATABASE_URL=
GEMINI_API_KEY=
```

Defaults:

* SQLite database is used if no database URL is provided.
* Gemini API key must be valid for project generation.
* Temporary and ZIP directories are automatically managed.

Prometheus metrics can be enabled using config flags already embedded in the application logic.

---

## Running the Application

Start the application:

```
python run.py
```

The application runs in development mode by default.

Open in a browser:

```
http://localhost:5000
```

---

## Usage

### User

* Register or log in
* Create a new AI project
* Submit a prompt
* View improved prompt and structured steps
* Allow AI to generate code
* View project progress
* Download generated ZIP
* Manage previously created projects

### Admin

* Access dashboard
* View statistics
* Manage users
* Manage projects
* View admin activity logs
* Enable / disable feature flags
* Perform moderation actions

---

## Monitoring

* Request metrics and API latency are tracked
* AI usage counters included
* Prometheus-compatible metrics server can be enabled
* Background scheduler is configured for maintenance and cleanup tasks

---

## Notes

* Google Generative AI key is required for code generation
* Internet connectivity is required for AI features
* ZIP downloads are automatically cleaned up after completion
* Feature flags determine whether certain capabilities are available
* Project data is persisted and can be reconstructed even if temp files are removed

---

## Troubleshooting

* Ensure dependencies are installed
* Verify database initializes correctly
* Confirm Gemini API key is valid
* Check server logs for AI response formatting errors
* Ensure temporary and ZIP directories are writable
* If downloads fail, check file permissions and cleanup behavior
* Prometheus may require proper environment enablement

---

This repository does not include a license file.
