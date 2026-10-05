variable "name" {
  description = "Resource name prefix (e.g. signalroom-dev)"
  type        = string
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.20.0.0/16"
}

variable "container_port" {
  description = "Port the API container listens on"
  type        = number
  default     = 8000
}
