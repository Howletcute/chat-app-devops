# CHANGELOG.md
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2025-04-19
### Added
- User registration and login functionality using PostgreSQL.
- Password hashing using Werkzeug.
- Session management using Flask-Login.
- Database migrations using Flask-Migrate (`users` table, `nickname_color` column).
- Required Python packages (SQLAlchemy, psycopg2, Flask-Login, Flask-WTF, etc.).
- Kubernetes manifests for PostgreSQL (Secret, PVC, Deployment, Service).
- Dark mode theme toggle with localStorage persistence (CSS Variables, JS).
- Nickname color customization stored in database (DB column, settings page picker, SocketIO handler).
- Dedicated `/settings` page for user customization.
- About page (`/about`) displaying build version/ref from `APP_VERSION` env var.
- Links to Changelog and GitHub Issues on About page.
- `CHANGELOG.md` file.
- Entrypoint script (`entrypoint.sh`) in Docker image to run database migrations (`flask db upgrade`) on container startup.

### Changed
- Refactored Flask application using Application Factory pattern and Blueprints (`app` package).
- Moved models, forms, routes, SocketIO events, helpers into separate modules within `app/`.
- Replaced anonymous nickname entry with user authentication systemwide (routes, SocketIO).
- Updated templates (`_base`, `index`, `chat`, `login`, `register`, `settings`) for auth state, refactoring, and new features.
- Updated `Dockerfile` to use `python:3.12-slim-bookworm`, copy new app structure, install `netcat`/`libpq-dev`, add entrypoint script, pass `APP_VERSION` build arg, use `run:app` in `CMD`.
- Updated `README.md` for v1.1.0 GKE deployment details.
- Updated CI/CD pipeline (`deploy.yml`) for GKE deployment using `kubectl apply`, Service Account auth, build args (`APP_VERSION`), commit SHA image tags, `gke-gcloud-auth-plugin` install.
- Moved CSS from inline `<style>` blocks to external `static/css/style.css`.
- Updated `python run.py` to use app factory and `eventlet.monkey_patch()`.
- Made GitHub repository public.

### Fixed
- Numerous local development server errors (Redis connect, NameErrors, TemplateSyntaxError, port conflict, monkey patching, `url_for` BuildError).
- Persistent CSS validation errors by moving CSS externally.
- Theme "flash" (FOUC) on page load & toggle switch animation glitch.
- Link readability in dark mode.
- CI/CD pipeline errors (Docker build cache, image tag SHA mismatch, auth plugin missing, `APP_VERSION` comment included).
- GKE ClusterIP allocation issues (by destroying/recreating cluster, removing cluster autoscaling block).
- Cert-manager installation failures on GKE (by adding `global.leaderElection.namespace`).
- Incorrect `.gitignore` entry for `migrations` directory.
- Missing `/register` route decorator.
- Missing `import os`.
- `redis-service` getting public ClusterIP due to stray NEG annotation (removed via `patch`, then service delete/recreate).

### Removed
- Original root-level `app.py` file.
- Ansible configuration files and related steps from CI/CD pipeline.
- Old nickname-based chat joining logic and routes.
- Note about public repo requirement from About page.

## [1.0.1] - 2025-04-16
### Fixed
- Corrected image tag name in README from 'todo-app' to 'chat-app'.

## [1.0.0] - 2025-04-15
### Added
- Initial simple chat application (Flask-SocketIO, Redis).
- Dockerfile and docker-compose for local running.
- Basic Ansible playbook to install Docker & Docker Compose on a VM.
- Terraform code to provision a GCP Compute Engine VM (`e2-micro`).
- GitHub Actions CI/CD pipeline to build/push image and deploy using Ansible/Compose via SSH.
- README.md with setup and deployment instructions.