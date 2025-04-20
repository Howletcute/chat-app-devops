# Real-Time Chat Application (v1.3.0 - GKE Deployment Template)

## Description

This project provides a template for deploying a real-time chat application using Flask-SocketIO, Redis, and PostgreSQL onto Google Kubernetes Engine (GKE). It includes user authentication with **email confirmation**, **password reset functionality**, basic chat features, and customization options. Infrastructure is provisioned via Terraform, deployment can be automated via GitHub Actions, and TLS/HTTPS is handled by cert-manager and Nginx Ingress. This guide assumes deployment to a custom domain.

**Note on Cost:** The default Terraform configuration uses resources (like `e2-medium` nodes) that may require a GCP account with active billing and potentially the Free Trial credit to run without incurring significant costs. Adjust Terraform variables (e.g., `gke_node_machine_type`) based on your budget and needs.

## Features (v1.3.0)

* **User Authentication:**
    * User registration and login functionality using PostgreSQL[cite: 401].
    * Password hashing using Werkzeug[cite: 401].
    * Session management using Flask-Login[cite: 401].
    * **Email confirmation required** before login is allowed[cite: 416].
    * **Forgot Password / Password Reset** functionality via email link[cite: 416].
* **Database:** Migrations using Flask-Migrate[cite: 401].
* **User Customization:**
    * Dark mode theme toggle with localStorage persistence[cite: 403].
    * Nickname color customization stored in the database[cite: 404].
    * Dedicated `/settings` page for user customization[cite: 405].
* **Chat:**
    * Real-time chat via Flask-SocketIO, online user list, basic history[cite: 453].
* **Deployment:**
    * Example CI/CD pipeline using GitHub Actions for automated deployment[cite: 453].
    * Containerized application with database migrations applied on startup via entrypoint script[cite: 407, 454].
    * Served over HTTPS via custom domain with Let's Encrypt certificate.
* **Info:** About page (`/about`) displaying build version/ref[cite: 406].

## Technology Stack

* **Backend:** Python, Flask, Flask-SocketIO, Eventlet, Gunicorn, Flask-Login, Flask-SQLAlchemy, Flask-Migrate, WTForms, Werkzeug, **Flask-Mail**
* **Database/Cache:** PostgreSQL, Redis
* **Containerization:** Docker
* **Orchestration:** Kubernetes (GKE Standard)
* **Infrastructure as Code:** Terraform
* **Cloud Provider:** Google Cloud Platform (GCP)
* **CI/CD:** GitHub Actions (Example)
* **Ingress:** Nginx Ingress Controller
* **TLS Certificates:** Cert-Manager + Let's Encrypt
* **Email:** SendGrid (via Flask-Mail)
* **Package Management:** Helm (for Nginx Ingress, Cert-Manager), Pip
* **Version Control:** Git

## Prerequisites

Before you begin, ensure you have the following installed and configured:

