"""Sampling theory utilities exposed as FastAPI endpoints."""

from typing import Any, Dict, Optional

import math
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/sampling-theory", tags=["Sampling Theory"])


class EWMADecisionEngine:
    """Encapsulates EWMA sampling theory controls used for counterfeit/suspect detection."""

    def __init__(
        self,
        S_baseline: float = 0.01,
        S_prev: Optional[float] = None,
        alpha: float = 0.2,
        k: float = 2.5,
        instant_thresh_factor: float = 3.0,
        extreme_abs_thresh: float = 0.15,
        confirm_repeat: bool = True,
        confirm_samples: int = 1,
        r_force_high_sampling: int = 3,
    ):
        self.S_baseline = S_baseline
        self.S_prev = S_prev if S_prev is not None else S_baseline
        self.alpha = alpha
        self.k = k
        self.instant_thresh = instant_thresh_factor * max(S_baseline, 1e-6)
        self.extreme_abs_thresh = extreme_abs_thresh
        self.confirm_repeat = confirm_repeat
        self.confirm_samples = confirm_samples
        self.r_force_high_sampling = r_force_high_sampling

    def sigma_ewma(self, p: float) -> float:
        """Compute EWMA-adjusted sigma for a proportion."""
        sigma_x = math.sqrt(p * (1 - p))
        return math.sqrt(self.alpha / (2 - self.alpha)) * sigma_x

    def compute_limits(self, p_for_sigma: Optional[float] = None):
        """Return control limits anchored on the current baseline."""
        p = p_for_sigma if p_for_sigma is not None else self.S_prev
        sigma = self.sigma_ewma(p)
        UCL = self.S_baseline + self.k * sigma
        LCL = max(0.0, self.S_baseline - self.k * sigma)
        return UCL, LCL, sigma

    def decide(self, x_t: float, extra_signals: Optional[Dict[str, object]] = None) -> Dict:
        """Evaluate the current lot to decide whether to escalate."""
        extra_signals = extra_signals or {}

        if x_t >= self.extreme_abs_thresh:
            reason = (
                f"Immediate extreme measurement: x_t={x_t:.3f} >= "
                f"extreme_abs_thresh {self.extreme_abs_thresh:.3f}"
            )
            return {
                "decision": "Likely counterfeit / Severe failure",
                "S_t": self.S_prev,
                "UCL": None,
                "sigma_EWMA": self.sigma_ewma(self.S_prev),
                "reason": reason,
                "actions": [
                    "Quarantine this lot and lot family",
                    "Force 100% inspection of queued lots",
                    "Escalate to engineering & lab analysis",
                ],
            }

        UCL, LCL, sigma = self.compute_limits()
        S_t = self.alpha * x_t + (1 - self.alpha) * self.S_prev

        if extra_signals.get("tool_alarm") or extra_signals.get("recipe_change"):
            k_backup = self.k
            self.k = max(1.5, self.k - 1.0)
            UCL, LCL, sigma = self.compute_limits()
            self.k = k_backup

        if S_t > UCL:
            reason = f"S_t ({S_t:.4f}) > UCL ({UCL:.4f}) -> sustained increase"
            actions = [
                f"Mark as SUSPECT. Force higher sampling for next {self.r_force_high_sampling} lots",
                "Quarantine lot(s) pending 100% inspection",
                "Start root-cause / defect classification",
            ]
            decision = "Suspect (sustained drift)"
        elif x_t > self.instant_thresh:
            reason = (
                f"Single-lot spike: x_t ({x_t:.4f}) > instant_thresh ({self.instant_thresh:.4f})"
            )
            if self.confirm_repeat:
                actions = [
                    "Request immediate repeat measurement(s) of this lot (reinspect same wafers/dies)",
                    "If repeat confirms, treat as SUSPECT and force 100% inspection",
                ]
                decision = "Suspect - confirm (single-lot spike)"
            else:
                actions = ["Treat as Suspect (no confirm configured)"]
                decision = "Suspect (single-lot spike)"
        else:
            reason = (
                f"No threshold crossed (S_t {S_t:.4f} <= UCL {UCL:.4f}, "
                f"x_t {x_t:.4f} <= instant_thresh {self.instant_thresh:.4f})"
            )
            actions = ["Normal - Continue baseline sampling"]
            decision = "Normal"

        self.S_prev = S_t

        return {
            "decision": decision,
            "S_t": S_t,
            "UCL": UCL,
            "sigma_EWMA": sigma,
            "reason": reason,
            "actions": actions,
        }


class SamplingTheoryPayload(BaseModel):
    """Request payload for EWMA decision."""

    s_prev: float = Field(0.01, description="Previous EWMA value (defaults to baseline).")
    x: float = Field(..., description="Observed defect fraction for the current lot.")
    extra_signals: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Optional contextual signals."
    )


@router.post(
    "/ewma-decision",
    response_model=Dict[str, Any],
    summary="Evaluate EWMA-based sampling theory decision",
    description=(
        "Provide the latest defect fraction and optional context. "
        "Returns whether the lot is Normal, Suspect, or requires escalation."
    ),
)
async def evaluate_sampling_decision(payload: SamplingTheoryPayload) -> Dict[str, Any]:
    """Endpoint that evaluates the EWMA control chart and returns an action plan."""

    engine = EWMADecisionEngine(
        S_baseline=0.01,
        S_prev=payload.s_prev,
        alpha=0.3,  # tuned for faster reaction
        k=2.0,  # sensitive
        instant_thresh_factor=3.0,
        extreme_abs_thresh=0.15,
    )

    result = engine.decide(payload.x, extra_signals=payload.extra_signals or {"tool_alarm": False})
    return result