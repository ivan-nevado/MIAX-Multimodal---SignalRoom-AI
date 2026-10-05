variable "name" {
  type = string
}

variable "schedule_expression" {
  type    = string
  default = "rate(15 minutes)"
}

variable "enabled" {
  type    = bool
  default = true
}

variable "cluster_arn" {
  type = string
}

variable "task_definition_arn" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "security_group_id" {
  type = string
}

variable "scheduler_role_arn" {
  type = string
}

variable "scheduler_role_name" {
  type = string
}

variable "pass_role_arns" {
  description = "Task execution + task role ARNs the scheduler must pass to ECS"
  type        = list(string)
}
