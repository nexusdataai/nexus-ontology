#!/bin/bash

ROLE_ARN=$1
PROFILE_NAME=$2

if [ -z "$ROLE_ARN" ] || [ -z "$PROFILE_NAME" ]; then
  echo "Usage: $0 <role-arn> <profile-name>"
  exit 1
fi

echo "Assuming role: $ROLE_ARN..."

CREDS=$(aws sts assume-role \
  --role-arn "$ROLE_ARN" \
  --role-session-name "$PROFILE_NAME-session" \
  --query 'Credentials.[AccessKeyId,SecretAccessKey,SessionToken]' \
  --output text)

if [ $? -ne 0 ]; then
  echo "❌ Failed to assume role."
  exit 1
fi

read AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN <<< "$CREDS"

aws configure set aws_access_key_id "$AWS_ACCESS_KEY_ID" --profile "$PROFILE_NAME"
aws configure set aws_secret_access_key "$AWS_SECRET_ACCESS_KEY" --profile "$PROFILE_NAME"
aws configure set aws_session_token "$AWS_SESSION_TOKEN" --profile "$PROFILE_NAME"

echo "✅ Temporary credentials stored in profile: $PROFILE_NAME"
echo "Test it with:"
echo "aws sts get-caller-identity --profile $PROFILE_NAME"