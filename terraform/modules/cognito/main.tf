# Cognito User Pool: email + password, email verification, forgot password.
# The SPA uses a PUBLIC app client (no secret) with SRP/password auth directly
# from the browser — no hosted UI, so no callback URLs or custom domain are needed.

resource "aws_cognito_user_pool" "this" {
  name                     = "${var.name}-users"
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]
  mfa_configuration        = "OFF"
  deletion_protection      = var.deletion_protection ? "ACTIVE" : "INACTIVE"

  password_policy {
    minimum_length                   = 8
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = false
    temporary_password_validity_days = 7
  }

  dynamic "lambda_config" {
    for_each = local.invite_only ? [1] : []
    content {
      pre_sign_up = aws_lambda_function.pre_signup[0].arn
    }
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  verification_message_template {
    default_email_option = "CONFIRM_WITH_CODE"
    email_subject        = "Your SignalRoom verification code"
    email_message        = "Welcome to SignalRoom. Your verification code is {####}."
  }

  # Cognito's built-in email sender (50 emails/day) is enough for a class demo.
  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }

  schema {
    name                = "email"
    attribute_data_type = "String"
    required            = true
    mutable             = true
    string_attribute_constraints {
      min_length = 5
      max_length = 254
    }
  }
}

resource "aws_cognito_user_pool_client" "spa" {
  name                          = "${var.name}-spa"
  user_pool_id                  = aws_cognito_user_pool.this.id
  generate_secret               = false # public SPA client
  prevent_user_existence_errors = "ENABLED"
  enable_token_revocation       = true

  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
  ]

  access_token_validity  = 60
  id_token_validity      = 60
  refresh_token_validity = 30
  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }
}

# ------------------------------------------------------------------ invite-only sign-up
# Budget protection for the public demo: a pre sign-up Lambda rejects any email that is
# not in var.allowed_emails. Packaged by Terraform (archive provider): nothing manual.
locals {
  invite_only = length(var.allowed_emails) > 0
}

data "archive_file" "pre_signup" {
  count       = local.invite_only ? 1 : 0
  type        = "zip"
  source_file = "${path.module}/lambda/pre_signup.py"
  output_path = "${path.module}/lambda/pre_signup.zip"
}

resource "aws_iam_role" "pre_signup" {
  count = local.invite_only ? 1 : 0
  name  = "${var.name}-cognito-pre-signup"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy_attachment" "pre_signup_logs" {
  count      = local.invite_only ? 1 : 0
  role       = aws_iam_role.pre_signup[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "pre_signup" {
  count            = local.invite_only ? 1 : 0
  function_name    = "${var.name}-cognito-pre-signup"
  role             = aws_iam_role.pre_signup[0].arn
  runtime          = "python3.12"
  handler          = "pre_signup.handler"
  filename         = data.archive_file.pre_signup[0].output_path
  source_code_hash = data.archive_file.pre_signup[0].output_base64sha256
  timeout          = 5
  environment {
    variables = { ALLOWED_EMAILS = join(",", var.allowed_emails) }
  }
}

resource "aws_lambda_permission" "cognito_pre_signup" {
  count         = local.invite_only ? 1 : 0
  statement_id  = "AllowCognitoInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.pre_signup[0].function_name
  principal     = "cognito-idp.amazonaws.com"
  source_arn    = aws_cognito_user_pool.this.arn
}
