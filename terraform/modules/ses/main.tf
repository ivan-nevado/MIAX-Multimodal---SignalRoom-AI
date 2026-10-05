# SES email identity for the daily briefing sender.
#
# Without a custom domain we verify a single email address: AWS sends a confirmation
# link to it after `terraform apply`. While the account is in the SES SANDBOX, every
# RECIPIENT must also be verified (see docs/email_setup.md) — fine for a class demo.
# With a domain you would create a domain identity + DKIM records instead.

resource "aws_sesv2_email_identity" "sender" {
  count          = var.sender_email == "" ? 0 : 1
  email_identity = var.sender_email
}

resource "aws_sesv2_email_identity" "test_recipients" {
  for_each       = toset(var.sandbox_recipients)
  email_identity = each.value
}
