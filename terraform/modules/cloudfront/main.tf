# One CloudFront distribution = one HTTPS origin for the whole product (no domain needed):
#   https://<id>.cloudfront.net/        → S3 SPA (Origin Access Control, SPA rewrite)
#   https://<id>.cloudfront.net/api/*   → ALB → FastAPI (no caching, all methods, SSE)
# Same origin for UI and API ⇒ no CORS between them and a single URL to share.

data "aws_cloudfront_cache_policy" "optimized" {
  name = "Managed-CachingOptimized"
}

data "aws_cloudfront_cache_policy" "disabled" {
  name = "Managed-CachingDisabled"
}

data "aws_cloudfront_origin_request_policy" "all_viewer_except_host" {
  name = "Managed-AllViewerExceptHostHeader"
}

data "aws_cloudfront_response_headers_policy" "security" {
  name = "Managed-SecurityHeadersPolicy"
}

resource "aws_cloudfront_origin_access_control" "frontend" {
  name                              = "${var.name}-frontend-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

locals {
  basic_auth_enabled = var.basic_auth_password != ""
  basic_auth_header  = "Basic ${base64encode("${var.basic_auth_user}:${var.basic_auth_password}")}"
}

# Viewer-request function on the SPA behaviour only:
#  1. optional site-wide password (HTTP Basic Auth): without it nobody even sees the demo
#  2. client-side routing: /app/dashboard etc. are served by index.html (API 404s untouched)
# The /api/* behaviour has no function: API calls are authenticated with Cognito JWTs.
resource "aws_cloudfront_function" "spa_rewrite" {
  name    = "${var.name}-spa-rewrite"
  runtime = "cloudfront-js-2.0"
  publish = true
  code    = <<-EOT
    function handler(event) {
      var request = event.request;
      var expected = ${local.basic_auth_enabled ? jsonencode(local.basic_auth_header) : "null"};
      if (expected) {
        var auth = request.headers.authorization;
        if (!auth || auth.value !== expected) {
          return {
            statusCode: 401,
            statusDescription: 'Unauthorized',
            headers: { 'www-authenticate': { value: 'Basic realm="SignalRoom demo"' } }
          };
        }
      }
      if (!request.uri.includes('.')) { request.uri = '/index.html'; }
      return request;
    }
  EOT
}

resource "aws_cloudfront_distribution" "this" {
  enabled             = true
  comment             = "${var.name} SPA + API"
  default_root_object = "index.html"
  price_class         = var.price_class
  http_version        = "http2and3"

  origin {
    origin_id                = "frontend"
    domain_name              = var.frontend_bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.frontend.id
  }

  origin {
    origin_id   = "api"
    domain_name = var.alb_dns_name
    custom_origin_config {
      http_port                = 80
      https_port               = 443
      origin_protocol_policy   = "http-only"
      origin_ssl_protocols     = ["TLSv1.2"]
      origin_read_timeout      = 60 # SSE streams close at ~50 s and the client reconnects
      origin_keepalive_timeout = 60
    }
    custom_header {
      name  = "X-Origin-Verify"
      value = var.origin_verify_secret
    }
  }

  default_cache_behavior {
    target_origin_id           = "frontend"
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD", "OPTIONS"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    cache_policy_id            = data.aws_cloudfront_cache_policy.optimized.id
    response_headers_policy_id = data.aws_cloudfront_response_headers_policy.security.id

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.spa_rewrite.arn
    }
  }

  ordered_cache_behavior {
    path_pattern             = "/api/*"
    target_origin_id         = "api"
    viewer_protocol_policy   = "redirect-to-https"
    allowed_methods          = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods           = ["GET", "HEAD"]
    compress                 = false # do not buffer/compress text/event-stream
    cache_policy_id          = data.aws_cloudfront_cache_policy.disabled.id
    origin_request_policy_id = data.aws_cloudfront_origin_request_policy.all_viewer_except_host.id
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true # free HTTPS on *.cloudfront.net
  }
}

# Only this distribution may read the frontend bucket.
resource "aws_s3_bucket_policy" "frontend" {
  bucket = var.frontend_bucket_id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AllowCloudFrontRead"
      Effect    = "Allow"
      Principal = { Service = "cloudfront.amazonaws.com" }
      Action    = "s3:GetObject"
      Resource  = "${var.frontend_bucket_arn}/*"
      Condition = { StringEquals = { "AWS:SourceArn" = aws_cloudfront_distribution.this.arn } }
    }]
  })
}
