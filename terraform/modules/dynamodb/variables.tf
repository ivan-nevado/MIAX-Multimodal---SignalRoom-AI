variable "prefix" {
  description = "Table name prefix; the app reads it from DYNAMODB_TABLE_PREFIX"
  type        = string
}

variable "point_in_time_recovery" {
  type    = bool
  default = false
}

variable "deletion_protection" {
  type    = bool
  default = false
}
