
from flask import current_app, request
from prometheus_client import Counter, Histogram, start_http_server
import time


API_REQUESTS = Counter(
    'api_requests_total',
    'Total API requests',
    ['endpoint', 'method', 'status']
)

API_LATENCY = Histogram(
    'api_request_latency_seconds',
    'API request latency',
    ['endpoint']
)

AI_REQUESTS = Counter(
    'ai_requests_total',
    'Total AI API requests',
    ['model_type', 'status']
)

AI_LATENCY = Histogram(
    'ai_request_latency_seconds',
    'AI request processing latency',
    ['model_type']
)

def init_request_monitoring(app):
    @app.before_request
    def start_timer():
        request._start_time = time.time()

    @app.after_request
    def record_metrics(response):
        endpoint = request.endpoint or "unknown"
        method = request.method
        status = response.status_code

        API_REQUESTS.labels(endpoint, method, status).inc()

        duration = time.time() - getattr(request, "_start_time", time.time())
        API_LATENCY.labels(endpoint).observe(duration)

        return response

def monitor_ai_request(model_type):
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                response = func(*args, **kwargs)
                AI_REQUESTS.labels(model_type, 'success').inc()
                return response
            except Exception as e:
                AI_REQUESTS.labels(model_type, 'error').inc()
                raise e
            finally:
                duration = time.time() - start_time
                AI_LATENCY.labels(model_type).observe(duration)
        return wrapper
    return decorator

def start_metrics_server():
    
    if current_app.config.get('ENABLE_METRICS'):
        start_http_server(9100)
