"""
API Gateway - External entry point.
Exposes /health, /metrics, and a dummy /api/dummy endpoint.
Optionally proxies to orders-service and inventory-service (internal).
"""
import os
from flask import Flask, jsonify
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Histogram

app = Flask(__name__)

# Prometheus metrics for observability
REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "Request latency", ["endpoint"])


@app.route("/health")
def health():
    """Liveness and readiness: return 200 with status ok."""
    return jsonify({"status": "ok", "service": "api-gateway"}), 200


@app.route("/metrics")
def metrics():
    """Prometheus-compatible metrics."""
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


@app.route("/api/dummy")
@REQUEST_LATENCY.labels(endpoint="/api/dummy").time()
def dummy():
    REQUEST_COUNT.labels(method="GET", endpoint="/api/dummy").inc()
    # Static response as per assignment (application behavior not evaluated)
    return jsonify({
        "service": "api-gateway",
        "message": "Welcome to the API Gateway",
        "version": "1.0",
    }), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
