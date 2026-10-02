# Kubernetes Deployment Guide with nginx Proxy

Complete guide for deploying nexus-ui to Kubernetes with internal backend proxy and external API access.

---

## 🏗️ Architecture Overview

```
┌────────────────────────────────────────────────────────────┐
│  Internet                                                   │
│                                                              │
│  Browser → Frontend LB:8080 (HTTPS)                        │
│  External App → Backend LB:8000 (HTTP/HTTPS)               │
└──────────────────┬───────────────────┬─────────────────────┘
                   │                   │
                   ▼                   ▼
┌────────────────────────────────────────────────────────────┐
│  AWS LoadBalancers                                          │
│  - Frontend LB (port 8080)                                 │
│  - Backend LB (port 8000)                                  │
└──────────────────┬───────────────────┬─────────────────────┘
                   │                   │
                   ▼                   ▼
┌────────────────────────────────────────────────────────────┐
│  Kubernetes Cluster (call-processing-prod namespace)       │
│                                                              │
│  ┌──────────────────┐          ┌──────────────────┐       │
│  │ Frontend Pods    │          │ Backend Pods     │       │
│  │ (nginx + React)  │──────────│ (API server)     │       │
│  │ Port: 8080       │ Internal │ Port: 8000       │       │
│  └──────────────────┘  ClusterIP └──────────────────┘     │
│          │             Service            ▲                 │
│          └─────────────────────────────────┘                │
│            nginx proxy_pass (HTTP OK - internal)            │
└────────────────────────────────────────────────────────────┘
```

**Key Points:**
- Frontend nginx proxies `/api/*` to internal backend (fast, secure)
- External apps use LoadBalancer directly (public, requires auth)
- Same backend pods serve both (no duplication)

---

## 📋 **Prerequisites**

- Kubernetes cluster (EKS recommended)
- kubectl configured
- Docker for building images
- AWS CLI for ECR access
- Totogi Operator deployed

---

## 🚀 **Step-by-Step Deployment**

### Step 1: Build Frontend Image with Proxy Config

```bash
cd /opt/mycode/trilogy/nexus-ui

# Verify nginx.conf has proxy configuration
grep -A5 "location /api/" nginx.conf

# Build image
docker build -t nexus-ui:latest .

# Tag for ECR
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --profile external-access)
REGION="ap-southeast-1"
ECR_REPO="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/nexus-ui"

docker tag nexus-ui:latest ${ECR_REPO}:latest

# Login to ECR
aws ecr get-login-password --region ${REGION} --profile external-access | \
  docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com

# Create repository if needed
aws ecr create-repository --repository-name nexus-ui --region ${REGION} --profile external-access 2>/dev/null || true

# Push image
docker push ${ECR_REPO}:latest

echo "✓ Frontend image pushed: ${ECR_REPO}:latest"
```

### Step 2: Build Backend Image

```bash
cd /opt/mycode/trilogy/nexus-backend

# Build image (ensure it listens on port 8000)
docker build -t ai-job-engine:latest .

# Tag for ECR
docker tag ai-job-engine:latest ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/ai-job-engine:latest

# Create repository if needed
aws ecr create-repository --repository-name ai-job-engine --region ${REGION} --profile external-access 2>/dev/null || true

# Push image
docker push ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/ai-job-engine:latest

echo "✓ Backend image pushed: ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/ai-job-engine:latest"
```

### Step 3: Deploy Complete Stack

```bash
cd /opt/mycode/trilogy/nexus-deployer/kube-operator

# Create namespace
kubectl create namespace call-processing-prod

# Deploy everything (TotogiCapability + dual services)
kubectl apply -f examples/call-processing-complete.yaml

# Wait for pods to be ready (2-3 minutes)
kubectl wait --for=condition=ready pod \
  -l app.kubernetes.io/name=call-processing \
  -n call-processing-prod \
  --timeout=5m
```

### Step 4: Verify Deployment

```bash
# Check all resources
kubectl get all -n call-processing-prod

# Should see:
# - 3 frontend pods (Running)
# - 3 backend pods (Running)
# - frontend-svc (LoadBalancer)
# - backend-svc-internal (ClusterIP)
# - backend-svc-external (LoadBalancer)
```

### Step 5: Get URLs

```bash
# Frontend URL (for browsers)
FRONTEND_URL=$(kubectl get svc call-processing-prod-frontend-svc -n call-processing-prod -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "Frontend: http://${FRONTEND_URL}:8080"

# External API URL (for external apps)
BACKEND_URL=$(kubectl get svc call-processing-prod-backend-svc-external -n call-processing-prod -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "Backend API: http://${BACKEND_URL}:8000"
```

