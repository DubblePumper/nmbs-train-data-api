"""
Monitoring systeem voor de NMBS Train Data API met Prometheus metrics
"""
import time
import logging
from flask import request, g
from prometheus_client import Counter, Histogram, Gauge, Summary

logger = logging.getLogger(__name__)

# Metrics definities
# HTTP request metrics
REQUEST_COUNT = Counter(
    'nmbs_api_http_requests_total', 
    'Totaal aantal HTTP verzoeken', 
    ['method', 'endpoint', 'status_code']
)

REQUEST_LATENCY = Histogram(
    'nmbs_api_http_request_duration_seconds', 
    'HTTP verzoek duur in seconden',
    ['method', 'endpoint']
)

# Rate limiting metrics
RATE_LIMIT_HIT = Counter(
    'nmbs_api_rate_limit_hits_total',
    'Aantal keer dat rate limiting is toegepast',
    ['endpoint']
)

# Data metrics
RECORDS_COUNT = Gauge(
    'nmbs_api_records_count',
    'Aantal records per datatype',
    ['data_type']
)

DATA_UPDATE_TIMES = Summary(
    'nmbs_api_data_update_seconds',
    'Tijd nodig om data te updaten',
    ['data_type']
)

LAST_UPDATE_TIME = Gauge(
    'nmbs_api_last_update_timestamp',
    'Timestamp van laatste data update',
    ['data_type']
)

# Error metrics
ERROR_COUNT = Counter(
    'nmbs_api_errors_total',
    'Totaal aantal errors',
    ['endpoint', 'error_type']
)

def register_metrics_endpoint(app):
    """
    Registreer een /metrics endpoint voor Prometheus
    
    Args:
        app: De Flask applicatie
    """
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from flask import Response
    
    @app.route('/metrics')
    def metrics():
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

def setup_request_monitoring(app):
    """
    Stel request monitoring in
    
    Args:
        app: De Flask applicatie
    """
    @app.before_request
    def before_request():
        g.start_time = time.time()
    
    @app.after_request
    def after_request(response):
        # Skip monitoring for metrics endpoint
        if request.path == '/metrics':
            return response
        
        # Record request latency
        latency = time.time() - g.start_time
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.path
        ).observe(latency)
        
        # Record request count
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.path,
            status_code=response.status_code
        ).inc()
        
        # Log lange verzoeken (meer dan 1 seconde)
        if latency > 1:
            logger.warning(f"Lang verzoek: {request.method} {request.path} duurde {latency:.2f}s")
            
        # Log fouten
        if response.status_code >= 400:
            ERROR_COUNT.labels(
                endpoint=request.path,
                error_type=f"HTTP_{response.status_code}"
            ).inc()
            logger.warning(f"Fout {response.status_code}: {request.method} {request.path}")
            
        return response

def record_data_update(data_type, records_count, update_time_seconds):
    """
    Registreer een data update in metrics
    
    Args:
        data_type: Type van de data (bijv. 'realtime', 'stops', etc.)
        records_count: Aantal records in de data
        update_time_seconds: Tijd die de update kostte in seconden
    """
    RECORDS_COUNT.labels(data_type=data_type).set(records_count)
    DATA_UPDATE_TIMES.labels(data_type=data_type).observe(update_time_seconds)
    LAST_UPDATE_TIME.labels(data_type=data_type).set(time.time())
    logger.info(f"Data update voor {data_type}: {records_count} records in {update_time_seconds:.2f}s")

def record_rate_limit_hit(endpoint):
    """
    Registreer een rate limit hit
    
    Args:
        endpoint: Het endpoint dat de rate limit heeft bereikt
    """
    RATE_LIMIT_HIT.labels(endpoint=endpoint).inc()
    logger.warning(f"Rate limit bereikt voor {endpoint}")

def record_error(endpoint, error_type, message=None):
    """
    Registreer een fout
    
    Args:
        endpoint: Het endpoint waar de fout optrad
        error_type: Type fout (bijv. 'ValidationError', 'DatabaseError')
        message: Optioneel foutbericht
    """
    ERROR_COUNT.labels(endpoint=endpoint, error_type=error_type).inc()
    log_msg = f"Fout in {endpoint}: {error_type}"
    if message:
        log_msg += f" - {message}"
    logger.error(log_msg)