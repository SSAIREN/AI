from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class ScenarioConfig:
    scenario_id: str
    name_kr: str
    description: str
    keywords: List[str]
    required_tools: List[str]
    optional_tools: List[str]
    risk_weight: float


SCENARIOS: Dict[str, ScenarioConfig] = {
    "KIDNAP_THREAT": ScenarioConfig(
        scenario_id="KIDNAP_THREAT",
        name_kr="납치/협박형",
        description="가족을 납치했거나 위해를 가하겠다고 협박하며 금전을 요구하는 유형",
        keywords=["납치", "잡고 있다", "죽인다", "협박", "돈 보내", "입금", "경찰 부르지 마"],
        required_tools=["check_family_gps", "send_family_sms_alert", "save_evidence"],
        optional_tools=["notify_police", "show_warning_banner"],
        risk_weight=1.0,
    ),
    "INSTITUTION_IMPERSONATION": ScenarioConfig(
        scenario_id="INSTITUTION_IMPERSONATION",
        name_kr="기관 사칭형",
        description="검찰, 경찰, 금융감독원 등 공공기관을 사칭해 계좌 이체나 개인정보를 요구하는 유형",
        keywords=["검찰", "경찰", "금융감독원", "수사관", "대포통장", "안전 계좌", "영장"],
        required_tools=["verify_official_institution", "show_warning_banner", "save_evidence"],
        optional_tools=["send_family_sms_alert", "notify_police"],
        risk_weight=0.9,
    ),
    "FAMILY_IMPERSONATION": ScenarioConfig(
        scenario_id="FAMILY_IMPERSONATION",
        name_kr="가족 사칭형",
        description="가족이나 지인을 사칭해 사고, 병원비, 휴대폰 고장 등을 이유로 돈을 요구하는 유형",
        keywords=["엄마", "아빠", "아들", "딸", "사고", "병원비", "휴대폰 고장", "카드"],
        required_tools=["verify_family_location", "send_family_sms_alert", "save_evidence"],
        optional_tools=["check_family_gps"],
        risk_weight=0.85,
    ),
    "SAFE_ACCOUNT_TRANSFER": ScenarioConfig(
        scenario_id="SAFE_ACCOUNT_TRANSFER",
        name_kr="안전 계좌 이체형",
        description="보호 계좌나 안전 계좌라는 명목으로 즉시 송금을 유도하는 유형",
        keywords=["안전 계좌", "보호 계좌", "즉시 이체", "송금", "OTP", "인증번호", "원격제어"],
        required_tools=["show_transfer_warning", "save_evidence", "show_warning_banner"],
        optional_tools=["send_family_sms_alert", "notify_police"],
        risk_weight=0.95,
    ),
}


DETAIL_SCORE_KEYS = [
    "urgency_pressure",
    "financial_demand",
    "isolation_attempt",
    "identity_deception",
    "behavioral_pattern",
]
