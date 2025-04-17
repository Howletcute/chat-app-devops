# terraform/backend.tf

terraform {
  backend "gcs" {
    bucket = "howlet-chat-app-tfstate-gke-std" # <-- Put the EXACT name of the bucket you just created
    prefix = "terraform/state/gke-standard"    # State file path within the bucket
  }
}