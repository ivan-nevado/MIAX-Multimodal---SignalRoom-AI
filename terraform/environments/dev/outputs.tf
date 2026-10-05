output "app_url" {
  description = "Public HTTPS URL of SignalRoom (UI + /api) — no custom domain needed"
  value       = module.cloudfront.url
}

output "api_docs_url" {
  value = "${module.cloudfront.url}/api/docs"
}

output "cloudfront_distribution_id" {
  value = module.cloudfront.distribution_id
}

output "frontend_bucket" {
  value = module.s3.frontend_bucket_id
}

output "uploads_bucket" {
  value = module.s3.uploads_bucket_id
}

output "ecr_repository_url" {
  value = module.ecr.repository_url
}

output "ecs_cluster" {
  value = module.ecs.cluster_name
}

output "ecs_api_service" {
  value = module.ecs.api_service_name
}

output "ecs_worker_service" {
  value = module.ecs.worker_service_name
}

output "scheduler_task_family" {
  value = module.ecs.scheduler_task_definition_family
}

output "log_groups" {
  value = module.ecs.log_groups
}

output "secret_name" {
  description = "Populate with scripts/set_secrets.sh (values never go through Terraform)"
  value       = module.secrets.secret_name
}

output "cognito_user_pool_id" {
  value = module.cognito.user_pool_id
}

output "cognito_client_id" {
  value = module.cognito.client_id
}

output "region" {
  value = var.region
}

output "public_subnet_ids" {
  value = module.networking.public_subnet_ids
}

output "tasks_security_group_id" {
  value = module.networking.tasks_security_group_id
}

output "invite_only" {
  description = "true when sign-up is restricted to var.allowed_emails"
  value       = module.cognito.invite_only
}

output "site_password_enabled" {
  value = nonsensitive(var.site_password != "")
}
