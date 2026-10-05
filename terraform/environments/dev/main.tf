locals {
  name = "${var.project}-${var.environment}"
}

resource "random_id" "suffix" {
  byte_length = 3
}

# Shared secret between CloudFront and the ALB (not an API key; never leaves AWS).
resource "random_password" "origin_verify" {
  length  = 40
  special = false
}

module "networking" {
  source = "../../modules/networking"
  name   = local.name
}

module "ecr" {
  source = "../../modules/ecr"
  name   = local.name
}

module "s3" {
  source = "../../modules/s3"
  name   = local.name
  suffix = random_id.suffix.hex
}

module "dynamodb" {
  source = "../../modules/dynamodb"
  prefix = local.name
}

module "sqs" {
  source = "../../modules/sqs"
  name   = local.name
}

module "secrets" {
  source = "../../modules/secrets-manager"
  name   = "${var.project}/${var.environment}"
}

module "cognito" {
  source         = "../../modules/cognito"
  name           = local.name
  allowed_emails = var.allowed_emails
}

module "ses" {
  source             = "../../modules/ses"
  sender_email       = var.ses_from_email
  sandbox_recipients = var.ses_sandbox_recipients
}

module "alb" {
  source               = "../../modules/alb"
  name                 = local.name
  vpc_id               = module.networking.vpc_id
  subnet_ids           = module.networking.public_subnet_ids
  security_group_id    = module.networking.alb_security_group_id
  origin_verify_secret = random_password.origin_verify.result
}

module "cloudfront" {
  source                               = "../../modules/cloudfront"
  name                                 = local.name
  frontend_bucket_id                   = module.s3.frontend_bucket_id
  frontend_bucket_arn                  = module.s3.frontend_bucket_arn
  frontend_bucket_regional_domain_name = module.s3.frontend_bucket_regional_domain_name
  alb_dns_name                         = module.alb.dns_name
  origin_verify_secret                 = random_password.origin_verify.result
  basic_auth_user                      = var.site_username
  basic_auth_password                  = var.site_password
}

# Browsers upload directly to the private uploads bucket with presigned PUT URLs.
resource "aws_s3_bucket_cors_configuration" "uploads" {
  bucket = module.s3.uploads_bucket_id
  cors_rule {
    allowed_methods = ["PUT", "GET"]
    allowed_origins = [module.cloudfront.url]
    allowed_headers = ["Content-Type"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

module "iam" {
  source              = "../../modules/iam"
  name                = local.name
  dynamodb_table_arns = module.dynamodb.table_arns
  dynamodb_index_arns = module.dynamodb.index_arns
  uploads_bucket_arn  = module.s3.uploads_bucket_arn
  queue_arns          = module.sqs.queue_arns
  secret_arn          = module.secrets.secret_arn
}

module "ecs" {
  source                  = "../../modules/ecs"
  name                    = local.name
  region                  = var.region
  app_env                 = var.environment
  image_repository_url    = module.ecr.repository_url
  image_tag               = var.image_tag
  subnet_ids              = module.networking.public_subnet_ids
  security_group_id       = module.networking.tasks_security_group_id
  target_group_arn        = module.alb.target_group_arn
  execution_role_arn      = module.iam.execution_role_arn
  task_role_arn           = module.iam.task_role_arn
  dynamodb_table_prefix   = module.dynamodb.prefix
  uploads_bucket          = module.s3.uploads_bucket_id
  investigation_queue_url = module.sqs.investigation_queue_url
  briefing_queue_url      = module.sqs.briefing_queue_url
  secret_arn              = module.secrets.secret_arn
  cognito_user_pool_id    = module.cognito.user_pool_id
  cognito_client_id       = module.cognito.client_id
  ses_from_email          = var.ses_from_email
  public_url              = module.cloudfront.url
  extra_environment       = var.model_overrides
  api_desired_count       = var.api_desired_count
  worker_desired_count    = var.worker_desired_count
  worker_use_spot         = var.worker_use_spot

  allowed_emails             = var.allowed_emails
  max_investigations_per_day = var.max_investigations_per_day
  max_briefings_per_day      = var.max_briefings_per_day
}

module "eventbridge" {
  source              = "../../modules/eventbridge"
  name                = local.name
  enabled             = var.briefing_schedule_enabled
  cluster_arn         = module.ecs.cluster_arn
  task_definition_arn = module.ecs.scheduler_task_definition_arn
  subnet_ids          = module.networking.public_subnet_ids
  security_group_id   = module.networking.tasks_security_group_id
  scheduler_role_arn  = module.iam.scheduler_role_arn
  scheduler_role_name = module.iam.scheduler_role_name
  pass_role_arns      = [module.iam.execution_role_arn, module.iam.task_role_arn]
}
