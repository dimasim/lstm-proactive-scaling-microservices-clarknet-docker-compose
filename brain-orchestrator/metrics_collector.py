import os
import time
import requests
import logging

PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL", "http://prometheus:9090")

def query_prometheus(query):
    try:
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={'query': query}, timeout=1)
        response.raise_for_status()
        data = response.json()
        
        result = data.get('data', {}).get('result', [])
        if not result:
            return 0.0
            
        value = result[0].get('value', [])
        if len(value) >= 2:
            return float(value[1])
            
        return 0.0
    except Exception as e:
        logging.error(f"Failed to query prometheus for {query}: {e}")
        return 0.0

def get_current_metrics():
    """
    Returns the current RPS for content and media services.
    """
    rps_content = query_prometheus('sum(sent_rps_content)')
    rps_media = query_prometheus('sum(sent_rps_media)')
    
    return {
        'rps_content': rps_content,
        'rps_media': rps_media
    }
