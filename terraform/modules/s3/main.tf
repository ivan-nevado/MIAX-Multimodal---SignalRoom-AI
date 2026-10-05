# Two PRIVATE buckets:
#  - frontend: static SPA, read only by CloudFront (Origin Access Control)
#  - uploads:  user files + generated media under users/{user_id}/..., accessed only via
#              short-lived presigned URLs. Never public.
# The uploads bucket CORS rule (browser PUT from the CloudFront origin) is defined in the
# environment because it depends on the CloudFront domain.

resource "aws_s3_bucket" "frontend" {
  bucket        = "${var.name}-frontend-${var.suffix}"
  force_destroy = var.force_destroy
}

resource "aws_s3_bucket" "uploads" {
  bucket        = "${var.name}-uploads-${var.suffix}"
  force_destroy = var.force_destroy
}

resource "aws_s3_bucket_public_access_block" "all" {
  for_each                = { frontend = aws_s3_bucket.frontend.id, uploads = aws_s3_bucket.uploads.id }
  bucket                  = each.value
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "all" {
  for_each = { frontend = aws_s3_bucket.frontend.id, uploads = aws_s3_bucket.uploads.id }
  bucket   = each.value
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "all" {
  for_each = { frontend = aws_s3_bucket.frontend.id, uploads = aws_s3_bucket.uploads.id }
  bucket   = each.value
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Data minimisation: raw uploads are deleted automatically after N days.
resource "aws_s3_bucket_lifecycle_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  rule {
    id     = "expire-raw-uploads"
    status = "Enabled"
    filter {
      prefix = "users/"
    }
    expiration {
      days = var.upload_retention_days
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

# Deny any non-TLS access.
resource "aws_s3_bucket_policy" "uploads_tls" {
  bucket = aws_s3_bucket.uploads.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "DenyInsecureTransport"
      Effect    = "Deny"
      Principal = "*"
      Action    = "s3:*"
      Resource  = [aws_s3_bucket.uploads.arn, "${aws_s3_bucket.uploads.arn}/*"]
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  })
  depends_on = [aws_s3_bucket_public_access_block.all]
}
