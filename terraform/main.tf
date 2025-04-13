# main.tf

# Configure the Google Cloud provider
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0" # Use a recent version
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
  zone    = var.gcp_zone
}

# Use the default VPC network for simplicity
data "google_compute_network" "default" {
  name = "default"
}

# Firewall rule to allow incoming HTTP traffic on port 5001
resource "google_compute_firewall" "allow_http_5001" {
  name    = "${var.instance_name}-allow-http-5001"
  network = data.google_compute_network.default.name
  # Allow traffic from any source (0.0.0.0/0) for the web app
  source_ranges = ["0.0.0.0/0"]
  allow {
    protocol = "tcp"
    ports    = ["5001"] # The host port we mapped in docker-compose
  }
  # Apply this rule to instances tagged with "http-server" (we'll add this tag to our VM)
  target_tags = ["http-server"]
}

# Firewall rule to allow incoming SSH traffic only from your specified IP
resource "google_compute_firewall" "allow_ssh" {
  name    = "${var.instance_name}-allow-ssh"
  network = data.google_compute_network.default.name
  # IMPORTANT: Use your specific IP from the variable for security
  source_ranges = [var.ssh_source_ip]
  allow {
    protocol = "tcp"
    ports    = ["22"] # Standard SSH port
  }
  # Apply this rule to instances tagged with "ssh-server" (we'll add this tag to our VM)
  target_tags = ["ssh-server"]
}

# Define the Compute Engine instance (VM)
resource "google_compute_instance" "vm_instance" {
  name         = var.instance_name
  machine_type = var.machine_type # e.g., "e2-micro"
  zone         = var.gcp_zone

  # Use a standard Debian image
  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11" # Using Debian 11
      size = 30 # GB (within Always Free limit)
    }
  }

  # Connect the instance to the default network
  network_interface {
    network = data.google_compute_network.default.name
    # Add an access config to assign a public IP address
    access_config {
    }
  }

  # Add tags to apply firewall rules
  tags = ["http-server", "ssh-server"]

  # Metadata startup script (optional but useful for installing Docker later - we'll use Ansible though)
  # metadata_startup_script = <<-EOF
  # #!/bin/bash
  # echo "VM Started" > /tmp/startup_log.txt
  # EOF

  # Allow Terraform to delete this instance even if the disk isn't auto-deleted
  allow_stopping_for_update = true
}

# Output the public IP address of the VM
output "instance_public_ip" {
  description = "Public IP address of the VM instance"
  value       = google_compute_instance.vm_instance.network_interface[0].access_config[0].nat_ip
}