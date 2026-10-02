# nginx Proxy Setup for Backend API Access

## Overview

This configuration enables the frontend to communicate with the backend API while:
- ✅ Avoiding mixed content issues (HTTPS → HTTP)
- ✅ Keeping backend private via internal service
- ✅ Exposing backend API externally for other applications
- ✅ Using fast internal Kubernetes networking

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                    │
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Frontend Pod (nginx)                           │    │
│  │                                                  │    │
│  │  Browser → HTTPS frontend:8080/api/v1/jobs     │    │
│  │              ↓                                   │    │
│  │         nginx proxy_pass                        │    │
│  │              ↓                                   │    │
│  │  HTTP backend-internal:8000/api/v1/jobs ────────┼───→│
│  └─────────────────────────────────────────────────┘    │
│                                                      ↓    │
│                                    ┌─────────────────────┤
│                                    │ Backend Pods        │
│                                    │ (3 replicas)        │
│                                    │ Port: 8000          │
│                                    └─────────────────────┤
│                                                      ↑    │
│  ┌───────────────────────────────────────────────────────┤
│  │  External LoadBalancer                           │    │
│  │  abc123.elb.amazonaws.com:8000                  │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
             ↑
             │ External Applications
```

**Key Points:**
- Frontend nginx proxies to **internal ClusterIP service** (fast, private)
- External apps use **LoadBalancer service** (public, same pods)
- Both services route to the **same backend pods**
- No dual deployment, just dual access paths

---

## 📝 **Files Modified**

### 1. nginx.conf

**Location:** `/opt/mycode/trilogy/nexus-ui/nginx.conf`

**Added proxy configuration:**
```nginx
location /api/ {
    proxy_pass http://call-processing-prod-backend-svc-internal:8000;
    # ... proxy headers and settings
}
```

**What it does:**
- Intercepts all `/api/*` requests from browser
- Forwards to internal backend service via HTTP
- Browser only sees HTTPS (no mixed content)
- Fast internal Kubernetes networking

### 2. config.json

**Location:** `/opt/mycode/trilogy/nexus-ui/public/config.json`

**Changed:**
```json
{
  "api": {
    "baseUrl": "",  // Empty = use nginx proxy (same origin)
    "timeout": 30000
  }
}
```

**What it does:**
- Empty baseUrl means relative URLs
- `fetch('/api/v1/jobs')` goes to same origin
- nginx intercepts and proxies to backend

---

## 🔧 **Kubernetes Services Setup**

### Service 1: Internal (ClusterIP)

**File:** `kube-operator/examples/dual-service-backend.yaml`

```yaml
apiVersion: v1
kind: Service
metadata:
  name: call-processing-prod-backend-svc-internal
  namespace: call-processing-prod
spec:
  type: ClusterIP  # Internal only
  selector:
    app: call-processing-prod-backend
  ports:
    - port: 8000
      targetPort: 8000
```

**Purpose:** Fast internal communication for UI

**DNS:** `call-processing-prod-backend-svc-internal.call-processing-prod.svc.cluster.local:8000`

**Short form:** `call-processing-prod-backend-svc-internal:8000`

### Service 2: External (LoadBalancer)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: call-processing-prod-backend-svc-external
  namespace: call-processing-prod
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
    service.beta.kubernetes.io/aws-load-balancer-scheme: "internet-facing"
spec:
  type: LoadBalancer
  selector:
    app: call-processing-prod-backend  # Same pods!
  ports:
    - port: 8000
      targetPort: 8000
```

**Purpose:** Public API access for external applications

**URL:** `http://abc123-xyz.elb.amazonaws.com:8000`

---

## 🚀 **Deployment Steps**

### Step 1: Update Operator (Optional)

Currently, the operator creates one LoadBalancer service. You can either:

**Option A:** Modify operator to create ClusterIP by default (requires code change)

**Option B:** Let operator create LoadBalancer, then create ClusterIP manually

### Step 2: Deploy TotogiCapability

```bash
kubectl create namespace call-processing-prod
kubectl apply -f examples/call-processing.yaml
```

**This creates:**
- Backend pods
- One service (LoadBalancer by default from operator)

### Step 3: Create Internal ClusterIP Service

```bash
kubectl apply -f examples/dual-service-backend.yaml
```

**This creates:**
- Internal ClusterIP service
- Additional external LoadBalancer service (or rename existing one)

### Step 4: Update Frontend to Use Proxy

**Already done:**
- ✅ nginx.conf updated with proxy_pass
- ✅ config.json updated with empty baseUrl

### Step 5: Rebuild and Deploy Frontend

```bash
cd /opt/mycode/trilogy/nexus-ui

# Build new image with updated nginx.conf
./build.sh

# Or manually
docker build -t nexus-ui:latest .

# Tag and push to ECR
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
docker tag nexus-ui:latest ${ACCOUNT_ID}.dkr.ecr.ap-southeast-1.amazonaws.com/nexus-ui:latest
aws ecr get-login-password --region ap-southeast-1 | docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.ap-southeast-1.amazonaws.com
docker push ${ACCOUNT_ID}.dkr.ecr.ap-southeast-1.amazonaws.com/nexus-ui:latest
```

### Step 6: Restart Frontend Pods

```bash
kubectl rollout restart deployment/call-processing-prod-frontend -n call-processing-prod
```

---

## ✅ **Verification**

### Test Internal Communication (UI → Backend)

```bash
# Get frontend pod name
FRONTEND_POD=$(kubectl get pods -n call-processing-prod -o name | grep frontend | head -1 | cut -d'/' -f2)

# Test API call through nginx proxy
kubectl exec -n call-processing-prod "$FRONTEND_POD" -- wget -O- http://localhost:8080/api/v1/health
```

**Expected:** Backend response (proxied through nginx)

### Test External API Access

```bash
# Get external LoadBalancer URL
EXTERNAL_URL=$(kubectl get svc call-processing-prod-backend-svc-external -n call-processing-prod -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# Test from outside cluster
curl http://$EXTERNAL_URL:8000/api/v1/health
```

**Expected:** Direct backend response

### Check Services

```bash
kubectl get svc -n call-processing-prod

# Should show:
# call-processing-prod-backend-svc-internal   ClusterIP      172.20.x.x
# call-processing-prod-backend-svc-external   LoadBalancer   abc.elb.amazonaws.com
# call-processing-prod-frontend-svc           LoadBalancer   xyz.elb.amazonaws.com
```

---

## 🔍 **How Requests Flow**

### Internal Request (UI)

```
1. Browser: https://frontend-lb:8080/api/v1/jobs
2. nginx receives: GET /api/v1/jobs
3. nginx matches: location /api/
4. nginx proxy_pass: http://backend-internal:8000/api/v1/jobs
5. Kubernetes DNS: backend-internal → Backend pod IP
6. Backend processes request
7. Backend returns response
8. nginx returns to browser
9. Browser receives: HTTPS response (doesn't see HTTP backend)
```

**Performance:** ~5-10ms internal latency

### External Request (External Apps)

```
1. External app: http://abc123.elb.amazonaws.com:8000/api/v1/jobs
2. AWS LoadBalancer receives request
3. LoadBalancer routes to Backend pod
4. Backend processes request
5. Backend returns response
6. LoadBalancer returns to external app
```

**Performance:** ~50-100ms (depends on external app location)

---

## 🔒 **Security Configuration**

### For External LoadBalancer

**Restrict by IP (if possible):**
```yaml
annotations:
  service.beta.kubernetes.io/aws-load-balancer-source-ranges: "203.0.113.0/24"
```

**Add API authentication in backend:**
```python
# FastAPI example
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key not in valid_api_keys:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

@app.get("/api/v1/jobs")
async def get_jobs(api_key: str = Security(verify_api_key)):
    # Only executes if API key is valid
    return jobs
```

**Add rate limiting:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/v1/jobs")
@limiter.limit("100/minute")  # Max 100 requests per minute
async def get_jobs():
    return jobs
```

### For Internal Service

No authentication needed if:
- Only accessible from within cluster
- Network policies restrict access
- Trust all pods in cluster

---

## 📊 **Benefits of This Setup**

| Aspect | Internal Service | External Service |
|--------|------------------|------------------|
| **Performance** | ⚡⚡⚡ 5-10ms | ⚡ 50-100ms |
| **Cost** | 💰 Free | 💰💰 LB + data transfer |
| **Security** | 🔒🔒🔒 Private | 🔒 Public (needs auth) |
| **Use case** | UI communication | External integrations |
| **DNS** | K8s internal DNS | AWS LoadBalancer DNS |
| **Protocol** | HTTP (safe internally) | HTTP/HTTPS (public) |

---

## 🎯 **Configuration Summary**

### Frontend (UI)

- **Port:** 8080
- **API calls:** Relative URLs (`/api/v1/jobs`)
- **nginx proxy:** Forwards to `backend-internal:8000`
- **Browser sees:** HTTPS only (no mixed content)

### Backend (Internal Service)

- **Type:** ClusterIP
- **DNS:** `call-processing-prod-backend-svc-internal:8000`
- **Access:** Cluster-internal only
- **Used by:** Frontend UI

### Backend (External Service)

- **Type:** LoadBalancer
- **URL:** `http://abc123.elb.amazonaws.com:8000`
- **Access:** Public internet
- **Used by:** External applications

---

## 🧪 **Testing After Deployment**

### Test 1: Frontend → Backend (via nginx proxy)

```bash
# From your browser, open frontend
https://YOUR-FRONTEND-URL:8080

# Open browser DevTools → Network tab
# Make API call from UI
# Check request URL: Should be /api/v1/... (relative)
# Check response: Should succeed
```

### Test 2: External App → Backend (via LoadBalancer)

```bash
# Get external backend URL
kubectl get svc call-processing-prod-backend-svc-external -n call-processing-prod

# Test from external client
curl http://EXTERNAL-LB-URL:8000/api/v1/health
```

### Test 3: Verify Internal is Faster

```bash
# From inside a pod
kubectl exec -n call-processing-prod FRONTEND_POD -- time wget -O- http://backend-internal:8000/api/v1/health

# Vs external
kubectl exec -n call-processing-prod FRONTEND_POD -- time wget -O- http://EXTERNAL-LB:8000/api/v1/health

# Internal should be ~10x faster
```

---

## 🔄 **Next Steps**

1. **Rebuild frontend image** with updated nginx.conf
2. **Push to ECR**
3. **Deploy dual-service-backend.yaml** to create both services
4. **Restart frontend pods** to use new nginx config
5. **Test both access paths**

---

## 📚 **Related Documentation**

- See `dual-service-backend.yaml` for service definitions
- Frontend calls will use `/api/` prefix (nginx proxy)
- External apps use full LoadBalancer URL
- Both access same backend pods (no duplication)
