"""from datetime import datetime, timezone
from typing import Dict, List
import logging
import os
from fastapi import BackgroundTasks, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from .models import AlertPayload, EmergencyAlert, HealthResponse, NotificationRequest
from .services import EmergencyResponseService, NotificationService, SystemMonitorService.
"""

"""Emergency Response Endpoints - API routes for emergency system"""

from src.infrastructure.logging_config import get_logger

logger = get_logger(__name__, component="api")

security = HTTPBearer()

# متغيرات البيئة - أمان محسّن بدون قيم افتراضية خطيرة
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    logger.critical("JWT_SECRET environment variable is required but not set")
    raise RuntimeError(
        "CRITICAL SECURITY ERROR: JWT_SECRET must be set in environment variables",
    )

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")


class EmergencyEndpoints:
    """Emergency Response API Endpoints."""

    def __init__(
        self,
        emergency_service: EmergencyResponseService,
        monitor_service: SystemMonitorService,
        notification_service: NotificationService,
    ):
        self.emergency_service = emergency_service
        self.monitor_service = monitor_service
        self.notification_service = notification_service

    async def webhook_alerts(
        self,
        request: Request,
        payload: AlertPayload,
        background_tasks: BackgroundTasks,
    ) -> Dict[str, str]:
        """استلام التنبيهات من Prometheus / Alertmanager."""
        client_ip = request.client.host
        logger.info(f"Received alert webhook from {client_ip}")
        try:
            # معالجة كل تنبيه في الخلفية
            for alert_data in payload.alerts:
                background_tasks.add_task(
                    self._process_single_alert,
                    alert_data,
                    payload.receiver,
                )
            return {
                "status": "accepted",
                "message": f"تم استلام {len(payload.alerts)} تنبيه للمعالجة",
            }
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def _process_single_alert(self, alert_data: Dict, receiver: str):
        """معالجة تنبيه واحد."""
        try:
            # تحويل البيانات إلى نموذج التنبيه
            emergency_alert = EmergencyAlert(
                id=f"alert_{datetime.now().timestamp()}",
                severity=alert_data.get("labels", {}).get(
                    "severity", "unknown"
                ),
                description=alert_data.get("annotations", {}).get(
                    "summary",
                    "No description",
                ),
                source=alert_data.get("labels", {}).get("instance", "unknown"),
                timestamp=datetime.now(timezone.utc),
                child_id=alert_data.get("labels", {}).get("child_id"),
                action_required=True,
                metadata=alert_data,
            )
            await self.emergency_service.process_alert(emergency_alert.dict())
        except Exception as e:
            logger.error(f"Error processing single alert: {e}")

    async def health_check(self) -> HealthResponse:
        """فحص صحة خدمة الاستجابة الطارئة."""
        try:
            # فحص الاتصال بالخدمات المطلوبة
            system_status = await self.monitor_service.check_system_health()
            dependencies = {}
            for status in system_status:
                dependencies[status.service_name] = status.status
            return HealthResponse(
                status="healthy",
                timestamp=datetime.now(timezone.utc),
                version="1.0.0",
                uptime_seconds=0.0,  # سيتم حسابه لاحقاً
                dependencies=dependencies,
            )
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise HTTPException(status_code=503, detail="Service unhealthy")

    async def get_alerts(
        self,
        credentials: HTTPAuthorizationCredentials = Depends(security),
    ) -> List[Dict]:
        """الحصول على قائمة التنبيهات النشطة."""
        # التحقق من صحة التوكن
        if not self._verify_token(credentials.credentials):
            raise HTTPException(status_code=401, detail="Invalid token")
        try:
            # الحصول على التنبيهات من Redis
            # هذا مجرد مثال - سيتم تنفيذه بالكامل لاحقاً
            return []
        except Exception as e:
            logger.error(f"Error fetching alerts: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def send_notification(
        self,
        request: NotificationRequest,
        credentials: HTTPAuthorizationCredentials = Depends(security),
    ) -> Dict[str, str]:
        """إرسال إشعار طارئ."""
        # التحقق من صحة التوكن
        if not self._verify_token(credentials.credentials):
            raise HTTPException(status_code=401, detail="Invalid token")
        try:
            success = await self.notification_service.send_notification(
                request
            )
            if success:
                return {"status": "sent", "message": "تم إرسال الإشعار بنجاح"}
            raise HTTPException(status_code=500, detail="فشل في إرسال الإشعار")
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def system_status(
        self,
        credentials: HTTPAuthorizationCredentials = Depends(security),
    ) -> List[Dict]:
        """الحصول على حالة النظام."""
        # التحقق من صحة التوكن
        if not self._verify_token(credentials.credentials):
            raise HTTPException(status_code=401, detail="Invalid token")
        try:
            statuses = await self.monitor_service.check_system_health()
            return [status.dict() for status in statuses]
        except Exception as e:
            logger.error(f"Error checking system status: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    def _verify_token(self, token: str) -> bool:
        """التحقق من صحة التوكن."""
        if ENVIRONMENT == "development":
            return True  # تجاهل التحقق في بيئة التطوير
        # في الإنتاج، سيتم التحقق من JWT token
        return token == JWT_SECRET  # مؤقت - سيتم تحسينه
