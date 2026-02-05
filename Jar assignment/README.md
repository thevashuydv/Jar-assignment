# Kubernetes Backend Platform — DevOps Assignment

## Table of Contents

1. [Project Description](#project-description)
2. [Architecture Overview](#architecture-overview)
3. [Prerequisites](#prerequisites)
4. [Local Setup](#local-setup)
5. [Health Check Design](#health-check-design)
6. [Key Infrastructure Choices](#key-infrastructure-choices)
7. [Project Structure](#project-structure)
8. [CI/CD (Jenkins)](#cicd-jenkins)
9. [Running the Platform](#running-the-platform)
10. [Verification](#verification)

---

## Project Description

This repository implements a **local Kubernetes-based backend platform**. The goal is to demonstrate containerization, Kubernetes fundamentals, networking, scaling, availability, identity/access, observability, and CI/CD. 

The platform consists of three services:

| Service             | Role                  | Exposure        |
|---------------------|-----------------------|-----------------|
| **api-gateway**     | External entry point  | Ingress (HTTP)  |
| **orders-service**  | Internal microservice | ClusterIP       |
| **inventory-service** | Internal microservice | ClusterIP    |

Each service exposes:

- **GET /health** — Used for Kubernetes liveness and readiness probes.
- **Dummy API endpoint** — Returns a static JSON response.

Traffic flows: **Client → Ingress → api-gateway → orders-service / inventory-service** via Kubernetes DNS (ClusterIP). The setup runs on a local cluster created with **kind** (Kubernetes in Docker).

---

## Architecture Overview

```
                    ┌─────────────────────────────────────────┐
                    │              kind cluster                │
                    │  ┌─────────────────────────────────────┐│
                    │  │  Ingress Controller (nginx)         ││
                    │  └─────────────────┬───────────────────┘│
                    │                    │                     │
                    │  ┌─────────────────▼───────────────────┐│
                    │  │  api-gateway (Deployment + SA)      ││
                    │  └─────────────────┬───────────────────┘│
                    │                    │                     │
                    │     ┌──────────────┼──────────────┐     │
                    │     ▼              ▼              │     │
                    │  orders-service  inventory-service│     │
                    │  (ClusterIP)     (ClusterIP)     │     │
                    │     │              │              │     │
                    │  Prometheus ◄─────┴── metrics    │     │
                    │  OpenTelemetry (tracing)         │     │
                    └─────────────────────────────────────────┘
```

Namespaces used: **staging**, **production** (same manifests can be applied to both; examples use **staging** by default).



---

## Local Setup

### 1. Install kind (Kubernetes in Docker)

**macOS (Homebrew):**

```bash
brew install kind
```

**Linux (curl):**

```bash
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind
```


### 2. Create the kind cluster

From the repository root:

```bash
kind create cluster --name jar-cluster --config kind-config.yaml
```

This uses `kind-config.yaml` in the repo to define the cluster.

### 3. Install required cluster components

**Metrics Server (required for HPA):**

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

**Ingress controller (nginx):**

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
kubectl wait --namespace ingress-nginx --for=condition=ready pod --selector=app.kubernetes.io/component=controller --timeout=120s
```

**VPA (Vertical Pod Autoscaler) — optional but recommended for VPA step:**

```bash
# Add VPA repo and install
kubectl apply -f https://raw.githubusercontent.com/kubernetes/autoscaler/vertical-pod-autoscaler/master/deploy/vpa-v1-crd-gen.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes/autoscaler/vertical-pod-autoscaler/master/deploy/vpa-rbac.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes/autoscaler/vertical-pod-autoscaler/master/deploy/updater-deployment.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes/autoscaler/vertical-pod-autoscaler/master/deploy/recommender-deployment.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes/autoscaler/vertical-pod-autoscaler/master/deploy/admission-controller-deployment.yaml
```

### 4. Build and load Docker images into kind

```bash
# Build images
docker build -t api-gateway:latest ./services/api-gateway
docker build -t orders-service:latest ./services/orders-service
docker build -t inventory-service:latest ./services/inventory-service

# Load into kind (so the cluster can pull them)
kind load docker-image api-gateway:latest orders-service:latest inventory-service:latest --name jar-cluster
```

### 5. Deploy the application and observability

Apply manifests in order (namespaces first, then RBAC/SA, then workloads, then Ingress/Observability):

```bash
# Namespaces
kubectl apply -f k8s/00-namespaces.yaml

# Service accounts and RBAC (staging)
kubectl apply -f k8s/01-rbac/ -n staging

# Core workloads (staging)
kubectl apply -f k8s/api-gateway/ -n staging
kubectl apply -f k8s/orders-service/ -n staging
kubectl apply -f k8s/inventory-service/ -n staging

# Observability (optional, for Step 6)
kubectl apply -f k8s/observability/ -n staging
```

### 6. Access the API

- Ingress is typically available at `http://localhost` (kind often maps 80 → ingress).
- If not, use port-forward:  
  `kubectl port-forward -n ingress-nginx svc/ingress-nginx-controller 8080:80`
- Then:  
  - Health: `curl http://localhost:8080/health` (via api-gateway)  
  - Dummy: `curl http://localhost:8080/api/dummy`

---

## Health Check Design

- **Endpoint:** `GET /health`
- **Contract:** HTTP 200 with JSON body e.g. `{"status":"ok"}`. Non-200 or timeout → unhealthy.

**Kubernetes usage:**

- **Liveness probe** — Restarts the container if the process is stuck (no successful `/health` within the threshold).
- **Readiness probe** — Removes the pod from Service endpoints if the app is not ready to serve (e.g. during startup or overload). Ingress and other services should only send traffic to ready pods.

**Implementation:** Each service (api-gateway, orders-service, inventory-service) implements `GET /health` and returns 200 + JSON. Probes in Deployment manifests use `httpGet` on `/health` with appropriate `initialDelaySeconds` and `periodSeconds` so that startup and failures are detected without excessive load.

---

## Key Infrastructure Choices

| Area | Choice | Rationale |
|------|--------|-----------|
| **Local cluster** | kind | Lightweight, Docker-based, good for CI and local dev; easy to script. |
| **Ingress** | nginx Ingress Controller | Widely used, works well with kind; respects Service readiness. |
| **Service discovery** | Kubernetes DNS (ClusterIP) | Internal services reach each other by `<service>.<namespace>.svc.cluster.local`. |
| **Scaling** | HPA (CPU) + VPA (recommendation) | HPA for replica count; VPA for resource recommendations/autopilot. |
| **Availability** | PDB + pod anti-affinity | PDB prevents too many pods from being evicted at once; anti-affinity spreads pods across nodes where possible. |
| **Identity** | Dedicated ServiceAccount per service | No default SA; least-privilege RBAC per service. |
| **Observability** | Prometheus + OpenTelemetry | Prometheus for metrics (including health); OpenTelemetry for distributed tracing. |
| **CI/CD** | Jenkins | Pipeline builds Docker images and deploys manifests to Kubernetes (cluster and tools assumed pre-configured). |

---

## Project Structure

```
.
├── README.md
├── kind-config.yaml              # kind cluster definition
├── services/                     # Application source and Dockerfiles
│   ├── api-gateway/
│   │   ├── Dockerfile
│   │   ├── app.py
│   │   └── requirements.txt
│   ├── orders-service/
│   │   ├── Dockerfile
│   │   ├── app.py
│   │   └── requirements.txt
│   └── inventory-service/
│       ├── Dockerfile
│       ├── app.py
│       └── requirements.txt
├── k8s/                          # Kubernetes manifests (with comments)
│   ├── 00-namespaces.yaml
│   ├── 01-rbac/                  # ServiceAccounts and RoleBindings
│   ├── api-gateway/              # Deployment, Service, Ingress, HPA, VPA, PDB
│   ├── orders-service/
│   ├── inventory-service/
│   └── observability/            # Prometheus config + deployment; OpenTelemetry Collector for tracing
└── Jenkinsfile                  # CI/CD: build images, deploy manifests
```


---

## CI/CD (Jenkins)

The pipeline does **only** what the assignment specifies for Step 7:

1. **Build Docker images** — api-gateway, orders-service, inventory-service (tagged as `latest`).
2. **Deploy manifests to Kubernetes** — Applies namespaces, RBAC, then each service and observability in order to the target namespace (default: `staging`).

**Prerequisites:** Jenkins with Docker and `kubectl` available on the agent; `kubeconfig` configured so `kubectl` can reach your cluster. No cluster creation or add-on installation (Metrics Server, Ingress, etc.) is done in the pipeline—set up the cluster and tools separately.

- Pipeline file: **`Jenkinsfile`** (in repo root).
- To deploy to production: set the pipeline environment variable `K8S_NAMESPACE = 'production'` or use a parameter.

---

To tear down:

```bash
kind delete cluster --name jar-cluster
```

---

## Verification

- **Pods:** `kubectl get pods -n staging`
- **Services:** `kubectl get svc -n staging`
- **Ingress:** `kubectl get ingress -n staging`
- **Health:** `curl http://localhost/health` or `curl http://localhost:8080/health`
- **Metrics:** Prometheus targets and dashboards if observability is deployed.

---

