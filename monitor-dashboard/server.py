#!/usr/bin/env python3
"""
Lightweight SSE monitoring dashboard for parallel load test.
No external dependencies beyond 'requests'.

Usage:
    python3 monitor-dashboard/server.py --sets a,b,c,d --port 3002
"""

import argparse
import json
import time
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

PROM_URL = "http://localhost:9090"
METRICS_CACHE = {}
CACHE_LOCK = threading.Lock()


def query_prometheus_instant(query: str):
    """Query Prometheus instant API."""
    try:
        r = requests.get(f"{PROM_URL}/api/v1/query", params={"query": query}, timeout=3)
        if r.status_code == 200:
            result = r.json()
            if result.get("status") == "success" and result["data"]["result"]:
                return float(result["data"]["result"][0]["value"][1])
    except Exception:
        pass
    return 0.0


def collect_metrics(suffixes):
    """Background thread: poll Prometheus every 2s and cache results."""
    while True:
        data = {"ts": time.time(), "sets": {}}
        for s in suffixes:
            data["sets"][s] = {
                "rps_media": query_prometheus_instant(f'sum(sent_rps_media{{job="load-generator-{s}"}})'),
                "rps_content": query_prometheus_instant(f'sum(sent_rps_content{{job="load-generator-{s}"}})'),
                "cpu_media": query_prometheus_instant(f'sum(rate(container_cpu_usage_seconds_total{{container_label_com_docker_compose_service="media-service-{s}"}}[5s])) * 100'),
                "cpu_content": query_prometheus_instant(f'sum(rate(container_cpu_usage_seconds_total{{container_label_com_docker_compose_service="content-service-{s}"}}[5s])) * 100'),
                "ram_media": query_prometheus_instant(f'sum(container_memory_working_set_bytes{{container_label_com_docker_compose_service="media-service-{s}"}}) / 1024 / 1024'),
                "ram_content": query_prometheus_instant(f'sum(container_memory_working_set_bytes{{container_label_com_docker_compose_service="content-service-{s}"}}) / 1024 / 1024'),
                "latency_media": query_prometheus_instant(f'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{{job="media-service-{s}"}}[5s])) by (le)) * 1000'),
                "latency_content": query_prometheus_instant(f'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{{job="content-service-{s}"}}[5s])) by (le)) * 1000'),
            }
        with CACHE_LOCK:
            METRICS_CACHE["latest"] = data
        time.sleep(2)


HTML_PAGE = None  # loaded at startup


class Handler(BaseHTTPRequestHandler):
    suffixes = []

    def log_message(self, fmt, *args):
        pass  # suppress request logs

    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode())

        elif self.path == "/events":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                while True:
                    with CACHE_LOCK:
                        data = METRICS_CACHE.get("latest", {})
                    if data:
                        payload = f"data: {json.dumps(data)}\n\n"
                        self.wfile.write(payload.encode())
                        self.wfile.flush()
                    time.sleep(2)
            except (BrokenPipeError, ConnectionResetError):
                pass

        elif self.path == "/api/sets":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"sets": self.suffixes}).encode())

        else:
            self.send_response(404)
            self.end_headers()


def main():
    global HTML_PAGE

    parser = argparse.ArgumentParser(description="Lightweight SSE monitoring dashboard")
    parser.add_argument("--sets", type=str, default="a,b,c,d", help="Comma-separated set suffixes")
    parser.add_argument("--port", type=int, default=3002, help="Dashboard port (default: 3002)")
    parser.add_argument("--prom-url", type=str, default="http://localhost:9090", help="Prometheus URL")
    args = parser.parse_args()

    global PROM_URL
    PROM_URL = args.prom_url
    suffixes = args.sets.split(",")
    Handler.suffixes = suffixes

    # Load HTML
    html_path = Path(__file__).parent / "index.html"
    HTML_PAGE = html_path.read_text(encoding="utf-8")
    # Inject sets into HTML
    HTML_PAGE = HTML_PAGE.replace("__SETS__", json.dumps(suffixes))

    # Start metrics collector thread
    t = threading.Thread(target=collect_metrics, args=(suffixes,), daemon=True)
    t.start()

    server = HTTPServer(("0.0.0.0", args.port), Handler)
    print(f"🖥️  Dashboard running at http://0.0.0.0:{args.port}")
    print(f"📊 Monitoring sets: {', '.join(s.upper() for s in suffixes)}")
    print(f"📡 Prometheus: {PROM_URL}")
    server.serve_forever()


if __name__ == "__main__":
    main()
