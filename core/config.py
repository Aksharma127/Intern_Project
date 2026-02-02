"""Project configuration and thresholds"""
from typing import Final

# Price thresholds according to Reconciliation_Rules.md
PRICE_EXACT_MATCH_PERCENT: Final[float] = 0.02  # 2%
PRICE_FLAG_LOW_PERCENT: Final[float] = 0.05    # >5% and <=15% => flag
PRICE_FLAG_HIGH_PERCENT: Final[float] = 0.15   # >15% => escalate

# Total variance thresholds
TOTAL_VARIANCE_PERCENT: Final[float] = 0.01  # 1% total variance guidance (used in rules)

# Other config
DEFAULT_EXTRACTION_CONFIDENCE: Final[float] = 0.90
