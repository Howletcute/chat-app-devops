# Real-Time Chat Application (v1.1.0 - GKE Deployment)

## Description

This project implements a simple, anonymous real-time chat application using Flask-SocketIO and Redis. Users can choose a nickname, enter a common chat room, send messages, and see who else is online.

Version 1.1.0 represents the migration of the deployment from a single VM to **Google Kubernetes Engine (GKE)**. It runs on a **GKE Standard Zonal cluster** (starting with an `e2-medium` node pool with autoscaling) provisioned via Terraform. Ingress is handled by **Nginx Ingress Controller**, and TLS/HTTPS is automated using **cert-manager** with Let's Encrypt certificates. Deployment is automated via **GitHub Actions**.

**Note on Cost:** This configuration requires a GCP account with the **$300 Free Trial credit** activated to run without incurring costs during the trial period, as the `e2-medium` node(s) and GCP Load Balancer provisioned by Nginx Ingress exceed the limits of the basic Always Free tier.

## Features (v1.1.0)

* Anonymous login using a chosen nickname (duplicates allowed).
* Single, common chat room for all connected users.
* Real-time message broadcasting using WebSockets (Flask-SocketIO).
* Display list of currently online users (updates on join/leave).
* Basic message history loaded on joining.
* Deployment automated via CI/CD (GitHub Actions).
* Served over HTTPS with a valid certificate.

## Technology Stack

* **Backend:** Python, Flask, Flask-SocketIO, Eventlet, Gunicorn
* **Database/Cache:** Redis
* **Containerization:** Docker
* **Orchestration:** Kubernetes (GKE Standard)
* **Infrastructure as Code:** Terraform
* **Cloud Provider:** Google Cloud Platform (GCP)
* **CI/CD:** GitHub Actions
* **Ingress:** Nginx Ingress Controller
* **TLS Certificates:** Cert-Manager + Let's Encrypt
* **Package Management:** Helm (for Nginx Ingress, Cert-Manager)
* **Version Control:** Git

## Prerequisites

Before you begin, ensure you have the following installed and configured:

