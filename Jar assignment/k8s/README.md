# Kubernetes Manifests (k8s)

This folder contains all Kubernetes manifests for the backend platform. They are organized by **apply order** and by **component**. Apply with `-n staging` or `-n production` unless noted.

---

## Table of Contents

1. [Apply Order](#apply-order)
2. [Namespaces](#namespaces)
3. [RBAC (Identity & Access)](#rbac-identity--access)
4. [API Gateway](#api-gateway)
5. [Orders Service](#orders-service)
6. [Inventory Service](#inventory-service)
7. [Observability](#observability)

---

## Apply Order

Apply in this sequence (replace `<namespace>` with `staging` or `production`):

```bash
kubectl apply -f k8s/00-namespaces.yaml
kubectl apply -f k8s/01-rbac/ -n <namespace>
kubectl apply -f k8s/api-gateway/ -n <namespace>
kubectl apply -f k8s/orders-service/ -n <namespace>
kubectl apply -f k8s/inventory-service/ -n <namespace>
kubectl apply -f k8s/observability/ -n <namespace>
```

---

## Namespaces

| File | Description |
|------|-------------|
| **00-namespaces.yaml** | Defines **staging** and **production** namespaces. Apply once; no `-n` needed (resource defines its own namespace). |

Use these namespaces for all subsequent resources so you can run staging and production side by side.

---

## RBAC (Identity & Access)

**Folder:** `01-rbac/`  
**Apply:** `kubectl apply -f k8s/01-rbac/ -n <namespace>`

| File | Description |
|------|-------------|
| **serviceaccount-api-gateway.yaml** | Dedicated ServiceAccount for api-gateway pods (do not use default). |
| **serviceaccount-orders-service.yaml** | ServiceAccount for orders-service pods. |
| **serviceaccount-inventory-service.yaml** | ServiceAccount for inventory-service pods. |
| **role-service-discovery.yaml** | **Role** granting `get`, `list` on `services` and `endpoints` in the same namespace. **RoleBindings** attach this role to each of the three ServiceAccounts (minimal RBAC for service discovery). |

Each workload references its ServiceAccount in the Deployment `spec.serviceAccountName`.

---

## API Gateway

**Role:** External entry point. Exposed to the outside via Ingress; routes traffic to internal services.  
**Folder:** `api-gateway/`  
**Apply:** `kubectl apply -f k8s/api-gateway/ -n <namespace>`

| File | Resource | Description |
|------|----------|-------------|
| **deployment.yaml** | Deployment | 2 replicas; image `api-gateway:latest`; ServiceAccount `api-gateway`; **liveness** and **readiness** probes on `GET /health` (port 8080); **pod anti-affinity** (prefer spread across nodes); resource requests/limits. |
| **service.yaml** | Service (ClusterIP) | Port 80 → targetPort 8080; selector `app: api-gateway`. Ingress sends traffic to this Service; only **ready** pods receive traffic. |
| **ingress.yaml** | Ingress | nginx IngressController; host `localhost`, path `/` → backend `api-gateway:80`. Makes the gateway reachable at `http://localhost` when using kind. |
| **hpa.yaml** | HorizontalPodAutoscaler | Scales Deployment between **2–6** replicas when average CPU utilization is above 70%. Requires metrics-server. |
| **vpa.yaml** | VerticalPodAutoscaler | Recommends (or can auto-adjust) CPU/memory for the api-gateway container. `updateMode: Off` = recommendation only. Requires VPA components in the cluster. |
| **pdb.yaml** | PodDisruptionBudget | **minAvailable: 1** for pods with `app: api-gateway`. Ensures at least one replica during voluntary disruptions (e.g. node drain). |

**DNS (internal):** `api-gateway.<namespace>.svc.cluster.local`

---

## Orders Service

**Role:** Internal microservice. Not exposed via Ingress; used for order-related data.  
**Folder:** `orders-service/`  
**Apply:** `kubectl apply -f k8s/orders-service/ -n <namespace>`

| File | Resource | Description |
|------|----------|-------------|
| **deployment.yaml** | Deployment | 2 replicas; image `orders-service:latest`; ServiceAccount `orders-service`; liveness/readiness on `GET /health`; pod anti-affinity; resource requests/limits. |
| **service.yaml** | Service (ClusterIP) | Port 80 → 8080; selector `app: orders-service`. Used for service-to-service communication (e.g. api-gateway → orders-service). |
| **hpa.yaml** | HorizontalPodAutoscaler | **2–5** replicas by CPU (70% target). |
| **vpa.yaml** | VerticalPodAutoscaler | Resource recommendations for the orders-service container. |
| **pdb.yaml** | PodDisruptionBudget | **minAvailable: 1** for `app: orders-service`. |

**DNS (internal):** `orders-service.<namespace>.svc.cluster.local`

---

## Inventory Service

**Role:** Internal microservice. Not exposed via Ingress; used for inventory/stock data.  
**Folder:** `inventory-service/`  
**Apply:** `kubectl apply -f k8s/inventory-service/ -n <namespace>`

| File | Resource | Description |
|------|----------|-------------|
| **deployment.yaml** | Deployment | 2 replicas; image `inventory-service:latest`; ServiceAccount `inventory-service`; liveness/readiness on `GET /health`; pod anti-affinity; resource requests/limits. |
| **service.yaml** | Service (ClusterIP) | Port 80 → 8080; selector `app: inventory-service`. |
| **hpa.yaml** | HorizontalPodAutoscaler | **2–5** replicas by CPU (70% target). |
| **vpa.yaml** | VerticalPodAutoscaler | Resource recommendations for the inventory-service container. |
| **pdb.yaml** | PodDisruptionBudget | **minAvailable: 1** for `app: inventory-service`. |

**DNS (internal):** `inventory-service.<namespace>.svc.cluster.local`

---

## Observability

**Folder:** `observability/`  
**Apply:** `kubectl apply -f k8s/observability/ -n <namespace>`

| File | Resource | Description |
|------|----------|-------------|
| **prometheus-config.yaml** | ConfigMap | Prometheus scrape config: targets **api-gateway:80**, **orders-service:80**, **inventory-service:80** (each exposes `/metrics`). |
| **prometheus-deployment.yaml** | Deployment + Service | Prometheus server (image `prom/prometheus`); mounts config; port 9090; ClusterIP Service for querying. |
| **otel-collector-config.yaml** | ConfigMap | OpenTelemetry Collector config: OTLP receiver (gRPC 4317, HTTP 4318), batch processor, logging exporter (optional Tempo export in comments). |
| **otel-collector-deployment.yaml** | Deployment + Service | OTel Collector (image `otel/opentelemetry-collector-contrib`); receives traces for distributed tracing; ClusterIP Service on 4317 and 4318. |

Apply observability **after** the three application services are deployed so Prometheus can scrape their metrics. Health-check-related metrics are available from each service’s `/metrics` endpoint.
