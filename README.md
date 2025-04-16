# Real-Time Chat Application (v1.0)

## Description

This project implements a simple, anonymous real-time chat application. Users can choose a nickname, enter a common chat room, send messages, and see who else is online.

It serves as a demonstration of deploying a containerized web application using modern DevOps practices and tools. Version 1.0 deploys the application to a single Google Cloud Platform (GCP) Compute Engine VM using Docker Compose, provisioned via Terraform and Ansible, with CI/CD handled by GitHub Actions.

## Features (v1.0)

* Anonymous login using a chosen nickname.
* Single, common chat room for all connected users.
* Real-time message broadcasting using WebSockets (Flask-SocketIO).
* Display list of currently online users.
* Basic message history loaded on joining.

## Technology Stack

* **Backend:** Python, Flask, Flask-SocketIO, Eventlet
* **Database:** Redis (for message history and online user tracking)
* **Containerization:** Docker, Docker Compose
* **Infrastructure as Code:** Terraform
* **Configuration Management:** Ansible (for initial server setup)
* **Cloud Provider:** Google Cloud Platform (GCP)
* **CI/CD:** GitHub Actions
* **Version Control:** Git

## Prerequisites

Before you begin, ensure you have the following installed and configured:

1.  **Git:** For cloning the repository.
2.  **Docker & Docker Compose:** For running the application locally and building images. ([Install Docker](https://docs.docker.com/engine/install/))
3.  **Terraform CLI:** For provisioning cloud infrastructure. ([Install Terraform](https://developer.hashicorp.com/terraform/downloads))
4.  **Ansible:** For configuring the server (can be installed via pip: `pip install ansible`).
5.  **Google Cloud SDK (`gcloud`):** For interacting with GCP, including authentication. ([Install gcloud](https://cloud.google.com/sdk/docs/install))
6.  **Google Cloud Platform (GCP) Account:** With an active project and **Billing Enabled**. Even free tier usage requires billing to be enabled.
7.  **Docker Hub Account:** To store and retrieve the application's Docker image. ([Create Account](https://hub.docker.com/))
8.  **GitHub Account:** To host the repository and use GitHub Actions.

## Running Locally

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Howletcute/chat-app-devops.git
    cd chat-app-devops
    ```
2.  **Create Environment File:** Create a `.env` file in the project root for local development secrets (this file is gitignored):
    ```dotenv
    # .env
    SECRET_KEY=a_local_secret_dev_key_!@#
    ```
    *(Note: The `docker-compose.yml` file is configured to use a Redis service named `db`, so specific REDIS variables aren't usually needed here when using compose)*

3.  **Build and Run with Docker Compose:**
    ```bash
    docker compose up --build -d
    ```
4.  **Access:** Open your web browser to `http://localhost:5001`.

## Deploying to GCP (Free Tier Focus)

This outlines the process to deploy the application to a single GCP VM, aiming to stay within the Always Free tier limits.

## Deploying to GCP (Free Tier Focus)

This outlines the process to deploy the application from this repository to a single GCP VM, aiming to stay within the Always Free tier limits. It assumes you have contributor/owner access to this repository or a fork of it to configure secrets and Actions.

**1. Prerequisites Check:**

* Ensure you have met all items listed in the [Prerequisites](#prerequisites) section above.

**2. GCP Setup:**

* Ensure you have a GCP Project with **Billing Enabled**.
* Create a unique Google Cloud Storage (GCS) bucket to store Terraform's remote state. **Object Versioning must be enabled.** Replace placeholders below:
    ```bash
    gcloud storage buckets create gs://<YOUR-UNIQUE-BUCKET-NAME> --project=<YOUR-PROJECT-ID> --location=<GCP_REGION e.g., us-central1> --uniform-bucket-level-access --versioning
    ```

**3. Terraform Setup:**

* **Clone Repository:** If you haven't already cloned this project repository:
    ```bash
    # Replace with the actual HTTPS or SSH URL of your repository
    git clone [https://github.com/howletcute/chat-app-devops.git](https://github.com/howletcute/chat-app-devops.git)
    cd chat-app-devops
    ```
* **Configure Backend:** Edit `terraform/backend.tf` and replace `"YOUR-UNIQUE-BUCKET-NAME"` with the name of the GCS bucket you created.
* **Configure Variables:** Create a `terraform/terraform.tfvars` file (ensure this file is in your `.gitignore`!) with the following content, replacing placeholders:
    ```hcl
    # terraform/terraform.tfvars
    gcp_project_id = "<YOUR-PROJECT-ID>"
    ssh_source_ip  = "<YOUR_PUBLIC_IP>/32" # e.g., "8.8.8.8/32"
    ```
* **Initialize & Apply:** Navigate to the `terraform` directory and run:
    ```bash
    cd terraform
    terraform init # Will configure the GCS backend
    terraform plan # Review the planned infrastructure
    terraform apply # Type 'yes' to create the resources
    ```
    Note the `instance_public_ip` output value.

**4. GitHub Actions Setup (Secrets & Keys):**

* This needs to be done on the GitHub repository where the Actions workflow will run (either the main project repo if you have access, or your fork).
* **Generate SSH Key:** Create a new SSH key pair (`ssh-keygen ...`).
* **Generate Docker Hub Token:** Create an Access Token on Docker Hub.
* **Add GitHub Secrets:** In the repository settings (Settings > Secrets and variables > Actions), add the required secrets (`DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, `SSH_PRIVATE_KEY`, `SSH_HOST` [use VM IP from terraform output], `SSH_USER` [your username on the VM]).
* **Add Public Key to VM:** Add the SSH public key to the VM's `~/.ssh/authorized_keys` file (connect via `gcloud compute ssh ...`).

**5. Deployment Trigger:**

* Pushing changes to the `main` branch of the repository configured with secrets will trigger the GitHub Actions workflow in `.github/workflows/deploy.yml`.
* The pipeline builds and pushes the `howletcute/chat-app:latest` image and deploys it to the VM.

**6. Accessing the Application:**

* Once the pipeline completes successfully after a push to `main`, open your browser and navigate to `http://<VM_PUBLIC_IP>:5001`.


## Project Structure

```text
.
├── .github/workflows/      # GitHub Actions CI/CD pipeline
│   └── deploy.yml
├── ansible/                # Ansible configuration
│   ├── configure-vm.yml    # Playbook to setup Docker on VM (v1.0 state)
│   ├── deploy-app.yml      # Playbook for app deployment (used by CI/CD logic)
│   └── inventory.ini       # Ansible inventory file
├── templates/              # Flask HTML templates
│   ├── chat.html
│   └── index.html
├── terraform/              # Terraform infrastructure code
│   ├── backend.tf          # GCS backend configuration
│   ├── gke.tf              # GKE cluster definition (Added in feature branch)
│   ├── main.tf             # Core resources (VM, Firewall in v1.0)
│   ├── outputs.tf          # Terraform outputs
│   ├── providers.tf        # Terraform provider configuration
│   └── variables.tf        # Terraform input variables
├── .env                    # Local environment variables (Gitignored)
├── .gitignore
├── app.py                  # Main Flask application code
├── Dockerfile              # Docker build instructions
├── docker-compose.yml      # Docker Compose configuration
├── README.md               # This file
└── requirements.txt        # Python dependencies

## Future Improvements (Post v1.0)

* Migrate deployment to Google Kubernetes Engine (GKE).
* Implement user authentication (login/passwords).
* Add proper error handling and user feedback (e.g., nickname taken).
* Set up monitoring and logging.
* Use a managed database service (Cloud SQL) instead of containerized Redis/Postgres.
* Improve CI/CD pipeline (testing, staging environments, security scanning).
* Manage secrets more securely (e.g., Vault, GCP Secret Manager).
* Refactor Ansible playbook to reliably use `signed-by=` GPG key method if possible.