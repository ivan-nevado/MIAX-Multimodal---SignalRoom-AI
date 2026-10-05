variable "name" {
  type = string
}

variable "deletion_protection" {
  type    = bool
  default = false
}

variable "allowed_emails" {
  description = "Invite list: exact emails and/or @domain entries. Empty = open sign-up."
  type        = list(string)
  default     = []
}
