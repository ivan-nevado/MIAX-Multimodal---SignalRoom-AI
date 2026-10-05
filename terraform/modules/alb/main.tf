# Application Load Balancer in front of the FastAPI service.
#
# No custom domain → no ACM certificate on the ALB: viewers talk HTTPS to CloudFront
# (free *.cloudfront.net certificate) and CloudFront talks HTTP to the ALB inside AWS.
# The ALB only forwards requests carrying the secret X-Origin-Verify header that
# CloudFront adds, and its security group only admits CloudFront's prefix list, so
# the ALB cannot be used to bypass CloudFront.

resource "aws_lb" "this" {
  name                       = "${var.name}-alb"
  load_balancer_type         = "application"
  security_groups            = [var.security_group_id]
  subnets                    = var.subnet_ids
  idle_timeout               = 120 # long enough for Server-Sent Events between keep-alives
  drop_invalid_header_fields = true
}

resource "aws_lb_target_group" "api" {
  name        = "${var.name}-api"
  port        = var.container_port
  protocol    = "HTTP"
  target_type = "ip" # Fargate awsvpc
  vpc_id      = var.vpc_id

  health_check {
    path                = "/api/v1/health/live"
    matcher             = "200"
    interval            = 20
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  deregistration_delay = 30
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.this.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "text/plain"
      message_body = "Forbidden"
      status_code  = "403"
    }
  }
}

resource "aws_lb_listener_rule" "from_cloudfront" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 10

  condition {
    http_header {
      http_header_name = "X-Origin-Verify"
      values           = [var.origin_verify_secret]
    }
  }

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}
