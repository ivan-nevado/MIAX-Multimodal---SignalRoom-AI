# ECS Fargate: one image, three task definitions.
#   api       → service behind the ALB         (uvicorn app.main:app)
#   worker    → service polling SQS            (python -m app.workers.sqs_worker)
#   scheduler → one-shot task run by EventBridge (python -m app.workers.daily_briefing_scheduler)
# API keys are NOT in the task definitions: tasks receive SECRETS_MANAGER_SECRET_ID and
# load the secret at startup with their task role.

locals {
  image = "${var.image_repository_url}:${var.image_tag}"

  common_env = [for k, v in merge({
    APP_ENV                     = var.app_env
    BACKEND_MODE                = "aws"
    AUTH_MODE                   = "cognito"
    LOG_LEVEL                   = "INFO"
    AWS_REGION                  = var.region
    DYNAMODB_TABLE_PREFIX       = var.dynamodb_table_prefix
    S3_BUCKET                   = var.uploads_bucket
    SQS_INVESTIGATION_QUEUE_URL = var.investigation_queue_url
    SQS_BRIEFING_QUEUE_URL      = var.briefing_queue_url
    SECRETS_MANAGER_SECRET_ID   = var.secret_arn
    COGNITO_USER_POOL_ID        = var.cognito_user_pool_id
    COGNITO_APP_CLIENT_ID       = var.cognito_client_id
    COGNITO_REGION              = var.region
    SES_FROM_EMAIL              = var.ses_from_email
    APP_BASE_URL                = var.public_url
    FRONTEND_URL                = var.public_url
    CORS_ORIGINS                = var.public_url
    ALLOWED_EMAILS              = join(",", var.allowed_emails)
    MAX_INVESTIGATIONS_PER_DAY  = tostring(var.max_investigations_per_day)
    MAX_BRIEFINGS_PER_DAY       = tostring(var.max_briefings_per_day)
  }, var.extra_environment) : { name = k, value = v }]

  roles = {
    api       = { command = null, cpu = var.api_cpu, memory = var.api_memory }
    worker    = { command = ["python", "-m", "app.workers.sqs_worker"], cpu = var.worker_cpu, memory = var.worker_memory }
    scheduler = { command = ["python", "-m", "app.workers.daily_briefing_scheduler"], cpu = 256, memory = 512 }
  }
}

resource "aws_ecs_cluster" "this" {
  name = "${var.name}-cluster"
  setting {
    name  = "containerInsights"
    value = "disabled" # enable in production; costs extra CloudWatch metrics
  }
}

resource "aws_ecs_cluster_capacity_providers" "this" {
  cluster_name       = aws_ecs_cluster.this.name
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]
}

resource "aws_cloudwatch_log_group" "this" {
  for_each          = local.roles
  name              = "/ecs/${var.name}/${each.key}"
  retention_in_days = var.log_retention_days
}

resource "aws_ecs_task_definition" "this" {
  for_each                 = local.roles
  family                   = "${var.name}-${each.key}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = each.value.cpu
  memory                   = each.value.memory
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([merge(
    {
      name        = each.key
      image       = local.image
      essential   = true
      environment = local.common_env
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.this[each.key].name
          awslogs-region        = var.region
          awslogs-stream-prefix = each.key
        }
      }
    },
    each.value.command == null ? {} : { command = each.value.command },
    each.key == "api" ? { portMappings = [{ containerPort = var.container_port, protocol = "tcp" }] } : {},
    # The image HEALTHCHECK probes the API port; workers have none.
    each.key == "api" ? {} : { healthCheck = { command = ["CMD-SHELL", "exit 0"], interval = 60, timeout = 5, retries = 3 } },
  )])
}

resource "aws_ecs_service" "api" {
  name                              = "${var.name}-api"
  cluster                           = aws_ecs_cluster.this.id
  task_definition                   = aws_ecs_task_definition.this["api"].arn
  desired_count                     = var.api_desired_count
  launch_type                       = "FARGATE"
  health_check_grace_period_seconds = 60
  enable_execute_command            = false

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = [var.security_group_id]
    assign_public_ip = true # no NAT gateway: see modules/networking
  }

  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = "api"
    container_port   = var.container_port
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
}

resource "aws_ecs_service" "worker" {
  name            = "${var.name}-worker"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.this["worker"].arn
  desired_count   = var.worker_desired_count

  # Spot is ~70% cheaper; SQS redelivery makes interruptions safe for idempotent jobs.
  capacity_provider_strategy {
    capacity_provider = var.worker_use_spot ? "FARGATE_SPOT" : "FARGATE"
    weight            = 1
  }

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = [var.security_group_id]
    assign_public_ip = true
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  depends_on = [aws_ecs_cluster_capacity_providers.this]
}
