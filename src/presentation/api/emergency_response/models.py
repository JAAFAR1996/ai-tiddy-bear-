"""from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field.
"""

"""Emergency Response Models - Data models for emergency system"""


class AlertPayload(BaseModel):
    """نموذج بيانات التنبيه الواردة."""

    alerts: List[Dict[str, Any]]
    receiver: str = Field(..., description="اسم المتلقي")
    status: str = Field(..., description="حالة التنبيه")


class EmergencyAlert(BaseModel):
    """نموذج التنبيه الطارئ."""

    id: str = Field(..., description="معرف التنبيه")
    severity: str = Field(..., description="مستوى الخطورة")
    description: str = Field(..., description="وصف التنبيه")
    source: str = Field(..., description="مصدر التنبيه")
    timestamp: datetime = Field(..., description="وقت التنبيه")
    child_id: Optional[str] = Field(None, description="معرف الطفل المتأثر")
    action_required: bool = Field(True, description="يتطلب إجراء")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SystemStatus(BaseModel):
    """نموذج حالة النظام."""

    service_name: str
    status: str
    last_check: datetime
    response_time_ms: float
    error_message: Optional[str] = None


class HealthResponse(BaseModel):
    """نموذج استجابة فحص الصحة."""

    status: str = Field(..., description="حالة الخدمة")
    timestamp: datetime = Field(..., description="وقت الفحص")
    version: str = Field(..., description="إصدار الخدمة")
    uptime_seconds: float = Field(..., description="وقت التشغيل بالثواني")
    dependencies: Dict[str, str] = Field(default_factory=dict)


class NotificationRequest(BaseModel):
    """نموذج طلب الإشعار."""

    alert_id: str
    child_id: Optional[str] = None
    parent_contacts: List[str]
    message: str
    priority: str = Field(default="high", regex="^(low|medium|high|critical)$")


class ResponseAction(BaseModel):
    """نموذج إجراء الاستجابة."""

    action_type: str
    target: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    success: bool = False
    error_message: Optional[str] = None
    executed_at: Optional[datetime] = None
