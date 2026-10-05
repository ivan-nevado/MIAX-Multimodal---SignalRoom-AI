variable "region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-1"
}

variable "project" {
  type    = string
  default = "signalroom"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "image_tag" {
  description = "Backend image tag pushed to ECR by scripts/deploy.sh"
  type        = string
  default     = "latest"
}

variable "ses_from_email" {
  description = "Verified sender for briefing emails (leave empty to disable email)"
  type        = string
  default     = ""
}

variable "ses_sandbox_recipients" {
  description = "Recipients to verify while SES is in sandbox mode"
  type        = list(string)
  default     = []
}

variable "briefing_schedule_enabled" {
  type    = bool
  default = true
}

variable "worker_use_spot" {
  type    = bool
  default = true
}

variable "api_desired_count" {
  description = "Set to 0 to pause the API (and save credits) without destroying anything"
  type        = number
  default     = 1
}

variable "worker_desired_count" {
  type    = number
  default = 1
}

variable "model_overrides" {
  description = "Optional non-secret env overrides, e.g. { OPENAI_MODEL = \"openai/gpt-6-luna\" }"
  type        = map(string)
  default     = {}
}

# ------------------------------------------------------------------ budget protection
variable "allowed_emails" {
  description = "Invite-only access: emails and/or @domain entries allowed to sign up and use the API. Empty = anyone."
  type        = list(string)
  default     = []
}

variable "site_password" {
  description = "Optional password for the whole web app (HTTP Basic Auth in CloudFront). Empty = disabled."
  type        = string
  default     = ""
  sensitive   = true
}

variable "site_username" {
  type    = string
  default = "signalroom"
}

variable "max_investigations_per_day" {
  description = "Per-user daily investigation limit"
  type        = number
  default     = 20
}

variable "max_briefings_per_day" {
  description = "Per-user daily on-demand briefing limit"
  type        = number
  default     = 5
}
