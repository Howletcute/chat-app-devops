# terraform/gke.tf

# Data source for default network (used by cluster)
data "google_compute_network" "default" {
  name = "default"
}

# GKE Cluster Resource (Standard, Zonal)
resource "google_container_cluster" "primary" {
  name     = var.gke_cluster_name
  location = var.gcp_zone # Create a Zonal cluster

  # We define our own node pool, so remove the default one GKE creates
  remove_default_node_pool = true
  initial_node_count       = 1 # Required by TF when removing default pool

  network    = data.google_compute_network.default.id
  subnetwork = null # Use default subnet in the zone

  # Explicitly disable cluster autoscaling
  cluster_autoscaling {
    enabled = false
    # No resource_limits needed when disabled
  }

  # Standard logging/monitoring services
  logging_service    = "logging.googleapis.com/kubernetes"
  monitoring_service = "monitoring.googleapis.com/kubernetes"

  # Allow deletion via Terraform
  deletion_protection = false
}

# GKE Node Pool Resource (Single e2-medium Node)
resource "google_container_node_pool" "primary_nodes" {
  name       = "${var.gke_cluster_name}-node-pool" # Simplified pool name
  cluster    = google_container_cluster.primary.id
  location   = var.gcp_zone # Place nodes in the same zone as the control plane
  node_count = 1            # Start with exactly one node

  # Disable node pool autoscaling (enforce single node)
  autoscaling {
    min_node_count = 1
    max_node_count = 1
  }

  # Configure node management options
  management {
    auto_repair  = true
    auto_upgrade = true
  }

  # Define the node configuration
  node_config {
    machine_type = var.gke_node_machine_type # e.g., "e2-medium"
    disk_size_gb = var.gke_node_disk_size_gb # e.g., 30
    disk_type    = var.gke_node_disk_type    # e.g., "pd-standard"
    preemptible  = false                     # Must be non-preemptible

    # Required OAuth scopes for GKE nodes
    oauth_scopes = [
      "https://www.googleapis.com/auth/compute",
      "https://www.googleapis.com/auth/devstorage.read_only",
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring",
    ]
  }

  # Ensure this node pool is created only after the cluster exists
  depends_on = [google_container_cluster.primary]
}