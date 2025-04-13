# variables.tf

variable "gcp_project_id" {
  description = "todo-devops-456703"
  type        = string
  # Make sure this project exists in your GCP account
}

variable "gcp_region" {
  description = "GCP region to deploy resources in (e.g., us-central1)"
  type        = string
  default     = "us-central1" # Choose an Always Free eligible region
}

variable "gcp_zone" {
  description = "GCP zone within the region (e.g., us-central1-a)"
  type        = string
  default     = "us-central1-a" # Choose a zone within your selected region
}

variable "instance_name" {
  description = "Name for the Compute Engine instance"
  type        = string
  default     = "todo-app-vm"
}

variable "machine_type" {
  description = "Machine type for the VM"
  type        = string
  default     = "e2-micro" # Always Free eligible machine type
}

variable "ssh_source_ip" {
  description = "Your public IP address to allow SSH access from (use CIDR notation, e.g., 'YOUR_IP/32'). Find yours at https://whatismyipaddress.com/"
  type        = string
  # IMPORTANT: Replace this default with your actual IP address range for security!
  # Leaving it as 0.0.0.0/0 is insecure and allows SSH from anywhere.
  default     = "176.100.29.205/32" # <-- CHANGE THIS!
}