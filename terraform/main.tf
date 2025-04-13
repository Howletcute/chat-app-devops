# terraform/main.tf

# --- Network Data Source ---
# Get information about the default VPC network already present in the project
data "google_compute_network" "default" {
  name = "default"
}

# --- Firewall Rules ---
# Firewall rule to allow incoming HTTP traffic on port 5001 from anywhere
resource "google_compute_firewall" "allow_http_5001" {
  name          = "${var.instance_name}-allow-http-5001"
  network       = data.google_compute_network.default.name
  source_ranges = ["0.0.0.0/0"] # Allow traffic from any source

  allow {
    protocol = "tcp"
    ports    = ["5001"] # The host port mapped in docker-compose
  }

  # Apply this rule only to instances tagged with "http-server"
  target_tags = ["http-server"]
  description = "Allow incoming traffic on TCP port 5001"
}

# Firewall rule to allow incoming SSH traffic only from your specified IP
resource "google_compute_firewall" "allow_ssh" {
  name          = "${var.instance_name}-allow-ssh"
  network       = data.google_compute_network.default.name
  source_ranges = [var.ssh_source_ip] # Use your specific IP from the variable for security

  allow {
    protocol = "tcp"
    ports    = ["22"] # Standard SSH port
  }

  # Apply this rule only to instances tagged with "ssh-server"
  target_tags = ["ssh-server"]
  description = "Allow incoming SSH traffic from specified IP range"
}

# --- Compute Instance ---
# Define the Compute Engine instance (VM)
resource "google_compute_instance" "vm_instance" {
  name         = var.instance_name
  machine_type = var.machine_type # e.g., "e2-micro" from variables
  zone         = var.gcp_zone     # Zone from variables

  # Define the boot disk using a standard Debian 11 image
  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
      size  = 30 # GB (within Always Free limit)
    }
  }

  # Configure the network interface to use the default network and get a public IP
  network_interface {
    network = data.google_compute_network.default.name
    # Add an empty access_config block to request an ephemeral public IP address
    access_config {
    }
  }

  # Assign tags to the instance so the firewall rules apply correctly
  tags = ["http-server", "ssh-server"]

  # Add labels for organization, billing, etc. (Good practice)
  labels = {
    environment = "dev"     # Example: Could be "prod", "staging"
    project     = "todo-app"
    managed-by  = "terraform"
  }

  # Allow the instance to be stopped/updated by Terraform if needed
  allow_stopping_for_update = true
}