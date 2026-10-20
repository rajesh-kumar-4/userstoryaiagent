"""OpenTelemetry bootstrap. Spans are no-ops until telemetry is enabled."""

from opentelemetry import trace

TRACER_NAME = "userstoryai.platform"
_configured = False


def configure_telemetry(settings) -> bool:
    """Install an SDK tracer provider when `telemetry_enabled` is set. Idempotent.

    With `otel_exporter_otlp_endpoint` set, spans are exported over OTLP/HTTP
    (the endpoint must be the full traces URL, for example http://otel:4318/v1/traces).
    Without it, spans are written to the console for local development.
    """
    global _configured
    if not settings.telemetry_enabled or _configured:
        return _configured

    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

    provider = TracerProvider(resource=Resource.create({"service.name": settings.otel_service_name}))
    if settings.otel_exporter_otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
    else:
        exporter = ConsoleSpanExporter()
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _configured = True
    return True


def get_tracer() -> trace.Tracer:
    return trace.get_tracer(TRACER_NAME)
