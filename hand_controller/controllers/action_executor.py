from __future__ import annotations
from typing import Iterable

from .actions import Action, MoveRelative, Click, DoubleClick, MouseDown, MouseUp, KeyPress, KeyDown, KeyUp, Hotkey


def execute_actions(actions: Iterable[Action]) -> None:
    import pyautogui

    pyautogui.FAILSAFE = False
    for act in actions:
        if isinstance(act, MoveRelative):
            pyautogui.moveRel(act.dx, act.dy, _pause=False)
        elif isinstance(act, Click):
            pyautogui.mouseDown(button=act.button, _pause=False)
            pyautogui.mouseUp(button=act.button, _pause=False)
        elif isinstance(act, DoubleClick):
            pyautogui.click(button=act.button, clicks=2, interval=0.12, _pause=False)
        elif isinstance(act, MouseDown):
            pyautogui.mouseDown(button=act.button, _pause=False)
        elif isinstance(act, MouseUp):
            pyautogui.mouseUp(button=act.button, _pause=False)
        elif isinstance(act, KeyPress):
            pyautogui.press(act.key, _pause=False)
        elif isinstance(act, KeyDown):
            pyautogui.keyDown(act.key, _pause=False)
        elif isinstance(act, KeyUp):
            pyautogui.keyUp(act.key, _pause=False)
        elif isinstance(act, Hotkey):
            pyautogui.hotkey(*act.keys, _pause=False)
