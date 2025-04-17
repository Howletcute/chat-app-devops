# terraform/variables.tf

variable "gcp_project_id" {
  description = "Your GCP Project ID (howlet-chat-app)"
  type        = string
  # No default - value should come from terraform.tfvars
}

variable "gcp_region" {
  description = "GCP region for resources (e.g., us-central1)"
  type        = string
  default     = "us-central1" # Free tier eligible region
}

variable "gcp_zone" {
  description = "GCP zone within the region (e.g., us-central1-a)"
  type        = string
  default     = "us-central1-a" # Zone within the region
}

# Note: ssh_source_ip is still needed if you want firewall rules created by TF,
# but we removed the VM firewall rules. Keep it if you might add GKE firewall rules later via TF.
variable "ssh_source_ip" {
  description = "Your public IP address for potential SSH access rules (use CIDR notation, e.g., 'YOUR_IP/32')"
  type        = string
  # No default - value should come from terraform.tfvars
}

variable "gke_cluster_name" {
  description = "Name for the GKE cluster"
  type        = string
  default     = "chat-app-std-cluster" # Renamed slightly for clarity
}

variable "gke_node_machine_type" {
  description = "Machine type for GKE Standard node pool"
  type        = string
  default     = "e2-medium" # Use free-trial covered type
}

variable "gke_node_disk_size_gb" {
  description = "Disk size in GB for GKE nodes"
  type        = number
  default     = 30
}

variable "gke_node_disk_type" {
  description = "Disk type for GKE nodes"
  type        = string
  default     = "pd-standard"
}