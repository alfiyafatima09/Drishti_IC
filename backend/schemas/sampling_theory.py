# """Schemas for sampling theory endpoints."""
# from typing import List, Optional

# from pydantic import BaseModel, Field, confloat, conint


# class SamplingTheoryExtraSignals(BaseModel):
#     """Optional auxiliary signals that increase sensitivity."""

#     tool_alarm: Optional[bool] = Field(False, description="Raised tool alarm during measurement")
#     recipe_change: Optional[bool] = Field(
#         False, description="Was there a recent recipe/recipe parameter change?"
#     )
#     defect_signature: Optional[str] = Field(
#         None, description="Optional descriptive tag for observed defect characteristics"
#     )


# class SamplingTheoryRequest(BaseModel):
#     """Request payload for EWMA-based sampling decisions."""

#     defect_fraction: confloat(ge=0.0, le=1.0) = Field(..., description="Observed defect fraction in the current lot")
#     S_baseline: Optional[confloat(ge=0.0, le=1.0)] = Field(
#         None, description="Baseline defect rate used to compute control limits"
#     )
#     S_prev: Optional[confloat(ge=0.0, le=1.0)] = Field(
#         None, description="Previous EWMA value (if omitted, baseline is used)"
#     )
#     alpha: Optional[confloat(gt=0.0, lt=1.0)] = Field(
#         None, description="EWMA smoothing factor between 0 and 1"
#     )
#     k: Optional[confloat(gt=0.0)] = Field(None, description="Control chart width multiplier")
#     instant_thresh_factor: Optional[confloat(gt=0.0)] = Field(
#         None, description="Multiplier of S_baseline that defines single-lot spike threshold"
#     )
#     extreme_abs_thresh: Optional[confloat(ge=0.0, le=1.0)] = Field(
#         None, description="Absolute defect fraction threshold for immediate action"
#     )
#     confirm_repeat: Optional[bool] = Field(
#         None, description="Request immediate repeat measurement when a spike is detected"
#     )
#     confirm_samples: Optional[conint(gt=0)] = Field(
#         None, description="Number of repeated measurements to request when confirming spikes"
#     )
#     r_force_high_sampling: Optional[conint(ge=0)] = Field(
#         None, description="Number of subsequent lots to force high sampling for suspect drift"
#     )
#     extra_signals: Optional[SamplingTheoryExtraSignals] = Field(
#         None, description="Additional contextual signals (tool alarms, recipe changes, etc.)"
#     )


# class SamplingTheoryDecisionResponse(BaseModel):
#     """Response returned after evaluating the EWMA sampling decision."""

#     decision: str = Field(..., description="High-level recommendation (Normal, Suspect, etc.)")
#     S_t: float = Field(..., description="Updated EWMA")
#     UCL: Optional[float] = Field(None, description="Upper control limit used for decision")
#     sigma_EWMA: float = Field(..., description="EWMA sigma used in the control chart")
#     reason: str = Field(..., description="Human-readable rationale for the decision")
#     actions: List[str] = Field(..., description="Actionable next steps for operators")