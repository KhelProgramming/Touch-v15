from __future__ import annotations
from ..config import GatePolicy


def accept(pred_label: str, p1: float, margin: float, policy: GatePolicy) -> bool:
    if pred_label.lower() == "idle":
        return True
    return (p1 >= policy.min_p1) and (margin >= policy.min_margin)
