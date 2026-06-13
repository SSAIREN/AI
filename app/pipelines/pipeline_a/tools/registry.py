from typing import Any, Awaitable, Callable, Dict

from app.pipelines.pipeline_a.tools.actions import (
    check_family_gps,
    notify_police,
    save_evidence,
    send_family_sms_alert,
    show_transfer_warning,
    show_warning_banner,
    verify_family_location,
    verify_official_institution,
    verify_suspicious_account,
    check_spam_phone_number,
    send_emergency_email_alert,
    generate_safety_guideline,
)

ToolFn = Callable[..., Awaitable[Dict[str, Any]]]


TOOL_REGISTRY: Dict[str, ToolFn] = {
    "check_family_gps": check_family_gps,
    "send_family_sms_alert": send_family_sms_alert,
    "notify_police": notify_police,
    "save_evidence": save_evidence,
    "verify_official_institution": verify_official_institution,
    "show_warning_banner": show_warning_banner,
    "verify_family_location": verify_family_location,
    "show_transfer_warning": show_transfer_warning,
    "verify_suspicious_account": verify_suspicious_account,
    "check_spam_phone_number": check_spam_phone_number,
    "send_emergency_email_alert": send_emergency_email_alert,
    "generate_safety_guideline": generate_safety_guideline,
}