### Step 6: Test Internal Communication

```bash
# Get a frontend pod name
FRONTEND_POD=$(kubectl get pods -n call-processing-prod -o name | grep frontend | head -1 | cut -d'/' -f2)

# Test that frontend can reach backend via internal service
kubectl exec -n call-processing-prod "$FRONTEND_POD" -- \
  wget -O- --timeout=5 "http://call-processing-prod-backend-svc-internal:8000/health"

# Expected: Backend health response
```

### Step 7: Test External API Access

```bash
# Test external LoadBalancer
curl "http://${BACKEND_URL}:8000/api/v1/health"

# Expected: Backend health response
```

---

## 🔧 **Configuration Details**

### Frontend nginx.conf

**Key sections added:**
```nginx
# WebSocket support (at http level)
map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}

# API proxy (in server block)
location /api/ {
    proxy_pass http://call-processing-prod-backend-svc-internal:8000;
    # ... headers and settings
}
```

### Frontend config.json

**For Kubernetes deployment:**
```json
{
  "api": {
    "baseUrl": "",  // Empty = use nginx proxy
    "timeout": 30000
  }
}
```

**How it works:**
```javascript
// In your React app
fetch('/api/v1/jobs')  // Relative URL
  ↓
nginx intercepts /api/
  ↓
Proxies to http://backend-internal:8000/api/v1/jobs
  ↓
Backend responds
  ↓
nginx returns to browser
  ↓
Browser sees HTTPS response (no mixed content)
```

---

## 🔍 **Service Configuration**

### Services Created

```bash
kubectl get svc -n call-processing-prod

NAME                                       TYPE           PORT(S)
call-processing-prod-frontend-svc          LoadBalancer   8080:xxxxx/TCP
call-processing-prod-backend-svc           LoadBalancer   8000:xxxxx/TCP  (operator creates this)
call-processing-prod-backend-svc-internal  ClusterIP      8000/TCP        (we create this)
call-processing-prod-backend-svc-external  LoadBalancer   8000:xxxxx/TCP  (we create this)
```

**Note:** Operator creates one backend LoadBalancer by default. You can either:
- Rename it to `-external`
- Delete it and create both internal + external
- Keep it and add internal ClusterIP

### Service Selection by Use Case

| Use Case | Service to Use | Why |
|----------|---------------|-----|
| **UI → Backend** | `backend-svc-internal` (ClusterIP) | Fast, private, free |
| **External apps** | `backend-svc-external` (LoadBalancer) | Public, requires auth |
| **Testing internally** | `backend-svc-internal` | Quick, no internet |

---

## 🔒 **Security Configuration**

### Internal Service (ClusterIP)

**Already secure by default:**
- ✅ Not accessible from internet
- ✅ Only pods in cluster can reach it
- ✅ No public IP assigned

**Optional: Network Policies**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-internal-policy
  namespace: call-processing-prod
spec:
  podSelector:
    matchLabels:
      app: call-processing-prod-backend
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: call-processing-prod-frontend  # Only frontend can access
      ports:
        - port: 8000
```

### External Service (LoadBalancer)

**Add authentication in backend:**
```python
# FastAPI backend
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key"
        )
    
    # Verify against stored keys (from env var or Secrets Manager)
    valid_keys = os.getenv("API_KEYS", "").split(",")
    if api_key not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
    
    return api_key

@app.get("/api/v1/jobs")
async def get_jobs(api_key: str = Security(verify_api_key)):
    # Only accessible with valid API key
    return {"jobs": [...]}
```

**AWS Security Group (if needed):**
```bash
# Get LoadBalancer security group
aws elbv2 describe-load-balancers --region ap-southeast-1 | grep SecurityGroups

# Add rule to restrict access
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxx \
  --protocol tcp \
  --port 8000 \
  --cidr 203.0.113.0/24  # Only allow specific IPs
```

---

## 📊 **Performance Testing**

### Internal (UI → Backend)

```bash
# From frontend pod
kubectl exec -n call-processing-prod FRONTEND_POD -- \
  time wget -O- http://call-processing-prod-backend-svc-internal:8000/api/v1/health

# Expected: ~5-10ms
```

### External (Apps → Backend)

```bash
# From outside cluster
time curl http://EXTERNAL-LB:8000/api/v1/health

