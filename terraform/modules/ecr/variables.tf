variable "name" {
  type = string
}

variable "force_delete" {
  description = "Allow terraform destroy to delete a repository that still contains images (dev only)"
  type        = bool
  default     = true
}
