from app.config import ALLOWED_ACTIONS, ALLOWED_ASSETS, MAX_POSITION_SIZE
from app.schemas import RiskProfile


def validate_trade(asset: str, action: str, size: float) -> tuple[bool, str]:
    asset = asset.strip()
    action = action.strip()
    if size <= 0:
        return False, "size-must-be-positive"
    if size > MAX_POSITION_SIZE:
        return False, "position-size-exceeds-limit"
    if asset.upper() not in ALLOWED_ASSETS:
        return False, "asset-not-allowed"
    if action.lower() not in ALLOWED_ACTIONS:
        return False, "action-not-allowed"
    return True, "ok"


def validate_profile(profile: RiskProfile) -> tuple[bool, str]:
    if profile.max_drawdown > 0.6:
        return False, "risk-profile-too-aggressive"
    return True, "ok"
