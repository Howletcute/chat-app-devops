# Real-Time Chat Application (GKE Deployment Template)

## Description

This project provides a template for deploying a real-time chat application using Flask-SocketIO, Redis, and PostgreSQL onto Google Kubernetes Engine (GKE).
It includes user authentication, basic chat features, and customization options.
Infrastructure is provisioned via Terraform, deployment can be automated via GitHub Actions, and TLS/HTTPS is handled by cert-manager and Nginx Ingress. This guide assumes deployment to a custom domain.

**Note on Cost:** The default Terraform configuration uses resources (like `e2-medium` nodes) that may require a GCP account with active billing and potentially the Free Trial credit to run without incurring significant costs. Adjust Terraform variables (e.g., `gke_node_machine_type`) based on your budget and needs.

## Features (Based on v1.2.0)

* User registration and login functionality using PostgreSQL.
* Password hashing using Werkzeug.
* Session management using Flask-Login.
* Database migrations using Flask-Migrate.
* Dark mode theme toggle with localStorage persistence.
* Nickname color customization stored in the database.
* Dedicated `/settings` page for user customization.
* About page (`/about`) displaying build version/ref.
* Real-time chat via Flask-SocketIO, online user list, basic history.
* Example CI/CD pipeline using GitHub Actions for automated deployment.
* Containerized application with database migrations applied on startup via entrypoint script.

## Technology Stack

* **Backend:** Python, Flask, Flask-SocketIO, Eventlet, Gunicorn, Flask-Login, Flask-SQLAlchemy, Flask-Migrate, WTForms, Werkzeug
* **Database/Cache:** PostgreSQL, Redis
* **Containerization:** Docker
* **Orchestration:** Kubernetes (GKE Standard)
* **Infrastructure as Code:** Terraform
* **Cloud Provider:** Google Cloud Platform (GCP)
* **CI/CD:** GitHub Actions (Example)
* **Ingress:** Nginx Ingress Controller
* **TLS Certificates:** Cert-Manager + Let's Encrypt
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

## Running Locally

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/Howletcute/chat-app-devops.git](https://github.com/Howletcute/chat-app-devops.git) # Or your fork
    cd chat-app-devops
    ```
2.  **Create Environment File:** Create a `.env` file in the project root (see `config.py` for variables like `SECRET_KEY`, `SENDGRID_API_KEY`, DB/Redis details if not using defaults):
    ```dotenv
    # .env (Example for local development)
    SECRET_KEY=a_super_secret_local_key_!@#
    # Add other overrides if needed (e.g., SENDGRID_API_KEY)
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
    * **Configure DNS:** Go to your domain registrar or DNS provider where your custom domain (`<your-domain-name>`) is managed. Create an **'A' record** for the hostname you intend to use for the application (e.g., `chat` for `chat.<your-domain-name>` or `@` for the root `<your-domain-name>`) and point it to the External IP address you obtained above. Allow time for DNS changes to propagate.

**5. Prepare Kubernetes Secrets:**

* This application requires Kubernetes Secrets for sensitive configuration like the Flask `SECRET_KEY`, PostgreSQL credentials, and potentially third-party API keys (e.g., SendGrid).
* You must create these secrets manually in your GKE cluster *before* deploying the application. Example using `kubectl`:
    ```bash
    # Example for Flask Secret Key
    kubectl create secret generic <your-flask-secret-name> --from-literal=SECRET_KEY='<generate-a-strong-random-secret-key>'

    # Example for PostgreSQL Credentials
    kubectl create secret generic <your-postgres-secret-name> \
      --from-literal=POSTGRES_USER='<your-db-user>' \
      --from-literal=POSTGRES_PASSWORD='<your-db-password>'

    # Example for SendGrid API Key (if using email features)
    # kubectl create secret generic <your-sendgrid-secret-name> --from-literal=SENDGRID_API_KEY='<your-actual-sendgrid-key>'
    ```
* **Important:** Ensure the secret names and keys match what's referenced in the `k8s/web-deployment.yaml` and `k8s/postgres-deployment.yaml` files (or update the YAMLs to reference the secret names you create).

**6. Configure and Deploy Application:**

* **Update Ingress:** Modify `k8s/ingress.yaml`. Set the `host` fields under `spec.rules` and `spec.tls` to your desired application hostname (e.g., `chat.<your-domain-name>`). Set `spec.tls.secretName` to a name for cert-manager to store the certificate (e.g., `<your-app-hostname>-tls-secret`).
    ```yaml
    # k8s/ingress.yaml (Example Snippet - REPLACE PLACEHOLDERS)
    # ...
    spec:
      tls:
      - hosts:
        - <your-app-hostname> # e.g., chat.your-domain.com
        secretName: <your-tls-secret-name> # Use a descriptive name; cert-manager will create it
      rules:
      - host: <your-app-hostname> # e.g., chat.your-domain.com
    # ...
    ```
* **Update Image Name (If necessary):** Ensure the `image` field in `k8s/web-deployment.yaml` points to your built image in your container registry (e.g., `your-dockerhub-username/chat-app:<tag>`).
* **Apply Manifests:** Deploy the application components:
    ```bash
    # Apply secrets first if not already done
    kubectl apply -f k8s/postgres-pvc.yaml
    # kubectl apply -f <your-secret-manifests.yaml> # Or apply secrets created above
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
* **Setup:**
    * Create a GCP Service Account with appropriate roles (`Kubernetes Engine Developer`, `Service Account User`). Download its JSON key.
    * Add required secrets to your GitHub repository's Actions secrets (see workflow file for names like `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, `GCP_SA_KEY`, `GCP_PROJECT_ID`, `GCP_ZONE`, `GKE_CLUSTER_NAME`, etc.).
* **Functionality:** The example pipeline builds the Docker image, tags it with the commit SHA, pushes it to Docker Hub, authenticates to GKE, updates the image tag in `k8s/web-deployment.yaml` (using `sed` - **consider alternatives like Kustomize or Helm for better practice**), and applies the `k8s` manifests. Adapt this pipeline to your needs.

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

Future Improvements
Implement Email Confirmation & Forgot Password features.
Enhance Security (Network Policies, Vulnerability Scanning, GCP Secret Manager).
Implement Structured Logging & Monitoring (Cloud Logging/Monitoring, Prometheus/Grafana).
Refine CI/CD (Testing stages, Helm/Kustomize for manifests, Staging environment).
Use managed Database/Redis services (Cloud SQL, Memorystore) instead of containers.
Improve Kubernetes Secret Management (e.g., Vault, ExternalSecrets operator).