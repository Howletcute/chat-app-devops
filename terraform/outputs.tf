# terraform/outputs.tf

output "gke_cluster_name" {
  description = "GKE cluster name"
  value       = google_container_cluster.primary.name
}

output "gke_cluster_endpoint" {
  description = "GKE cluster endpoint (IP address)"
  value       = google_container_cluster.primary.endpoint
  sensitive   = true
}

# Output command to configure kubectl
output "kubeconfig_command" {
  description = "Command to configure kubectl for this cluster"
  value       = "gcloud container clusters get-credentials ${google_container_cluster.primary.name} --zone ${var.gcp_zone} --project ${var.gcp_project_id}"
  # Changed --region to --zone to match zonal cluster creation
}