1.  **Git:** For cloning the repository.
2.  **Docker & Docker Compose:** For running the application locally. ([Install Docker](https://docs.docker.com/engine/install/))
3.  **Terraform CLI:** For provisioning cloud infrastructure. ([Install Terraform](https://developer.hashicorp.com/terraform/downloads))
4.  **Google Cloud SDK (`gcloud`):** For interacting with GCP and GKE. Needs `gke-gcloud-auth-plugin`. ([Install gcloud](https://cloud.google.com/sdk/docs/install), then run `gcloud components install gke-gcloud-auth-plugin`)
5.  **`kubectl` CLI:** For interacting with the Kubernetes cluster. ([Install kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/))
6.  **Helm CLI:** For installing cluster add-ons (Nginx, Cert-Manager). ([Install Helm](https://helm.sh/docs/intro/install/))
7.  **Google Cloud Platform (GCP) Account:** With an active project, **Billing Enabled**, and ideally the **$300 Free Trial activated** to cover resource costs.
8.  **Docker Hub Account:** To store and retrieve the application's Docker image.
9.  **GitHub Account:** To host the repository and use GitHub Actions.
10. **DuckDNS Account & Subdomain:** A free subdomain (e.g., `your-name.duckdns.org`) registered at [DuckDNS](https://www.duckdns.org/).

## Running Locally

1.  **Clone the repository:**
    ```bash
    # Replace with the actual HTTPS or SSH URL of your repository
    git clone [https://github.com/Howletcute/chat-app-devops.git](https://github.com/Howletcute/chat-app-devops.git)
    cd chat-app-devops
    ```
2.  **Create Environment File:** Create a `.env` file in the project root:
    ```dotenv
    # .env
    SECRET_KEY=a_local_secret_dev_key_!@#
    ```
3.  **Build and Run with Docker Compose:**
    ```bash
    docker compose up --build -d
    ```
4.  **Access:** Open your web browser to `http://localhost:5001`.

## Deploying to GCP (GKE Standard with Free Trial)

This deploys the application to a GKE Standard Zonal cluster using resources covered by the GCP Free Trial credit.

**1. Prerequisites Check:**

* Ensure all items in the [Prerequisites](#prerequisites) section are met, especially the GCP account with Free Trial active and Billing enabled.

**2. GCP Setup:**

* Create a unique Google Cloud Storage (GCS) bucket for Terraform state (ensure **Object Versioning** is enabled):
    ```bash
    # Replace placeholders!
    gcloud storage buckets create gs://<YOUR-UNIQUE-BUCKET-NAME-gke> --project=<YOUR-GCP-PROJECT-ID> --location=<GCP_REGION e.g., us-central1> --uniform-bucket-level-access --versioning
    ```

**3. Terraform Infrastructure Setup:**

* **Clone Repository:** If not already done.
* **Configure Backend:** Edit `terraform/backend.tf` and set the `bucket` name to the GCS bucket you created.
* **Configure Variables:** Create `terraform/terraform.tfvars` with your GCP Project ID and your current public IP (for potential firewall rules, though less critical now):
    ```hcl
    # terraform/terraform.tfvars
    gcp_project_id = "<YOUR-GCP-PROJECT-ID>" # e.g., howlet-chat-app
    ssh_source_ip  = "<YOUR_PUBLIC_IP>/32"
    ```
    *(Note: Set the `gcp_region` and `gcp_zone` defaults in `variables.tf` if different from `us-central1`/`us-central1-a`. Set `gke_node_machine_type` to `e2-medium`)*
* **Initialize & Apply:** Navigate to the `terraform` directory:
    ```bash
    cd terraform
    terraform init -upgrade
    terraform plan # Review plan: should create GKE Standard Cluster + Node Pool
    terraform apply # Confirm with 'yes'. Takes several minutes.
    ```
* **Configure `kubectl`:** Copy the `kubeconfig_command` value from the `terraform apply` output and run it in your terminal. Verify with `kubectl get nodes`.

**4. Install Cluster Add-ons (Manual Helm Steps for v1.1.0):**

*These steps install prerequisites required *before* the application deployment pipeline can succeed.*
    * **Install Nginx Ingress:**
        ```bash
        helm repo add ingress-nginx [https://kubernetes.github.io/ingress-nginx](https://kubernetes.github.io/ingress-nginx)
        helm repo update
        helm install ingress-nginx ingress-nginx/ingress-nginx --namespace default --create-namespace
        ```
    * **Install Cert-Manager:** (Using the specific fix for GKE)
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
    * **Get Nginx External IP:** Wait a few minutes, then get the IP:
        ```bash
        kubectl get service ingress-nginx-controller -n default
        ```
    * **Update DNS:** Go to DuckDNS and update the IP address for your subdomain (`howlet-chat.duckdns.org`) to point to the External IP obtained above.

**5. GitHub Actions Setup (Secrets):**

* This needs to be done on the GitHub repository where the Actions workflow will run.
* **Create GCP Service Account & Key:** Create a Service Account (e.g., `github-actions-gke-deployer`), grant it `Kubernetes Engine Developer` and `Service Account User` roles, and create/download a JSON key.
* **Add GitHub Secrets:** In repository Settings > Secrets and variables > Actions, add:
    * `DOCKERHUB_USERNAME`: Your Docker Hub username.
    * `DOCKERHUB_TOKEN`: Your Docker Hub access token.
    * `GCP_SA_KEY`: The entire JSON content of the GCP Service Account key file.
    * `GCP_PROJECT_ID`: Your GCP Project ID (e.g., `howlet-chat-app`).
    * `GCP_ZONE`: The GCP zone used for the cluster (e.g., `us-central1-a`).
    * `GKE_CLUSTER_NAME`: The name of your GKE cluster (e.g., `chat-app-std-cluster`).

**6. Deployment Trigger:**

* Pushing changes to the `main` branch triggers the GitHub Actions workflow defined in `.github/workflows/deploy.yml`.
* The pipeline builds the `howletcute/chat-app:latest` image, pushes it, authenticates to GKE, and deploys the application using `kubectl apply -f k8s/`.

**7. Accessing the Application:**

* After the pipeline runs successfully, allow a minute or two for the Let's Encrypt certificate to be issued by cert-manager.
* Access the application via HTTPS: `https://howlet-chat.duckdns.org` (replace with your actual domain).

## Project Structure (v1.1.0)

```text
.
├── .github/workflows/      # GitHub Actions CI/CD pipeline for GKE
│   └── deploy.yml
├── ansible/                # Ansible (Not used for GKE deployment in v1.1)
│   ├── configure-vm.yml
│   ├── deploy-app.yml
│   └── inventory.ini
├── k8s/                    # Kubernetes Manifests
│   ├── cluster-issuer.yaml
│   ├── ingress.yaml
│   ├── redis-deployment.yaml
│   ├── redis-service.yaml
│   ├── web-deployment.yaml
│   └── web-service.yaml
├── templates/              # Flask HTML templates
│   ├── chat.html
│   └── index.html
├── terraform/              # Terraform infrastructure code (GKE Cluster/Nodes)
│   ├── backend.tf
│   ├── gke.tf              # Contains GKE cluster and node pool definitions
│   ├── main.tf             # Currently empty or holds non-GKE resources
│   ├── outputs.tf
│   ├── providers.tf
│   └── variables.tf
├── .env                    # Local environment variables (Gitignored)
├── .gitignore
├── app.py                  # Flask-SocketIO chat application code
├── Dockerfile              # Docker build instructions for chat app
├── docker-compose.yml      # Docker Compose for local development
├── README.md               # This file
└── requirements.txt        # Python dependencies


Future Improvements
Automate Helm installs via Terraform or GitOps.
Implement user authentication.
Add more chat features (private messages, rooms).
Set up monitoring and logging (Prometheus/Grafana/Cloud Monitoring).
Use managed Redis (Memorystore) instead of container.
Add automated tests to CI/CD pipeline.
Implement more robust secret management (Vault, GCP Secret Manager).