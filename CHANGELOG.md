# CHANGELOG.md
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- About page displaying build version/ref.
- Links to Changelog and GitHub Issues on About page.

## [1.1.0] - 2025-04-19
### Added
- User registration and login functionality using PostgreSQL.
- Password hashing using Werkzeug.
- Session management using Flask-Login.
- Dark mode theme toggle with localStorage persistence.
- Nickname color customization stored in database.
- Dedicated `/settings` page for user customization.
- CI/CD pipeline for automated deployment to GKE using `kubectl apply`.
- Entrypoint script in Docker image to run database migrations (`flask db upgrade`) on startup.
- Database migrations using Flask-Migrate.
- Required Python packages (SQLAlchemy, psycopg2, Flask-Login, etc.).
- Kubernetes manifests for PostgreSQL (Secret, PVC, Deployment, Service).

### Changed
- Refactored Flask application using Application Factory pattern and Blueprints (`app` package).
- Moved models, forms, routes, events into separate modules.
- Replaced anonymous nickname entry with user authentication.
- Updated templates (`_base`, `index`, `chat`) for auth state and new features.
* Added new templates (`register.html`, `login.html`, `settings.html`).
- Updated `Dockerfile` to use `python:3.12-slim-bookworm`, copy new structure, add entrypoint script.
- Moved CSS to external `static/css/style.css` file.
- Updated `README.md` for GKE deployment (v1.1.0).

### Fixed
- Persistent CSS validation errors by moving CSS externally.
- Theme "flash" (FOUC) on page load.
- Link readability in dark mode.
- Various local development server errors (Redis connect, NameErrors, TemplateSyntaxError, port conflict, monkey patching).
- CI/CD pipeline errors (Docker build cache, image tag SHA mismatch, missing gke-auth-plugin).
- Incorrect ClusterIP assignment in GKE Standard by explicitly setting service CIDR via Terraform (then removed explicit setting as destroy/recreate fixed it - *Correction*: Explicit setting *was* needed, then removed cluster autoscaling block entirely). *Self-correction: The final working TF state used explicit IP policy initially, then removed cluster autoscaling block*. Need to ensure final TF code reflects this if documenting steps.
- Cert-manager installation failures on GKE by setting `global.leaderElection.namespace`.

### Removed
- Original `app.py` file.
- Standalone VM deployment resources from Terraform (`main` branch state).
- Ansible configuration (no longer used in deployment).
- Old nickname-based chat joining logic.

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