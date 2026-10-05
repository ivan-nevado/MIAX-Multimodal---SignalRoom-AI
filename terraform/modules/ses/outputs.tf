output "sender_email" {
  value = var.sender_email
}

output "identity_arns" {
  value = concat([for i in aws_sesv2_email_identity.sender : i.arn], [for i in aws_sesv2_email_identity.test_recipients : i.arn])
}
