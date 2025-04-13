# terraform/backend.tf

# Configure the GCS backend for remote state storage
terraform {
  backend "gcs" {
    bucket = "howlets-todo-devops" # Replace with the exact name of the bucket you created
    prefix = "terraform/state/todo-app" # Path within the bucket to store the state file
  }
}