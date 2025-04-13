# terraform/outputs.tf

output "instance_public_ip" {
  description = "Public IP address of the Compute Engine instance"
  # Access the specific attribute from the google_compute_instance resource defined in main.tf
  value       = google_compute_instance.vm_instance.network_interface[0].access_config[0].nat_ip
}