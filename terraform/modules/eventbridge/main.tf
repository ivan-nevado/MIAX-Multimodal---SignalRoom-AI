# EventBridge Scheduler: ONE central schedule (not one per user). Every 15 minutes it
# starts the one-shot scheduler task, which finds users whose local briefing time has
# arrived and enqueues their jobs (idempotent per user/day). No cron inside containers.

resource "aws_scheduler_schedule" "daily_briefings" {
  name                         = "${var.name}-daily-briefings"
  description                  = "Find users due for their daily briefing and enqueue jobs"
  schedule_expression          = var.schedule_expression
  schedule_expression_timezone = "UTC"
  state                        = var.enabled ? "ENABLED" : "DISABLED"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = var.cluster_arn
    role_arn = var.scheduler_role_arn

    ecs_parameters {
      # Family name (without revision) always runs the latest task definition revision.
      task_definition_arn = replace(var.task_definition_arn, "/:\\d+$/", "")
      launch_type         = "FARGATE"
      task_count          = 1

      network_configuration {
        subnets          = var.subnet_ids
        security_groups  = [var.security_group_id]
        assign_public_ip = true
      }
    }

    retry_policy {
      maximum_retry_attempts       = 2
      maximum_event_age_in_seconds = 600
    }
  }
}

data "aws_iam_policy_document" "scheduler" {
  statement {
    actions   = ["ecs:RunTask"]
    resources = [replace(var.task_definition_arn, "/:\\d+$/", ":*")]
  }

  statement {
    actions   = ["iam:PassRole"]
    resources = var.pass_role_arns
  }
}

resource "aws_iam_role_policy" "scheduler" {
  name   = "${var.name}-scheduler-run-task"
  role   = var.scheduler_role_name
  policy = data.aws_iam_policy_document.scheduler.json
}
