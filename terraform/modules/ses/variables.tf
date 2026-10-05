variable "sender_email" {
  description = "From address for briefing emails (empty = email disabled)"
  type        = string
  default     = ""
}

variable "sandbox_recipients" {
  description = "Recipient addresses to verify while SES is in sandbox mode"
  type        = list(string)
  default     = []
}
