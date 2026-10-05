# DynamoDB tables — must match backend/app/repositories/dynamodb_schema.py.
# On-demand billing: zero cost when idle, no capacity planning for an MVP.

locals {
  user_index = "user_id-created_at-index"

  tables = {
    users = {
      hash_key   = "user_id"
      range_key  = null
      attributes = { user_id = "S" }
      gsi        = false
      ttl        = false
    }
    watchlists = {
      hash_key   = "user_id"
      range_key  = "symbol"
      attributes = { user_id = "S", symbol = "S" }
      gsi        = false
      ttl        = false
    }
    investigations = {
      hash_key   = "investigation_id"
      range_key  = null
      attributes = { investigation_id = "S", user_id = "S", created_at = "S" }
      gsi        = true
      ttl        = false
    }
    investigation-events = {
      hash_key   = "investigation_id"
      range_key  = "seq"
      attributes = { investigation_id = "S", seq = "N" }
      gsi        = false
      ttl        = true # transient progress events expire after 7 days
    }
    briefings = {
      hash_key   = "briefing_id"
      range_key  = null
      attributes = { briefing_id = "S", user_id = "S", created_at = "S" }
      gsi        = true
      ttl        = false
    }
    briefing-deliveries = {
      hash_key   = "delivery_key" # user_id#date#briefing_type → idempotency
      range_key  = null
      attributes = { delivery_key = "S" }
      gsi        = false
      ttl        = true
    }
    uploads = {
      hash_key   = "upload_id"
      range_key  = null
      attributes = { upload_id = "S", user_id = "S", created_at = "S" }
      gsi        = true
      ttl        = false
    }
    cache = {
      hash_key   = "cache_key" # provider:kind:asset:query:window
      range_key  = null
      attributes = { cache_key = "S" }
      gsi        = false
      ttl        = true
    }
  }
}

resource "aws_dynamodb_table" "this" {
  for_each     = local.tables
  name         = "${var.prefix}-${each.key}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = each.value.hash_key
  range_key    = each.value.range_key

  dynamic "attribute" {
    for_each = each.value.attributes
    content {
      name = attribute.key
      type = attribute.value
    }
  }

  dynamic "global_secondary_index" {
    for_each = each.value.gsi ? [1] : []
    content {
      name            = local.user_index
      hash_key        = "user_id"
      range_key       = "created_at"
      projection_type = "ALL"
    }
  }

  dynamic "ttl" {
    for_each = each.value.ttl ? [1] : []
    content {
      attribute_name = "expires_at"
      enabled        = true
    }
  }

  point_in_time_recovery {
    enabled = var.point_in_time_recovery
  }

  server_side_encryption {
    enabled = true
  }

  deletion_protection_enabled = var.deletion_protection
}
