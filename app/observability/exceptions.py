"""Exception hierarchy for the Observability & Developer Console Subsystem."""

from app.core.exceptions import JarvisError


class ObservabilityError(JarvisError):
    """Base exception class for observability errors."""
    pass


class MetricsError(ObservabilityError):
    """Raised when metrics recording or aggregation fails."""
    pass


class TracingError(ObservabilityError):
    """Raised when span tracing or context propagation fails."""
    pass


class ExporterError(ObservabilityError):
    """Raised when telemetry export generation fails."""
    pass


class DashboardError(ObservabilityError):
    """Raised when health dashboard compilation fails."""
    pass
