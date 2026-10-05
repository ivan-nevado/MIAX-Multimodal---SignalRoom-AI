output "investigation_queue_url" {
  value = aws_sqs_queue.main["investigation"].url
}

output "briefing_queue_url" {
  value = aws_sqs_queue.main["briefing"].url
}

output "queue_arns" {
  value = concat([for q in aws_sqs_queue.main : q.arn], [for q in aws_sqs_queue.dlq : q.arn])
}
