"""System and meta tools for JARVIS autonomous agent loop."""

from typing import Dict, Any
from jarvis.utils.logger import get_logger

logger = get_logger("tools.system")


def backtrack(reason: str) -> Dict[str, Any]:
    """현재 접근 방식이나 가설이 실패 또는 막다른 길(Dead End)에 봉착했을 때, 
    안전한 직전 체크포인트로 되돌아가 대안(Plan B)을 탐색합니다.
    
    Args:
        reason: 되돌아가야 하는 구체적인 이유 및 실패 원인 (예: '쿠팡 주문서에 필수 컬럼 누락으로 변환 불가').
    """
    logger.info(f"System backtrack triggered with reason: {reason}")
    return {
        "status": "BACKTRACK_REQUESTED",
        "reason": reason,
        "instruction": "직전 안전 체크포인트로 롤백되었으며, 이 실패 원인은 Taboo List에 등록되었습니다. 대안 계획을 실행하십시오.",
    }
