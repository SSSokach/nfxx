"""Token用量检测与限速机制"""
from app import SessionLocal
from models import TokenUsage
from datetime import date, datetime
import time

# 每日限额配置
DAILY_LIMITS = {
    "request_count": 50,   # 每日最多50次AI请求
    "token_count": 50000,  # 每日最多50000 token
}

# 限速阈值（达到此百分比后开始限速）
SLOWDOWN_THRESHOLD = 0.6  # 60%后开始降速
SLOWDOWN_MAX_DELAY = 8.0  # 最大延迟8秒

def get_today_usage(user_id: int):
    """获取用户今日用量"""
    db = SessionLocal()
    try:
        today = date.today()
        usage = db.query(TokenUsage).filter(
            TokenUsage.user_id == user_id,
            TokenUsage.date == today,
        ).first()
        return usage
    finally:
        db.close()

def record_usage(user_id: int, token_count: int = 0):
    """记录一次AI调用用量"""
    db = SessionLocal()
    try:
        today = date.today()
        usage = db.query(TokenUsage).filter(
            TokenUsage.user_id == user_id,
            TokenUsage.date == today,
        ).first()
        if not usage:
            usage = TokenUsage(
                user_id=user_id,
                date=today,
                request_count=0,
                token_count=0,
            )
            db.add(usage)
        usage.request_count += 1
        usage.token_count += token_count
        usage.updated_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()

def check_rate_limit(user_id: int):
    """检查用户是否超出限额，返回 {allowed, reason, usage_info}"""
    usage = get_today_usage(user_id)
    if not usage:
        return {
            "allowed": True,
            "reason": None,
            "usage": {"request_count": 0, "token_count": 0},
            "limits": DAILY_LIMITS,
        }

    req_pct = usage.request_count / DAILY_LIMITS["request_count"]
    token_pct = usage.token_count / DAILY_LIMITS["token_count"]

    if usage.request_count >= DAILY_LIMITS["request_count"]:
        return {
            "allowed": False,
            "reason": f"今日AI请求次数已达上限({DAILY_LIMITS['request_count']}次)",
            "usage": {"request_count": usage.request_count, "token_count": usage.token_count},
            "limits": DAILY_LIMITS,
        }

    if usage.token_count >= DAILY_LIMITS["token_count"]:
        return {
            "allowed": False,
            "reason": f"今日Token用量已达上限({DAILY_LIMITS['token_count']})",
            "usage": {"request_count": usage.request_count, "token_count": usage.token_count},
            "limits": DAILY_LIMITS,
        }

    return {
        "allowed": True,
        "reason": None,
        "usage": {"request_count": usage.request_count, "token_count": usage.token_count},
        "limits": DAILY_LIMITS,
    }

def apply_slowdown(user_id: int):
    """根据用量百分比计算并施加延迟，控制响应速度"""
    usage = get_today_usage(user_id)
    if not usage:
        return 0.0

    req_pct = usage.request_count / DAILY_LIMITS["request_count"]
    token_pct = usage.token_count / DAILY_LIMITS["token_count"]
    max_pct = max(req_pct, token_pct)

    if max_pct < SLOWDOWN_THRESHOLD:
        return 0.0

    # 从阈值到100%线性增加延迟
    excess_ratio = (max_pct - SLOWDOWN_THRESHOLD) / (1.0 - SLOWDOWN_THRESHOLD)
    delay = excess_ratio * SLOWDOWN_MAX_DELAY

    if delay > 0:
        time.sleep(delay)

    return round(delay, 2)

def estimate_tokens(text: str) -> int:
    """粗略估算文本的token数量（中文约1.5字/token，英文约4字符/token）"""
    if not text:
        return 0
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other_chars = len(text) - chinese_chars
    return int(chinese_chars / 1.5 + other_chars / 4)
