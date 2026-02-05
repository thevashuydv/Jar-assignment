"""
Inventory Service - Internal microservice.
Exposes /health, /metrics, and a dummy /api/inventory endpoint.
"""
import os
from flask import Flask, jsonify
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Histogram

app = Flask(__name__)

REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "Request latency", ["endpoint"])


@app.route("/health")
def health():
    """Liveness and readiness."""
    return jsonify({"status": "ok", "service": "inventory-service"}), 200


@app.route("/metrics")
def metrics():
    """Prometheus-compatible metrics."""
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


@app.route("/api/inventory")
@REQUEST_LATENCY.labels(endpoint="/api/inventory").time()
def inventory():
    REQUEST_COUNT.labels(method="GET", endpoint="/api/inventory").inc()
    return jsonify({
        "service": "inventory-service",
        "items": [{"sku": "WIDGET-01", "stock": 100}],
    }), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
