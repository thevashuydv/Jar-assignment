# Services

This folder contains the source code and Dockerfiles for the three microservices that make up the Kubernetes backend platform. Each service is a small Flask (Python) application with health checks, a dummy API endpoint, and Prometheus metrics.

---

## Table of Contents

1. [API Gateway](#api-gateway)
2. [Orders Service](#orders-service)
3. [Inventory Service](#inventory-service)
4. [Building and Running Locally](#building-and-running-locally)

---

## API Gateway

**Role:** External entry point. All traffic from outside the cluster (via Ingress) hits this service first.

| Detail | Description |
|--------|-------------|
| **Exposure** | External (Ingress) |
| **Technology** | Python 3.11, Flask, Gunicorn |
| **Port** | 8080 (container) |
| **Service Account** | `api-gateway` (Kubernetes) |

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness and readiness; returns `{"status":"ok","service":"api-gateway"}`. Used by Kubernetes probes. |
| `GET` | `/metrics` | Prometheus-compatible metrics (request count, latency). |
| `GET` | `/api/dummy` | Dummy API; returns static JSON (service name, welcome message, version). |

### Files

| File | Purpose |
|------|---------|
| `app.py` | Flask app: routes for `/health`, `/metrics`, `/api/dummy`; Prometheus counters and histograms. |
| `requirements.txt` | Dependencies: Flask, Gunicorn, prometheus-client, requests. |
| `Dockerfile` | Multi-stage not used; Python 3.11-slim, non-root user, Gunicorn with 2 workers. |

### Run locally (outside Kubernetes)

```bash
cd services/api-gateway
pip install -r requirements.txt
python app.py
# Or: gunicorn -b 0.0.0.0:8080 -w 2 app:app
```

```bash
curl http://localhost:8080/health
curl http://localhost:8080/api/dummy
```

---

## Orders Service

**Role:** Internal microservice. Handles order-related data; reachable only from inside the cluster (e.g. by api-gateway or other services) via Kubernetes DNS.

| Detail | Description |
|--------|-------------|
| **Exposure** | Internal (ClusterIP) |
| **Technology** | Python 3.11, Flask, Gunicorn |
| **Port** | 8080 (container) |
| **Service Account** | `orders-service` (Kubernetes) |
| **DNS (in cluster)** | `orders-service.<namespace>.svc.cluster.local` |

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness and readiness; returns `{"status":"ok","service":"orders-service"}`. |
| `GET` | `/metrics` | Prometheus-compatible metrics. |
| `GET` | `/api/orders` | Dummy API; returns static JSON with a sample order list (e.g. id, item, quantity). |

### Files

| File | Purpose |
|------|---------|
| `app.py` | Flask app: `/health`, `/metrics`, `/api/orders`; request count and latency metrics. |
| `requirements.txt` | Flask, Gunicorn, prometheus-client. |
| `Dockerfile` | Same pattern as api-gateway: Python 3.11-slim, non-root user, Gunicorn. |

### Run locally (outside Kubernetes)

```bash
cd services/orders-service
pip install -r requirements.txt
python app.py
```

```bash
curl http://localhost:8080/health
curl http://localhost:8080/api/orders
```

---

## Inventory Service

**Role:** Internal microservice. Handles inventory/stock data; reachable only from inside the cluster via Kubernetes DNS.

| Detail | Description |
|--------|-------------|
| **Exposure** | Internal (ClusterIP) |
| **Technology** | Python 3.11, Flask, Gunicorn |
| **Port** | 8080 (container) |
| **Service Account** | `inventory-service` (Kubernetes) |
| **DNS (in cluster)** | `inventory-service.<namespace>.svc.cluster.local` |

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness and readiness; returns `{"status":"ok","service":"inventory-service"}`. |
| `GET` | `/metrics` | Prometheus-compatible metrics. |
| `GET` | `/api/inventory` | Dummy API; returns static JSON with sample inventory items (e.g. sku, stock). |

### Files

| File | Purpose |
|------|---------|
| `app.py` | Flask app: `/health`, `/metrics`, `/api/inventory`; request count and latency metrics. |
| `requirements.txt` | Flask, Gunicorn, prometheus-client. |
| `Dockerfile` | Same pattern as api-gateway and orders-service. |

### Run locally (outside Kubernetes)

```bash
cd services/inventory-service
pip install -r requirements.txt
python app.py
```

```bash
curl http://localhost:8080/health
curl http://localhost:8080/api/inventory
```

---

## Building and Running Locally

### Build all Docker images (from repo root)

```bash
docker build -t api-gateway:latest ./services/api-gateway
docker build -t orders-service:latest ./services/orders-service
docker build -t inventory-service:latest ./services/inventory-service
```

### Load images into kind (after creating cluster)

```bash
kind load docker-image api-gateway:latest orders-service:latest inventory-service:latest --name jar-cluster
```

All three services follow the same structure: **Flask app** with **Gunicorn**, **GET /health** for probes, **GET /metrics** for Prometheus, and **one dummy GET API** returning static JSON. Application behavior is not evaluated; the focus is on containerization and Kubernetes integration.
