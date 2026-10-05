provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = "SignalRoom"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Purpose     = "MIAX academic MVP"
    }
  }
}
