"""
Buy Signal Filter and Position Sizing Logic.
Determines if a decision qualifies as a buy signal and calculates position size.
"""

import logging
from typing import Dict, Any, Optional, Tuple
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from app.config import (
    MIN_BUY_CONFIDENCE, HIGH_CONFIDENCE_THRESHOLD,
    POSITION_SIZE_HIGH, POSITION_SIZE_MEDIUM
)

logger = logging.getLogger(__name__)


class BuySignalFilter:
    """Filters decisions and calculates position sizing for buy signals."""

    def __init__(self):
        """Initialize the Buy Signal Filter."""
        pass

    def is_valid_buy_signal(
        self,
        decision: Dict[str, Any],
        features: Dict[str, Any]
    ) -> bool:
        """
        Determine if a decision qualifies as a valid buy signal.

        Criteria:
        - Decision == "BUY"
        - Confidence >= MIN_BUY_CONFIDENCE (0.75)
        - Volatility != "high"
        - Volume confirmation == True

        Args:
            decision: Decision dictionary from reasoning agent
            features: Technical features dictionary

        Returns:
            True if valid buy signal, False otherwise
        """
        # Check decision
        if decision.get('decision') != 'BUY':
            logger.debug("Not a BUY decision")
            return False

        # Check confidence
        confidence = decision.get('confidence', 0.0)
        if confidence < MIN_BUY_CONFIDENCE:
            logger.debug(f"Confidence {confidence:.2%} below threshold {MIN_BUY_CONFIDENCE:.2%}")
            return False

        # Check volatility
        volatility_level = features.get('volatility_level', 'unknown')
        if volatility_level == 'high':
            logger.debug("High volatility detected - rejecting buy signal")
            return False

        # Check volume confirmation
        volume_confirmation = features.get('volume_confirmation', False)
        if not volume_confirmation:
            logger.debug("No volume confirmation - rejecting buy signal")
            return False

        logger.info(
            f"Valid buy signal: Confidence {confidence:.2%}, "
            f"Volatility {volatility_level}, Volume confirmed"
        )
        return True

    def calculate_position_size(
        self,
        confidence: float,
        remaining_budget: float
    ) -> Tuple[float, str]:
        """
        Calculate suggested position size based on confidence.

        Position sizing rules:
        - Confidence >= 0.85: $300-400
        - Confidence 0.75-0.85: $150-250
        - Confidence < 0.75: ignore (should be filtered already)

        Args:
            confidence: Decision confidence score (0-1)
            remaining_budget: Remaining monthly budget

        Returns:
            Tuple of (suggested_amount, rationale)
        """
        if confidence >= HIGH_CONFIDENCE_THRESHOLD:
            # High confidence: larger position
            min_size, max_size = POSITION_SIZE_HIGH
            suggested = (min_size + max_size) / 2  # Midpoint
            rationale = f"High confidence ({confidence:.1%}) - larger position"

        elif confidence >= MIN_BUY_CONFIDENCE:
            # Medium confidence: smaller position
            min_size, max_size = POSITION_SIZE_MEDIUM
            suggested = (min_size + max_size) / 2  # Midpoint
            rationale = f"Medium confidence ({confidence:.1%}) - moderate position"

        else:
            # Below threshold (shouldn't happen if filtered properly)
            suggested = 0.0
            rationale = "Confidence too low"

        # Cap at remaining budget
        if suggested > remaining_budget:
            suggested = remaining_budget
            rationale += f" (capped at remaining budget ${remaining_budget:.2f})"

        logger.info(f"Position size: ${suggested:.2f} - {rationale}")

        return suggested, rationale

    def should_notify(
        self,
        decision: Dict[str, Any],
        features: Dict[str, Any],
        remaining_budget: float
    ) -> Tuple[bool, Optional[float], str]:
        """
        Comprehensive check: should we notify about this signal?

        Args:
            decision: Decision dictionary
            features: Technical features
            remaining_budget: Remaining budget

        Returns:
            Tuple of (should_notify, suggested_amount, reason)
        """
        # Check if valid buy signal
        if not self.is_valid_buy_signal(decision, features):
            return False, None, "Does not meet buy signal criteria"

        # Check budget availability
        if remaining_budget <= 0:
            return False, None, "No budget remaining this month"

        # Calculate position size
        confidence = decision.get('confidence', 0.0)
        suggested_amount, size_rationale = self.calculate_position_size(
            confidence,
            remaining_budget
        )

        # Final check: amount must be meaningful
        if suggested_amount < 100:
            return False, None, f"Suggested amount ${suggested_amount:.2f} too small (minimum $100)"

        reason = f"Valid buy signal - {size_rationale}"
        return True, suggested_amount, reason

    def format_buy_signal_summary(
        self,
        ticker: str,
        decision: Dict[str, Any],
        features: Dict[str, Any],
        suggested_amount: float,
        remaining_budget: float
    ) -> Dict[str, Any]:
        """
        Format a buy signal into a structured summary.

        Args:
            ticker: Stock ticker
            decision: Decision dictionary
            features: Technical features
            suggested_amount: Suggested investment amount
            remaining_budget: Remaining monthly budget

        Returns:
            Dictionary with formatted buy signal information
        """
        return {
            "ticker": ticker,
            "decision": decision.get('decision'),
            "confidence": decision.get('confidence', 0.0),
            "sentiment": decision.get('sentiment'),
            "suggested_amount": suggested_amount,
            "remaining_budget": remaining_budget,
            "latest_price": features.get('latest_price', 0.0),
            "trend": features.get('trend'),
            "momentum": features.get('momentum'),
            "rsi": features.get('rsi', 0.0),
            "volatility_level": features.get('volatility_level'),
            "volume_confirmation": features.get('volume_confirmation'),
            "explanation": decision.get('explanation', ''),
            "key_signals": decision.get('key_signals', []),
            "risk_factors": decision.get('risk_factors', []),
        }


# Singleton instance
_buy_signal_filter_instance = None


def get_buy_signal_filter() -> BuySignalFilter:
    """Get or create the BuySignalFilter singleton."""
    global _buy_signal_filter_instance
    if _buy_signal_filter_instance is None:
        _buy_signal_filter_instance = BuySignalFilter()
    return _buy_signal_filter_instance
