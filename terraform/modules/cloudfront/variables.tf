variable "name" {
  type = string
}

variable "frontend_bucket_id" {
  type = string
}

variable "frontend_bucket_arn" {
  type = string
}

variable "frontend_bucket_regional_domain_name" {
  type = string
}

variable "alb_dns_name" {
  type = string
}

variable "origin_verify_secret" {
  type      = string
  sensitive = true
}

variable "price_class" {
  description = "PriceClass_100 = North America + Europe edges only (cheapest)"
  type        = string
  default     = "PriceClass_100"
}

variable "basic_auth_user" {
  description = "Username for the optional site-wide password"
  type        = string
  default     = "signalroom"
}

variable "basic_auth_password" {
  description = "Optional site-wide password (HTTP Basic Auth on the web app). Empty = disabled."
  type        = string
  default     = ""
  sensitive   = true
}
