output "cluster_name" {
  value = aws_ecs_cluster.this.name
}

output "cluster_arn" {
  value = aws_ecs_cluster.this.arn
}

output "api_service_name" {
  value = aws_ecs_service.api.name
}

output "worker_service_name" {
  value = aws_ecs_service.worker.name
}

output "scheduler_task_definition_arn" {
  value = aws_ecs_task_definition.this["scheduler"].arn
}

output "scheduler_task_definition_family" {
  value = aws_ecs_task_definition.this["scheduler"].family
}

output "log_groups" {
  value = { for k, g in aws_cloudwatch_log_group.this : k => g.name }
}
