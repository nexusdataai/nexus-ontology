# EKS (Kubernetes) Deployment

Deployment on Amazon EKS with two configuration options: ConfigMap/Secrets or IRSA with SSM/Secrets Manager.

---

## Configuration Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          EKS CONFIGURATION                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Configuration Flow:                                                        │
│  ┌─────────────────┐     ┌─────────────────┐                                │
│  │ ConfigMap       │ ──► │                 │                                │
│  │ (env vars)      │     │  ConfigProvider │ ──► Application                │
│  ├─────────────────┤ ──► │                 │                                │
│  │ K8s Secrets     │     │                 │                                │
│  │ (or AWS SM)     │     │                 │                                │
│  └─────────────────┘     └─────────────────┘                                │
│                                                                             │
│  Option A: ConfigMap + K8s Secrets                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  ConfigMap: call-processing-config                                  │   │
│  │  ┌───────────────────────────────────────────────────────────────┐ │   │
│  │  │ ENVIRONMENT: prod                                             │ │   │
│  │  │ AWS_REGION: ap-southeast-1                                    │ │   │
│  │  │ DYNAMODB_TABLE: call-processing-prod-transformation-system    │ │   │
│  │  │ S3_RECORDINGS_BUCKET: call-processing-prod-call-data          │ │   │
│  │  └───────────────────────────────────────────────────────────────┘ │   │
│  │                                                                     │   │
│  │  Secret: call-processing-secrets                                    │   │
│  │  ┌───────────────────────────────────────────────────────────────┐ │   │
│  │  │ API_KEY: <base64-encoded>                                     │ │   │
│  │  │ OPENAI_API_KEY: <base64-encoded>                              │ │   │
│  │  └───────────────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Option B: AWS SSM + Secrets Manager with IRSA                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  • Use IAM Roles for Service Accounts (IRSA)                        │   │
│  │  • Pod assumes IAM role with SSM/Secrets permissions                │   │
│  │  • ConfigProvider loads from SSM just like ECS                      │   │
│  │  • Set ENVIRONMENT env var to trigger AWS config loading            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Option A: ConfigMap + Kubernetes Secrets

Best for: Teams preferring Kubernetes-native configuration management.

### ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: call-processing-config
  namespace: call-processing
data:
  ENVIRONMENT: "prod"
  AWS_REGION: "ap-southeast-1"
  DYNAMODB_TABLE: "call-processing-prod-transformation-system"
  LICENSE_TABLE: "call-processing-prod-license"
  S3_RECORDINGS_BUCKET: "call-processing-prod-call-data"
  WXCC_SIMULATOR_BUCKET: "call-processing-prod-wxcc-simulator"
  S3_JOURNEY_LOGS_BUCKET: "call-processing-prod-journey-logs"
  S3_JOURNEY_REPORTS_BUCKET: "call-processing-prod-journey-reports"
  GLUE_DATABASE_NAME: "call-processing-prod-analytics"
  GLUE_TABLE_NAME: "wxcc_calls"
  WXCC_SIMULATOR_ENABLED: "false"
  LOG_LEVEL: "INFO"
```

### Kubernetes Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: call-processing-secrets
  namespace: call-processing
type: Opaque
data:
  API_KEY: c3VwZXItc2VjcmV0  # base64 encoded
  OPENAI_API_KEY: c2stcHJvai14eHg=  # base64 encoded
```

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: call-processing-backend
  namespace: call-processing
spec:
  replicas: 2
  selector:
    matchLabels:
      app: call-processing-backend
  template:
    metadata:
      labels:
        app: call-processing-backend
    spec:
      serviceAccountName: call-processing-sa
      containers:
      - name: backend
        image: xxx.dkr.ecr.ap-southeast-1.amazonaws.com/call-processing:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: call-processing-config
        - secretRef:
            name: call-processing-secrets
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
```

---

## Option B: IRSA with SSM/Secrets Manager

Best for: Centralized configuration management consistent with ECS deployments.

### Service Account with IRSA

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: call-processing-sa
  namespace: call-processing
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::xxx:role/call-processing-prod-eks-role
```

### Deployment with IRSA

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: call-processing-backend
  namespace: call-processing
spec:
  replicas: 2
  selector:
    matchLabels:
      app: call-processing-backend
  template:
    metadata:
      labels:
        app: call-processing-backend
    spec:
      serviceAccountName: call-processing-sa  # IRSA enabled
      containers:
      - name: backend
        image: xxx.dkr.ecr.ap-southeast-1.amazonaws.com/call-processing:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "prod"
        - name: AWS_REGION
          value: "ap-southeast-1"
        # All other config loaded from SSM via ConfigProvider
```

### IAM Role for IRSA

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::xxx:oidc-provider/oidc.eks.ap-southeast-1.amazonaws.com/id/EXAMPLED539D4633E53DE1B716D3041E"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.eks.ap-southeast-1.amazonaws.com/id/EXAMPLED539D4633E53DE1B716D3041E:sub": "system:serviceaccount:call-processing:call-processing-sa"
        }
      }
    }
  ]
}
```

---

## Comparison: Option A vs Option B

| Aspect | Option A (ConfigMap) | Option B (IRSA) |
|--------|---------------------|-----------------|
| Configuration Location | Kubernetes ConfigMap/Secrets | AWS SSM/Secrets Manager |
| Secret Management | Kubernetes Secrets | AWS Secrets Manager |
| Centralized Config | Per-cluster | Cross-platform (ECS + EKS) |
| Config Updates | Requires pod restart | Can be dynamic (with cache invalidation) |
| Complexity | Lower | Higher (IRSA setup) |
| Best For | Simple deployments | Multi-platform consistency |

---

## Namespace Setup

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: call-processing
  labels:
    name: call-processing
```

---

## Health Checks

```yaml
# Add to container spec
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

---

## Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: call-processing-backend
  namespace: call-processing
spec:
  selector:
    app: call-processing-backend
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

---

*Related: [ECS Fargate](ecs-fargate.md) | [IAM Permissions](../iam-permissions.md)*