1.  **Git:** For cloning the repository.
2.  **Docker & Docker Compose:** For running the application locally. ([Install Docker](https://docs.docker.com/engine/install/))
3.  **Terraform CLI:** For provisioning cloud infrastructure. ([Install Terraform](https://developer.hashicorp.com/terraform/downloads))
4.  **Google Cloud SDK (`gcloud`):** For interacting with GCP and GKE. Needs `gke-gcloud-auth-plugin`. ([Install gcloud](https://cloud.google.com/sdk/docs/install), then run `gcloud components install gke-gcloud-auth-plugin`)
5.  **`kubectl` CLI:** For interacting with the Kubernetes cluster. ([Install kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/))
6.  **Helm CLI:** For installing cluster add-ons (Nginx, Cert-Manager). ([Install Helm](https://helm.sh/docs/intro/install/))
7.  **Google Cloud Platform (GCP) Account:** With an active project and Billing Enabled.
8.  **Docker Hub Account (or other registry):** To store and retrieve the application's Docker image.
9.  **GitHub Account (optional):** If using the example GitHub Actions workflow.
10. **Custom Domain Name:** A domain name you own and can manage DNS for.
11. **SendGrid Account:** API Key generated and sender domain/email verified/authenticated.

## Running Locally

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/Howletcute/chat-app-devops.git](https://github.com/Howletcute/chat-app-devops.git) # Or your fork
    cd chat-app-devops
    ```
2.  **Create Environment File:** Create a `.env` file in the project root and populate required variables (see `config.py`):
    ```dotenv
    # .env (Example for local development)
    SECRET_KEY=a_super_secret_local_key_!@#
    # --- Add SendGrid Vars ---
    SENDGRID_API_KEY='YOUR_SENDGRID_API_KEY_HERE'
    MAIL_DEFAULT_SENDER='your_verified_sender@yourdomain.com' 
    # --- Add DB/Redis overrides if not using localhost defaults ---
    # DB_USER=...
    # DB_PASS=...
    ```
3.  **Build and Run with Docker Compose:**
    ```bash
    docker compose up --build -d
    ```
4.  **Access:** Open your web browser to `http://localhost:5001`.

## Deploying to GCP GKE

This guide outlines deploying the application to a GKE Standard cluster.

**1. Prerequisites Check:**
    * Ensure all items in the [Prerequisites](#prerequisites) section are met.

**2. GCP Setup:**
    * Create a unique Google Cloud Storage (GCS) bucket for Terraform state (ensure **Object Versioning** is enabled):
      ```bash
      # Replace placeholders with your values!
      gcloud storage buckets create gs://<YOUR-UNIQUE-BUCKET-NAME-tfstate> --project=<YOUR-GCP-PROJECT-ID> --location=<GCP_REGION> --uniform-bucket-level-access --versioning
      ```

**3. Terraform Infrastructure Setup:**
    * **Clone Repository:** If not already done.
    * **Configure Backend:** Edit `terraform/backend.tf` and set the `bucket` name to the GCS bucket you just created.
    * **Configure Variables:** Create `terraform/terraform.tfvars` or set environment variables (e.g., `TF_VAR_gcp_project_id`):
      ```hcl
      # terraform/terraform.tfvars (Example)
      gcp_project_id = "<YOUR-GCP-PROJECT-ID>"
      gcp_region     = "<YOUR_GCP_REGION>" # e.g., us-central1
      gcp_zone       = "<YOUR_GCP_ZONE>"   # e.g., us-central1-a
      # Adjust gke_node_machine_type if needed
      ```
    * **Initialize & Apply:** Navigate to the `terraform` directory:
      ```bash
      cd terraform
      terraform init -upgrade
      terraform plan # Review plan
      terraform apply # Confirm with 'yes'
      ```
    * **Configure `kubectl`:** Copy the `kubeconfig_command` value from the `terraform apply` output and run it in your terminal. Verify with `kubectl get nodes`.

**4. Install Cluster Add-ons & Configure DNS:**
    *These steps install prerequisites within the cluster needed for Ingress and TLS.*
    * **Install Nginx Ingress Controller:**
        ```bash
        helm repo add ingress-nginx [https://kubernetes.github.io/ingress-nginx](https://kubernetes.github.io/ingress-nginx)
        helm repo update
        helm install ingress-nginx ingress-nginx/ingress-nginx --namespace default --create-namespace
        ```
    * **Install Cert-Manager:** (Handles Let's Encrypt certificates)
        ```bash
        helm repo add jetstack [https://charts.jetstack.io](https://charts.jetstack.io)
        helm repo update
        helm install cert-manager jetstack/cert-manager \
          --namespace cert-manager \
          --create-namespace \
          --version v1.14.5 \
          --set installCRDs=true \
          --set global.leaderElection.namespace=cert-manager
        ```
    * **Get Nginx Load Balancer IP:** Wait a few minutes for an external IP to be assigned:
        ```bash
        kubectl get service ingress-nginx-controller -n default -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
        ```
        Copy the resulting IP address.
    * **Configure DNS:** Go to your domain registrar or DNS provider. Create an **'A' record** for the hostname you intend to use (e.g., `chat.<your-domain-name>`) pointing to the External IP address obtained above. Allow time for DNS propagation.

**5. Prepare Kubernetes Secrets:**
    * This application requires Kubernetes Secrets for `SECRET_KEY`, PostgreSQL credentials, and the `SENDGRID_API_KEY`.
    * You must create these secrets manually in your GKE cluster *before* deploying the application. Example using `kubectl`:
      ```bash
      # Example for Flask Secret Key
      kubectl create secret generic flask-secret --from-literal=SECRET_KEY='<generate-a-strong-random-secret-key>'

      # Example for PostgreSQL Credentials (adjust name if needed)
      kubectl create secret generic postgres-secret \
        --from-literal=POSTGRES_USER='<your-db-user>' \
        --from-literal=POSTGRES_PASSWORD='<your-db-password>'
        
      # Example for SendGrid API Key
      kubectl create secret generic sendgrid-secret \
        --from-literal=SENDGRID_API_KEY='<your-actual-sendgrid-key>'
      ```
    * **Important:** Ensure the secret names (`flask-secret`, `postgres-secret`, `sendgrid-secret`) and keys (`SECRET_KEY`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `SENDGRID_API_KEY`) match what's referenced in `k8s/web-deployment.yaml`.

**6. Configure and Deploy Application:**
    * **Update Ingress:** Modify `k8s/ingress.yaml`. Set the `host` fields under `spec.rules` and `spec.tls` to your application hostname (e.g., `chat.<your-domain-name>`). Set `spec.tls.secretName` (e.g., `<your-app-hostname>-tls-secret`).
      ```yaml
      # k8s/ingress.yaml (Example Snippet - REPLACE PLACEHOLDERS)
      # ...
      spec:
        tls:
        - hosts:
          - <your-app-hostname> # e.g., chat.your-domain.com
          secretName: <your-tls-secret-name> # Cert-manager will create this
        rules:
        - host: <your-app-hostname> # e.g., chat.your-domain.com
      # ...
      ```
    * **Update Web Deployment:** Modify `k8s/web-deployment.yaml`. Ensure the `image` field points to your image (this should be handled by CI/CD). Verify the `env` section correctly references the Kubernetes secrets created in Step 5 and sets `MAIL_DEFAULT_SENDER` to your verified sender email.
    * **Apply Manifests:** Deploy the application components (ensure secrets are created first):
      ```bash
      kubectl apply -f k8s/postgres-pvc.yaml
      kubectl apply -f k8s/postgres-deployment.yaml
      kubectl apply -f k8s/postgres-service.yaml
      kubectl apply -f k8s/redis-deployment.yaml
      kubectl apply -f k8s/redis-service.yaml
      kubectl apply -f k8s/cluster-issuer.yaml # Ensure email is correct
      kubectl apply -f k8s/ingress.yaml # Apply your updated ingress
      kubectl apply -f k8s/web-deployment.yaml # Deploy the app
      kubectl apply -f k8s/web-service.yaml
      ```

**7. Accessing the Application:**
    * After deployment, allow time for DNS propagation and for cert-manager to issue the TLS certificate (check with `kubectl get certificate`).
    * Access the application via HTTPS at your configured hostname (e.g., `https://<your-app-hostname>`).

**8. CI/CD (Optional - GitHub Actions Example):**
    * The `.github/workflows/deploy.yml` provides an example pipeline.
    * **Setup:** Create a GCP Service Account, download its key, and add required secrets (`DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, `GCP_SA_KEY`, `GCP_PROJECT_ID`, `GCP_ZONE`, `GKE_CLUSTER_NAME`) to your GitHub repository Actions secrets.
    * **Functionality:** Builds image, tags with commit SHA, pushes, authenticates to GKE, updates image tag in `web-deployment.yaml` using `sed` (consider Kustomize/Helm later), applies `k8s` manifests. Adapt as needed.

## Project Structure

```text
.
├── .github/workflows/      # Example GitHub Actions CI/CD pipeline
│   └── deploy.yml
├── app/                    # Flask application package
│   └── ... (see detailed structure above)
├── k8s/                    # Kubernetes Manifests
│   └── ...
├── migrations/             # Alembic database migrations
│   └── ...
├── static/                 # Static assets (CSS, JS)
│   └── ...
├── templates/              # Jinja2 HTML templates
│   └── ...
├── terraform/              # Terraform infrastructure code (GKE Cluster/Nodes)
│   └── ...
├── .env                    # Local environment variables (Gitignored)
├── .gitignore
├── CHANGELOG.md
├── config.py               # Flask configuration classes
├── docker-compose.yml      # Docker Compose for local development
├── Dockerfile              # Docker build instructions for chat app
├── entrypoint.sh           # Container entrypoint (runs migrations)
├── README.md               # This file
├── requirements.txt        # Python dependencies
└── run.py                  # Script to run the Flask development server w/ SocketIO