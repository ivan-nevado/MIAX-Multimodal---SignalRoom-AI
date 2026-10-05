variable "name" {
  type = string
}

variable "suffix" {
  description = "Random suffix: bucket names are globally unique"
  type        = string
}

variable "force_destroy" {
  type    = bool
  default = true
}

variable "upload_retention_days" {
  type    = number
  default = 90
}
