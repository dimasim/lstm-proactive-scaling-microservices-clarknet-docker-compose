#!/usr/bin/env python3
"""
Generate docker-compose.yml and prometheus.yml for N parallel microservice sets.

Usage:
    python3 generate_compose.py --sets 4 --server-id 1 --port-start 8000 --exporter-port-start 8011
    python3 generate_compose.py --sets 4 --server-id 2 --port-start 8000 --exporter-port-start 8011

This generates:
    - docker-compose-server{N}.yml
    - prometheus/prometheus-server{N}.yml
"""

import argparse
import string

def get_suffix(index):
    """Get alphabetic suffix: 0->a, 1->b, ..., 25->z"""
    return string.ascii_lowercase[index]

def generate_docker_compose(num_sets, server_id, port_start, suffix_offset=0):
    """Generate docker-compose YAML content for N parallel sets."""
    
    services = []
    
    # Generate HAProxy + microservice pairs for each set
    for i in range(num_sets):
        suffix = get_suffix(suffix_offset + i)
        port = port_start + i
        
        services.append(f"""  haproxy-{suffix}:
    image: haproxy:2.8-alpine
    container_name: haproxy-{suffix}
    ports:
      - "{port}:80"
    volumes:
      - ./haproxy/haproxy-{suffix}.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro
    depends_on:
      - media-service-{suffix}
      - content-service-{suffix}

  media-service-{suffix}:
    build:
      context: ./media-service
    image: media-service:latest
    container_name: media-service-{suffix}

  content-service-{suffix}:
    build:
      context: ./content-service
    image: content-service:latest
    container_name: content-service-{suffix}""")
    
    # Infrastructure services
    infra = """  cadvisor:
    image: ghcr.io/google/cadvisor:latest
    container_name: cadvisor
    privileged: true
    devices:
      - "/dev/kmsg:/dev/kmsg"
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /sys/fs/cgroup:/sys/fs/cgroup:ro
      - /var/lib/docker/:/rootfs/var/lib/docker:ro
      - /dev/disk/:/dev/disk:ro
    command:
      - '--housekeeping_interval=1s'
      - '--max_housekeeping_interval=1s'
      - '--docker_only=true'

  prometheus:
    image: prom/prometheus:v2.45.0
    container_name: prometheus
    volumes:
      - ./prometheus/prometheus-server{server_id}.yml:/etc/prometheus/prometheus.yml:ro
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=3d'
    ports:
      - "9090:9090"
    depends_on:
      - cadvisor"""
    
    # Add haproxy dependencies to prometheus
    haproxy_depends = "\n".join(
        [f"      - haproxy-{get_suffix(suffix_offset + i)}" for i in range(num_sets)]
    )
    infra += f"\n{haproxy_depends}"
    
    
    # Get the suffixes for this server's sets
    set_suffixes = [get_suffix(suffix_offset + i) for i in range(num_sets)]
    sets_arg = ",".join(set_suffixes)
    
    infra += f"""

  monitor-dashboard:
    build:
      context: ./monitor-dashboard
    container_name: monitor-dashboard
    ports:
      - "3002:3002"
    command: ["--sets", "{sets_arg}", "--prom-url", "http://prometheus:9090", "--port", "3002"]
    depends_on:
      - prometheus"""
    
    # Format server_id into infra string
    infra = infra.replace("{server_id}", str(server_id))
    
    content = f"""version: '3.8'

services:
{chr(10).join(services)}

{infra}
"""
    return content

def generate_prometheus_config(num_sets, exporter_port_start, suffix_offset=0):
    """Generate prometheus.yml content for N parallel sets."""
    
    scrape_configs = """global:
  scrape_interval: 1s
  evaluation_interval: 1s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']
"""
    
    for i in range(num_sets):
        suffix = get_suffix(suffix_offset + i)
        exporter_port = exporter_port_start + i
        
        scrape_configs += f"""
  - job_name: 'haproxy-{suffix}'
    static_configs:
      - targets: ['haproxy-{suffix}:8404']

  - job_name: 'media-service-{suffix}'
    static_configs:
      - targets: ['media-service-{suffix}:8000']

  - job_name: 'content-service-{suffix}'
    static_configs:
      - targets: ['content-service-{suffix}:8000']

  - job_name: 'load-generator-{suffix}'
    static_configs:
      - targets: ['172.17.0.1:{exporter_port}']
"""
    
    return scrape_configs

def generate_haproxy_config(suffix):
    """Generate HAProxy config for a specific set."""
    return f"""global
    maxconn 256

defaults
    mode http
    timeout connect 5000ms
    timeout client 50000ms
    timeout server 50000ms

frontend http_front
    bind *:80
    acl is_media path_beg /media
    acl is_content path_beg /content
    use_backend media_backend if is_media
    use_backend content_backend if is_content

backend media_backend
    server media1 media-service-{suffix}:8000

backend content_backend
    server content1 content-service-{suffix}:8000

frontend stats
    bind *:8404
    stats enable
    stats uri /stats
    stats refresh 1s
"""

def main():
    parser = argparse.ArgumentParser(description="Generate docker-compose and prometheus config for N parallel sets")
    parser.add_argument("--sets", type=int, required=True, help="Number of parallel sets per server")
    parser.add_argument("--server-id", type=int, required=True, help="Server identifier (1 or 2)")
    parser.add_argument("--port-start", type=int, default=8000, help="Starting port for HAProxy (default: 8000)")
    parser.add_argument("--exporter-port-start", type=int, default=8011, help="Starting port for Prometheus exporters (default: 8011)")
    parser.add_argument("--suffix-offset", type=int, default=0, help="Offset for suffix naming (0=a, 4=e for server 2)")
    parser.add_argument("--output-dir", type=str, default=".", help="Output directory")
    args = parser.parse_args()
    
    # Generate docker-compose
    compose_content = generate_docker_compose(
        args.sets, args.server_id, args.port_start, args.suffix_offset
    )
    compose_file = f"{args.output_dir}/docker-compose-server{args.server_id}.yml"
    with open(compose_file, "w") as f:
        f.write(compose_content)
    print(f"✅ Generated {compose_file}")
    
    # Generate prometheus config
    prom_content = generate_prometheus_config(
        args.sets, args.exporter_port_start, args.suffix_offset
    )
    prom_file = f"{args.output_dir}/prometheus/prometheus-server{args.server_id}.yml"
    with open(prom_file, "w") as f:
        f.write(prom_content)
    print(f"✅ Generated {prom_file}")
    
    # Generate HAProxy configs
    for i in range(args.sets):
        suffix = get_suffix(args.suffix_offset + i)
        haproxy_content = generate_haproxy_config(suffix)
        haproxy_file = f"{args.output_dir}/haproxy/haproxy-{suffix}.cfg"
        with open(haproxy_file, "w") as f:
            f.write(haproxy_content)
        print(f"✅ Generated {haproxy_file}")
    
    print(f"\n📋 Usage:")
    print(f"  docker compose -f {compose_file} up -d")
    print(f"  python3 skrip-percobaan/run_parallel_k6.py <duration> --sets {','.join(get_suffix(args.suffix_offset + i) for i in range(args.sets))}")

if __name__ == "__main__":
    main()
