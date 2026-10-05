output "table_arns" {
  description = "ARNs of all tables"
  value       = [for t in aws_dynamodb_table.this : t.arn]
}

output "index_arns" {
  description = "ARNs of all secondary indexes (for IAM)"
  value       = [for t in aws_dynamodb_table.this : "${t.arn}/index/*"]
}

output "prefix" {
  value = var.prefix
}
