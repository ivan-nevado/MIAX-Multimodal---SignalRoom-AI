variable "name" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "security_group_id" {
  type = string
}

variable "container_port" {
  type    = number
  default = 8000
}

variable "origin_verify_secret" {
  description = "Shared secret header value CloudFront sends to the ALB"
  type        = string
  sensitive   = true
}
