from __future__ import annotations
from typing import Any
import mediapipe as mp


class HandTracker:
    def __init__(self, max_num_hands: int = 2, min_detection_confidence: float = 0.7, min_tracking_confidence: float = 0.7):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    @property
    def connections(self):
        return self.mp_hands.HAND_CONNECTIONS

    def process(self, rgb_frame):
        return self.hands.process(rgb_frame)

    def extract_hands(self, result) -> list[dict[str, Any]]:
        hands_list: list[dict[str, Any]] = []
        if result.multi_hand_landmarks and result.multi_handedness:
            for lm, hd in zip(result.multi_hand_landmarks, result.multi_handedness):
                hands_list.append({"label": hd.classification[0].label, "landmarks": lm})
        return hands_list

    def close(self) -> None:
        self.hands.close()
