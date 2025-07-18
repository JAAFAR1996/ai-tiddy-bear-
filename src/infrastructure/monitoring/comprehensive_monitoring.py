from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
import hashlib
import threading
import time

from src.infrastructure.logging_config import get_logger

logger = get_logger(__name__, component="monitoring")


class AlertSeverity(Enum):
    """Alert severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"  # For child safety incidents


class MetricType(Enum):
    """Types of metrics to monitor."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertStatus(Enum):
    """Alert status tracking."""

    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"
    SUPPRESSED = "suppressed"


@dataclass
class MetricValue:
    """Container for metric values."""

    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str]
    metric_type: MetricType

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
            "type": self.metric_type.value,
        }


@dataclass
class Alert:
    """Alert configuration and state."""

    alert_id: str
    name: str
    description: str
    severity: AlertSeverity
    condition: str
    threshold: float
    metric_name: str
    status: AlertStatus = AlertStatus.ACTIVE
    created_at: datetime = None
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    suppressed_until: Optional[datetime] = None
    tags: Dict[str, str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.tags is None:
            self.tags = {}


class ChildSafetyMonitor:
    """Specialized monitoring for child safety events."""

    def __init__(self) -> None:
        """Initialize child safety monitor."""
        self.safety_events = deque(maxlen=10000)
        self.safety_alerts = {}
        self.emergency_contacts = []
        # Child safety thresholds
        self.inappropriate_content_threshold = 5  # Per hour
        self.emotional_distress_threshold = 3  # Per hour
        self.unusual_activity_threshold = 20  # Per hour
        logger.info("Child safety monitor initialized")

    def record_safety_event(
        self,
        child_id: str,
        event_type: str,
        severity: str,
        details: Dict[str, Any],
    ) -> None:
        """Record a child safety event."""
        event = {
            "child_id": child_id,
            "event_type": event_type,
            "severity": severity,
            "details": details,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.safety_events.append(event)
        # Check for emergency conditions
        if severity == "emergency" or event_type in [
            "abuse_detected",
            "severe_distress",
        ]:
            self._trigger_emergency_alert(child_id, event_type, details)
        # Check for patterns
        self._check_safety_patterns(child_id, event_type)
        logger.warning(
            f"Child safety event recorded: {event_type} for child {child_id}"
        )

    def _trigger_emergency_alert(
        self, child_id: str, event_type: str, details: Dict[str, Any]
    ) -> None:
        """Trigger emergency alert for critical child safety events."""
        alert_id = f"emergency_{child_id}_{int(time.time())}"
        emergency_alert = {
            "alert_id": alert_id,
            "child_id": child_id,
            "event_type": event_type,
            "severity": "EMERGENCY",
            "details": details,
            "timestamp": datetime.utcnow().isoformat(),
            "requires_immediate_attention": True,
        }
        self.safety_alerts[alert_id] = emergency_alert
        # Log critical alert
        logger.critical(
            f"EMERGENCY CHILD SAFETY ALERT: {event_type} for child {child_id}"
        )
        # In production, this would trigger immediate notifications
        # to parents, administrators, and possibly authorities

    def _check_safety_patterns(self, child_id: str, event_type: str) -> None:
        """Check for concerning patterns in child safety events."""
        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)
        # Count recent events for this child
        recent_events = [
            event
            for event in self.safety_events
            if (
                event["child_id"] == child_id
                and datetime.fromisoformat(event["timestamp"]) > one_hour_ago
            )
        ]
        event_counts = defaultdict(int)
        for event in recent_events:
            event_counts[event["event_type"]] += 1
        # Check thresholds
        if (
            event_counts["inappropriate_content"]
            >= self.inappropriate_content_threshold
        ):
            self._create_pattern_alert(
                child_id,
                "excessive_inappropriate_content",
                event_counts["inappropriate_content"],
            )
        if (
            event_counts["emotional_distress"]
            >= self.emotional_distress_threshold
        ):
            self._create_pattern_alert(
                child_id,
                "repeated_emotional_distress",
                event_counts["emotional_distress"],
            )

    def _create_pattern_alert(
        self, child_id: str, pattern_type: str, count: int
    ) -> None:
        """Create alert for concerning patterns."""
        alert_id = f"pattern_{child_id}_{pattern_type}_{int(time.time())}"
        pattern_alert = {
            "alert_id": alert_id,
            "child_id": child_id,
            "pattern_type": pattern_type,
            "event_count": count,
            "severity": "HIGH",
            "timestamp": datetime.utcnow().isoformat(),
            "requires_parent_notification": True,
        }
        self.safety_alerts[alert_id] = pattern_alert
        logger.error(
            f"Child safety pattern detected: {pattern_type} for child {child_id} (count: {count})"
        )


class ComprehensiveMonitoringService:
    """
    Enterprise monitoring service with child safety focus.
    Features:
    - Real - time metrics collection
    - Child safety event monitoring
    - Performance metrics tracking
    - Security event detection
    - Automated alerting
    - COPPA compliance monitoring
    """

    def __init__(self) -> None:
        """Initialize comprehensive monitoring service."""
        self.metrics: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=10000)
        )
        self.alerts: Dict[str, Alert] = {}
        self.alert_rules: List[Dict[str, Any]] = []
        self.child_safety_monitor = ChildSafetyMonitor()

        # Performance tracking
        self.request_times = deque(maxlen=1000)
        self.error_counts = defaultdict(int)
        self.active_connections = 0

        # Security monitoring
        self.failed_auth_attempts = defaultdict(int)
        self.suspicious_activities = deque(maxlen=1000)

        # COPPA compliance tracking
        self.consent_violations = deque(maxlen=1000)
        self.data_access_logs = deque(maxlen=10000)

        # Monitoring thread
        self._monitoring_active = True
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop, daemon=True
        )
        self._monitoring_thread.start()

        # Initialize default alert rules
        self._setup_default_alerts()

        logger.info("Comprehensive monitoring service initialized")

    def _setup_default_alerts(self) -> None:
        """Setup default monitoring alerts."""
        default_alerts = [
            {
                "name": "High Error Rate",
                "description": "Error rate exceeds 5%",
                "severity": AlertSeverity.HIGH,
                "condition": "error_rate > 0.05",
                "threshold": 0.05,
                "metric_name": "error_rate",
            },
            {
                "name": "Slow Response Time",
                "description": "Average response time exceeds 2 seconds",
                "severity": AlertSeverity.MEDIUM,
                "condition": "avg_response_time > 2.0",
                "threshold": 2.0,
                "metric_name": "avg_response_time",
            },
            {
                "name": "High Memory Usage",
                "description": "Memory usage exceeds 80%",
                "severity": AlertSeverity.HIGH,
                "condition": "memory_usage > 0.8",
                "threshold": 0.8,
                "metric_name": "memory_usage",
            },
            {
                "name": "Failed Authentication Spike",
                "description": "Too many failed auth attempts",
                "severity": AlertSeverity.CRITICAL,
                "condition": "failed_auth_rate > 10",
                "threshold": 10.0,
                "metric_name": "failed_auth_rate",
            },
            {
                "name": "Child Safety Violation",
                "description": "Child safety event detected",
                "severity": AlertSeverity.EMERGENCY,
                "condition": "safety_events > 0",
                "threshold": 0.0,
                "metric_name": "safety_events",
            },
        ]

        for alert_config in default_alerts:
            self.add_alert_rule(**alert_config)

    def record_metric(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
        metric_type: MetricType = MetricType.GAUGE,
    ) -> None:
        """Record a metric value."""
        if tags is None:
            tags = {}

        metric = MetricValue(
            name=name,
            value=value,
            timestamp=datetime.utcnow(),
            tags=tags,
            metric_type=metric_type,
        )

        self.metrics[name].append(metric)

        # Check alert conditions
        self._check_alert_conditions(name, value)

    def record_request_time(self, endpoint: str, duration: float) -> None:
        """Record API request timing."""
        self.request_times.append(
            {
                "endpoint": endpoint,
                "duration": duration,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        # Record as metric
        self.record_metric(
            "request_duration",
            duration,
            {"endpoint": endpoint},
            MetricType.TIMER,
        )

        # Calculate average response time
        if len(self.request_times) >= 10:
            recent_times = [
                req["duration"] for req in list(self.request_times)[-100:]
            ]
            avg_time = sum(recent_times) / len(recent_times)
            self.record_metric("avg_response_time", avg_time)

    def record_error(
        self, error_type: str, endpoint: str, details: Optional[str] = None
    ) -> None:
        """Record an error occurrence."""
        self.error_counts[error_type] += 1

        # تم حذف المتغير error_event غير المستخدم

        # Record as metric
        self.record_metric(
            "error_count",
            1,
            {"error_type": error_type, "endpoint": endpoint},
            MetricType.COUNTER,
        )

        logger.error(f"Error recorded: {error_type} on {endpoint}")

    def record_security_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a security event."""
        security_event = {
            "event_type": event_type,
            "user_id": user_id,
            "ip_address": ip_address,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        self.suspicious_activities.append(security_event)

        # Track failed authentication attempts
        if event_type == "failed_authentication":
            key = ip_address or user_id or "unknown"
            self.failed_auth_attempts[key] += 1

            # Check for brute force attacks
            if self.failed_auth_attempts[key] > 5:
                self._create_security_alert(
                    "potential_brute_force",
                    key,
                    self.failed_auth_attempts[key],
                )

        logger.warning(
            f"Security event: {event_type} from {ip_address or 'unknown IP'}"
        )

    def record_child_safety_event(
        self,
        child_id: str,
        event_type: str,
        severity: str,
        details: Dict[str, Any],
    ) -> None:
        """Record a child safety event."""
        self.child_safety_monitor.record_safety_event(
            child_id, event_type, severity, details
        )

        # Record as metric
        self.record_metric(
            "safety_events",
            1,
            {
                "child_id": child_id,
                "event_type": event_type,
                "severity": severity,
            },
            MetricType.COUNTER,
        )

    def record_coppa_event(
        self,
        event_type: str,
        child_id: str,
        parent_id: str,
        details: Dict[str, Any],
    ) -> None:
        """Record COPPA compliance event."""
        coppa_event = {
            "event_type": event_type,
            "child_id": child_id,
            "parent_id": parent_id,
            "details": details,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if event_type == "consent_violation":
            self.consent_violations.append(coppa_event)
            logger.error(f"COPPA consent violation for child {child_id}")

        self.data_access_logs.append(coppa_event)

        # Record as metric
        self.record_metric(
            "coppa_events",
            1,
            {"event_type": event_type, "child_id": child_id},
            MetricType.COUNTER,
        )

    def add_alert_rule(
        self,
        name: str,
        description: str,
        severity: AlertSeverity,
        condition: str,
        threshold: float,
        metric_name: str,
        tags: Optional[Dict[str, str]] = None,
    ) -> str:
        """Add a new alert rule."""
        alert_id = hashlib.sha256(
            f"{name}_{metric_name}_{threshold}".encode()
        ).hexdigest()[:16]

        alert = Alert(
            alert_id=alert_id,
            name=name,
            description=description,
            severity=severity,
            condition=condition,
            threshold=threshold,
            metric_name=metric_name,
            tags=tags or {},
        )

        self.alerts[alert_id] = alert
        logger.info(f"Alert rule added: {name} (threshold: {threshold})")
        return alert_id

    def _check_alert_conditions(self, metric_name: str, value: float) -> None:
        """Check if any alert conditions are triggered."""
        for alert in self.alerts.values():
            if (
                alert.metric_name == metric_name
                and alert.status == AlertStatus.ACTIVE
            ):
                if self._evaluate_condition(
                    alert.condition, value, alert.threshold
                ):
                    self._trigger_alert(alert, value)

    def _evaluate_condition(
        self, condition: str, value: float, threshold: float
    ) -> bool:
        """Evaluate alert condition."""
        # Simple condition evaluation (in production, use a proper expression parser)
        if ">" in condition:
            return value > threshold
        elif "<" in condition:
            return value < threshold
        elif "==" in condition:
            return abs(value - threshold) < 0.001
        elif "!=" in condition:
            return abs(value - threshold) >= 0.001
        return False

    def _trigger_alert(self, alert: Alert, current_value: float) -> None:
        """Trigger an alert."""
        alert.last_triggered = datetime.utcnow()
        alert.trigger_count += 1

        # تم حذف المتغير alert_data غير المستخدم

        if alert.severity == AlertSeverity.EMERGENCY:
            logger.critical(
                f"EMERGENCY ALERT: {alert.name} - {alert.description}"
            )
        elif alert.severity == AlertSeverity.CRITICAL:
            logger.error(f"CRITICAL ALERT: {alert.name} - {alert.description}")
        else:
            logger.warning(f"ALERT: {alert.name} - {alert.description}")

        # In production, send notifications via email, SMS, Slack, etc.

    def _create_security_alert(
        self, alert_type: str, source: str, count: int
    ) -> None:
        """Create a security - specific alert."""
        alert_id = f"security_{alert_type}_{source}_{int(time.time())}"

        # تم حذف المتغير security_alert غير المستخدم

        logger.critical(
            f"SECURITY ALERT: {alert_type} from {source} (count: {count})"
        )

    def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        while self._monitoring_active:
            try:
                # Calculate system metrics
                self._calculate_system_metrics()

                # Check system health
                self._check_system_health()

                # Cleanup old data
                self._cleanup_old_data()

                # Sleep for monitoring interval
                time.sleep(60)  # Monitor every minute
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)  # Short sleep on error

    def _calculate_system_metrics(self) -> None:
        """Calculate system - wide metrics."""
        try:
            # Calculate error rate
            if len(self.request_times) > 0:
                total_requests = len(self.request_times)
                total_errors = sum(self.error_counts.values())
                error_rate = (
                    total_errors / total_requests if total_requests > 0 else 0
                )
                self.record_metric("error_rate", error_rate)

            # Calculate memory usage (mock)
            import psutil

            memory_usage = psutil.virtual_memory().percent / 100.0
            self.record_metric("memory_usage", memory_usage)

            # Calculate CPU usage (mock)
            cpu_usage = psutil.cpu_percent() / 100.0
            self.record_metric("cpu_usage", cpu_usage)
        except ImportError:
            # psutil not available, use mock values
            self.record_metric("memory_usage", 0.5)  # 50% mock
            self.record_metric("cpu_usage", 0.3)  # 30% mock
        except Exception as e:
            logger.warning(f"Error calculating system metrics: {e}")

    def _check_system_health(self) -> None:
        """Check overall system health."""
        health_score = 1.0

        # Check recent error rate
        if (
            "error_rate" in self.metrics
            and len(self.metrics["error_rate"]) > 0
        ):
            recent_error_rate = self.metrics["error_rate"][-1].value
            if recent_error_rate > 0.1:  # 10% error rate
                health_score -= 0.3

        # Check response times
        if len(self.request_times) > 10:
            recent_times = [
                req["duration"] for req in list(self.request_times)[-10:]
            ]
            avg_time = sum(recent_times) / len(recent_times)
            if avg_time > 5.0:  # 5 second average
                health_score -= 0.2

        # Check child safety events
        recent_safety_events = [
            event
            for event in self.child_safety_monitor.safety_events
            if datetime.fromisoformat(event["timestamp"])
            > datetime.utcnow() - timedelta(hours=1)
        ]
        if len(recent_safety_events) > 0:
            health_score -= 0.1 * len(recent_safety_events)

        health_score = max(0.0, min(1.0, health_score))
        self.record_metric("system_health_score", health_score)

    def _cleanup_old_data(self) -> None:
        """Clean up old monitoring data."""
        # تم حذف المتغير cutoff_time غير المستخدم

        # Clean up old metrics (keeping only recent ones due to deque maxlen)

        # Clean up old error counts
        if len(self.error_counts) > 100:
            # Keep only the most recent error types
            sorted_errors = sorted(
                self.error_counts.items(), key=lambda x: x[1], reverse=True
            )
            self.error_counts = dict(sorted_errors[:50])

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of current metrics."""
        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "metrics_count": len(self.metrics),
            "active_alerts": len(
                [
                    a
                    for a in self.alerts.values()
                    if a.status == AlertStatus.ACTIVE
                ]
            ),
            "total_requests": len(self.request_times),
            "total_errors": sum(self.error_counts.values()),
            "child_safety_events": len(
                self.child_safety_monitor.safety_events
            ),
            "security_events": len(self.suspicious_activities),
            "coppa_events": len(self.data_access_logs),
        }

        # Add latest metric values
        latest_metrics = {}
        for name, values in self.metrics.items():
            if values:
                latest_metrics[name] = values[-1].value

        summary["latest_metrics"] = latest_metrics
        return summary

    def shutdown(self) -> None:
        """Shutdown monitoring service."""
        self._monitoring_active = False
        if self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=5)

        logger.info("Comprehensive monitoring service shutdown")


# Global monitoring instance
monitoring_service = ComprehensiveMonitoringService()


# Decorator for monitoring function performance
def monitor_performance(metric_name: str = None) -> Callable:
    """Decorator to monitor function performance."""

    def decorator(func) -> Callable:
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            function_name = metric_name or f"{func.__module__}.{func.__name__}"

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                monitoring_service.record_request_time(function_name, duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                monitoring_service.record_error(
                    "function_error", function_name, str(e)
                )
                monitoring_service.record_request_time(function_name, duration)
                raise

        return wrapper

    return decorator
