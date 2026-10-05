variable "name" {
  type = string
}

variable "dynamodb_table_arns" {
  type = list(string)
}

variable "dynamodb_index_arns" {
  type = list(string)
}

variable "uploads_bucket_arn" {
  type = string
}

variable "queue_arns" {
  type = list(string)
}

variable "secret_arn" {
  type = string
}
