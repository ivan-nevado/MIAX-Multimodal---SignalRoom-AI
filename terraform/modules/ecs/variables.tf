variable "name" {
  type = string
}

variable "region" {
  type = string
}

variable "app_env" {
  type    = string
  default = "dev"
}

variable "image_repository_url" {
  type = string
}

variable "image_tag" {
  type    = string
  default = "latest"
}

variable "container_port" {
  type    = number
  default = 8000
}

variable "subnet_ids" {
  type = list(string)
}

variable "security_group_id" {
  type = string
}

variable "target_group_arn" {
  type = string
}

variable "execution_role_arn" {
  type = string
}

variable "task_role_arn" {
  type = string
}

variable "dynamodb_table_prefix" {
  type = string
}

variable "uploads_bucket" {
  type = string
}

variable "investigation_queue_url" {
  type = string
}

variable "briefing_queue_url" {
  type = string
}

variable "secret_arn" {
  type = string
}

variable "cognito_user_pool_id" {
  type = string
}

variable "cognito_client_id" {
  type = string
}

variable "ses_from_email" {
  type    = string
  default = ""
}

variable "public_url" {
  description = "https://<distribution>.cloudfront.net — used for CORS, email links and presigned local URLs"
  type        = string
}

variable "extra_environment" {
  description = "Additional non-secret environment variables (e.g. model overrides)"
  type        = map(string)
  default     = {}
}

variable "api_cpu" {
  type    = number
  default = 512
}

variable "api_memory" {
  type    = number
  default = 1024
}

variable "worker_cpu" {
  type    = number
  default = 1024
}

variable "worker_memory" {
  type    = number
  default = 2048
}

variable "api_desired_count" {
  type    = number
  default = 1
}

variable "worker_desired_count" {
  type    = number
  default = 1
}

variable "worker_use_spot" {
  type    = bool
  default = true
}

variable "log_retention_days" {
  type    = number
  default = 14
}

variable "allowed_emails" {
  description = "Invite list, also enforced by the API (defence in depth)"
  type        = list(string)
  default     = []
}

variable "max_investigations_per_day" {
  type    = number
  default = 20
}

variable "max_briefings_per_day" {
  type    = number
  default = 5
}