# Expected: ~50-100ms (depends on location)
```

---

## 🧪 **Testing Checklist**

- [ ] Frontend image built with nginx proxy config
- [ ] Backend image built and pushed to ECR
- [ ] Namespace created
- [ ] TotogiCapability deployed
- [ ] Internal ClusterIP service created
- [ ] External LoadBalancer service created
- [ ] Frontend pods running (3/3)
- [ ] Backend pods running (3/3)
- [ ] Frontend can reach backend via internal service
- [ ] External apps can reach backend via LoadBalancer
- [ ] No mixed content errors in browser console
- [ ] API calls succeed from UI
- [ ] External API calls succeed with auth

---

## 🔄 **Updating Deployed Application**

### Update Frontend

```bash
# Rebuild with new code
cd /opt/mycode/trilogy/nexus-ui
docker build -t nexus-ui:latest .
docker push ${ECR_REPO}:latest

# Restart pods to pull new image
kubectl rollout restart deployment/call-processing-prod-frontend -n call-processing-prod

# Watch rollout
kubectl rollout status deployment/call-processing-prod-frontend -n call-processing-prod
```

### Update Backend

```bash
# Rebuild
cd /opt/mycode/trilogy/nexus-backend
docker build -t ai-job-engine:latest .
docker push ${ECR_REPO}:latest

# Restart
kubectl rollout restart deployment/call-processing-prod-backend -n call-processing-prod
```

---

## 🆘 **Troubleshooting**

### Frontend Can't Reach Backend

**Check nginx proxy config:**
```bash
kubectl exec -n call-processing-prod FRONTEND_POD -- cat /etc/nginx/nginx.conf | grep -A10 "location /api/"
```

**Check internal service exists:**
```bash
kubectl get svc call-processing-prod-backend-svc-internal -n call-processing-prod
```

**Test DNS resolution:**
```bash
kubectl exec -n call-processing-prod FRONTEND_POD -- nslookup call-processing-prod-backend-svc-internal
```

### External Apps Can't Reach Backend

**Check LoadBalancer is ready:**
```bash
kubectl get svc call-processing-prod-backend-svc-external -n call-processing-prod

# EXTERNAL-IP should NOT be <pending>
```

**Check security groups:**
```bash
# LoadBalancer should allow port 8000 from your IP
curl -v http://EXTERNAL-LB:8000/api/v1/health
```

### Mixed Content Errors

**Check nginx proxy is working:**
```bash
# From browser console, check Network tab
# URLs should be: /api/v1/... (relative, not absolute http://)
```

**Verify config.json has empty baseUrl:**
```bash
curl https://FRONTEND-LB:8080/config.json
# Should show: "baseUrl": ""
```

---

## 📝 **Summary**

### Files Modified

| File | Changes | Purpose |
|------|---------|---------|
| `nginx.conf` | Added `location /api/` with proxy_pass | Proxy API requests to internal backend |
| `public/config.json` | Set `baseUrl: ""` | Use nginx proxy (relative URLs) |
| `public/config.kubernetes.json` | New example config | Template for K8s deployments |

### Files Created

| File | Purpose |
|------|---------|
| `NGINX-PROXY-SETUP.md` | nginx proxy documentation |
| `KUBERNETES-DEPLOYMENT.md` | This complete guide |
| `kube-operator/examples/dual-service-backend.yaml` | Service definitions |
| `kube-operator/examples/call-processing-complete.yaml` | Complete deployment example |

### Deployment Results

```
✅ Frontend: Public via LoadBalancer (port 8080)
✅ Backend Internal: ClusterIP (port 8000) - for UI
✅ Backend External: LoadBalancer (port 8000) - for external apps
✅ No mixed content issues
✅ Fast internal communication
✅ External API access available
```

---

## 🎯 **Quick Commands**

```bash
# Build and push images
cd /opt/mycode/trilogy/nexus-ui && docker build -t nexus-ui:latest . && docker push ECR_URL
cd /opt/mycode/trilogy/nexus-backend && docker build -t ai-job-engine:latest . && docker push ECR_URL

# Deploy
kubectl create namespace call-processing-prod
kubectl apply -f /opt/mycode/trilogy/nexus-deployer/kube-operator/examples/call-processing-complete.yaml

# Get URLs
kubectl get svc -n call-processing-prod

# Test
curl https://FRONTEND-LB:8080
curl http://BACKEND-LB:8000/api/v1/health
```

**You're now ready to deploy with dual backend access!** 🎉
