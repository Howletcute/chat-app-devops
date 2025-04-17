# terraform/gke.tf

# Data source to get information about the default VPC network
data "google_compute_network" "default" {
  name = "default"
  # project = var.gcp_project_id # Uncomment if your network is not in the provider's project
}

# --- GKE Cluster (Standard ZONAL) ---
resource "google_container_cluster" "primary" {
  # Required name for the cluster, uses variable defined in variables.tf
  name     = var.gke_cluster_name
  # Location sets this as a Zonal cluster (control plane in this zone)
  location = var.gcp_zone

  # We define our own node pool immediately, so remove the default one
  remove_default_node_pool = true
  initial_node_count       = 1 # Required by TF when removing the default pool

  # Networking configuration using the default VPC
  network    = data.google_compute_network.default.id
  subnetwork = null # Use the default subnetwork in the specified zone

  # Explicitly define IP allocation policy
  ip_allocation_policy {
    # Request a specific private range for Kubernetes Services (ClusterIPs)
    # This range should not overlap with your VPC subnets.
    # "10.100.0.0/20" is just an example, GKE might adjust slightly if needed.
    services_ipv4_cidr_block = "10.100.0.0/20"

    # We can let GKE choose the Pod IP range automatically by omitting
    # cluster_ipv4_cidr_block = "..."
  }

  # Enable standard logging and monitoring services
  logging_service    = "logging.googleapis.com/kubernetes"
  monitoring_service = "monitoring.googleapis.com/kubernetes"

  # Disable deletion protection for easy cleanup during testing
  deletion_protection = false

  # Explicitly disable cluster-level autoscaling features like Node Autoprovisioning
  # The 'cluster_autoscaling' block itself is removed as it caused API errors when 'enabled = false'
  # Node pool specific scaling is handled in the node pool resource below.
}

# --- GKE Node Pool (Single e2-medium, Autoscaling Enabled) ---
resource "google_container_node_pool" "primary_nodes" {
  # Name for the node pool
  name       = "${var.gke_cluster_name}-std-pool"
  # Link to the cluster defined above
  cluster    = google_container_cluster.primary.id
  # Ensure nodes are created in the same zone as the cluster control plane
  location   = var.gcp_zone

  # Configure node pool autoscaling
  autoscaling {
    min_node_count = 1 # Minimum number of nodes
    max_node_count = 3 # Maximum number of nodes GKE can scale up to
  }

  # Node pool management settings
  management {
    auto_repair  = true # Enable automatic node repairs
    auto_upgrade = true # Enable automatic node upgrades (recommended)
  }

  # Configuration for the nodes in this pool
  node_config {
    # Machine type - Using e2-medium (covered by free trial credit)
    machine_type = var.gke_node_machine_type # Defaults to "e2-medium" in variables.tf

    # Disk settings - Keeping size within general free tier ideas
    disk_size_gb = var.gke_node_disk_size_gb # Defaults to 30
    disk_type    = var.gke_node_disk_type    # Defaults to "pd-standard"

    # Must be false for standard node pools generally
    preemptible  = false

    # Standard OAuth scopes required for nodes to interact with GCP APIs
    oauth_scopes = [
      "https://www.googleapis.com/auth/compute",
      "https://www.googleapis.com/auth/devstorage.read_only",
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring",
    ]
  }

  # Ensure this depends on the cluster being created first (usually implicit)
  depends_on = [google_container_cluster.primary]
}