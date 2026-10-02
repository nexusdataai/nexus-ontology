# IAM Permissions

Required IAM permissions for the Nexus Telco Backend to access AWS services.

---

## Complete IAM Policy for ECS Task Role

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SSMParameterStore",
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParametersByPath",
        "ssm:PutParameter"
      ],
      "Resource": "arn:aws:ssm:*:*:parameter/call-processing/*"
    },
    {
      "Sid": "SecretsManager",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:call-processing/*"
    },
    {
      "Sid": "DynamoDB",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:BatchGetItem",
        "dynamodb:BatchWriteItem",
        "dynamodb:DescribeTable"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/call-processing-*",
        "arn:aws:dynamodb:*:*:table/call-processing-*/index/*"
      ]
    },
    {
      "Sid": "S3",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket",
        "s3:GetBucketLocation"
      ],
      "Resource": [
        "arn:aws:s3:::call-processing-*",
        "arn:aws:s3:::call-processing-*/*"
      ]
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogStreams"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/call-processing/*"
    },
    {
      "Sid": "GlueAthena",
      "Effect": "Allow",
      "Action": [
        "glue:GetDatabase",
        "glue:GetTable",
        "glue:GetPartitions",
        "glue:BatchGetPartition",
        "athena:StartQueryExecution",
        "athena:GetQueryExecution",
        "athena:GetQueryResults"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Permission Details

### SSM Parameter Store

```json
{
  "Sid": "SSMParameterStore",
  "Effect": "Allow",
  "Action": [
    "ssm:GetParameter",         // Get single parameter
    "ssm:GetParameters",        // Get multiple parameters
    "ssm:GetParametersByPath",  // Get all params under path
    "ssm:PutParameter"          // Update parameters (for log level API)
  ],
  "Resource": "arn:aws:ssm:*:*:parameter/call-processing/*"
}
```

**Note**: Wildcard `*` covers all environments (`/call-processing/dev/*`, `/call-processing/prod/*`, etc.)

### Secrets Manager

```json
{
  "Sid": "SecretsManager",
  "Effect": "Allow",
  "Action": [
    "secretsmanager:GetSecretValue",  // Read secret values
    "secretsmanager:DescribeSecret"   // Get secret metadata
  ],
  "Resource": "arn:aws:secretsmanager:*:*:secret:call-processing/*"
}
```

**Note**: Wildcard covers all environments (`call-processing/dev/*`, `call-processing/prod/*`, etc.)

### DynamoDB

```json
{
  "Sid": "DynamoDB",
  "Effect": "Allow",
  "Action": [
    "dynamodb:GetItem",
    "dynamodb:PutItem",
    "dynamodb:UpdateItem",
    "dynamodb:DeleteItem",
    "dynamodb:Query",
    "dynamodb:Scan",
    "dynamodb:BatchGetItem",
    "dynamodb:BatchWriteItem",
    "dynamodb:DescribeTable"
  ],
  "Resource": [
    "arn:aws:dynamodb:*:*:table/call-processing-*",
    "arn:aws:dynamodb:*:*:table/call-processing-*/index/*"
  ]
}
```

**Note**: Includes GSI access with `/index/*` pattern

### S3

```json
{
  "Sid": "S3",
  "Effect": "Allow",
  "Action": [
    "s3:GetObject",
    "s3:PutObject",
    "s3:DeleteObject",
    "s3:ListBucket",
    "s3:GetBucketLocation"
  ],
  "Resource": [
    "arn:aws:s3:::call-processing-*",
    "arn:aws:s3:::call-processing-*/*"
  ]
}
```

**Note**: First pattern for bucket-level operations (ListBucket), second for object-level operations

### CloudWatch Logs

```json
{
  "Sid": "CloudWatchLogs",
  "Effect": "Allow",
  "Action": [
    "logs:CreateLogGroup",
    "logs:CreateLogStream",
    "logs:PutLogEvents",
    "logs:DescribeLogStreams"
  ],
  "Resource": "arn:aws:logs:*:*:log-group:/aws/call-processing/*"
}
```

---

## ECS Execution Role

Separate role for ECS to manage container lifecycle:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECR",
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/call-processing/*"
    },
    {
      "Sid": "SecretsInjection",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:call-processing/*"
    }
  ]
}
```

---

## EKS IRSA Trust Policy

For EKS deployments using IAM Roles for Service Accounts:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/oidc.eks.REGION.amazonaws.com/id/OIDC_ID"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.eks.REGION.amazonaws.com/id/OIDC_ID:sub": "system:serviceaccount:call-processing:call-processing-sa",
          "oidc.eks.REGION.amazonaws.com/id/OIDC_ID:aud": "sts.amazonaws.com"
        }
      }
    }
  ]
}
```

---

## Minimal Permissions (Read-Only)

For applications that only need to read configuration:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SSMReadOnly",
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParametersByPath"
      ],
      "Resource": "arn:aws:ssm:*:*:parameter/call-processing/*"
    },
    {
      "Sid": "SecretsReadOnly",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:call-processing/*"
    }
  ]
}
```

---

## Create IAM Role (AWS CLI)

```bash
# Create trust policy file
cat > trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create role
aws iam create-role \
  --role-name call-processing-prod-task-role \
  --assume-role-policy-document file://trust-policy.json

# Attach policy
aws iam put-role-policy \
  --role-name call-processing-prod-task-role \
  --policy-name call-processing-access \
  --policy-document file://policy.json
```

---

*Related: [ECS Fargate](deployment-scenarios/ecs-fargate.md) | [EKS Kubernetes](deployment-scenarios/eks-kubernetes.md)*
