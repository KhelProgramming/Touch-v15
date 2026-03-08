# Hand Controller Functional Merged

This is a cleaned, merged repo built from your two versions:
- **team repo backbone**: threaded pipeline, Geo18, MLP loading, cleaner separation
- **solo repo feel**: relative mouse movement, sticky hold/drag, hover-based keyboard, smoother live interaction

## What this repo keeps
- MediaPipe hand tracking
- Geo18 feature extraction
- global MLP inference
- closest-hand selection with hysteresis
- 4-stage runtime pipeline:
  - capture
  - infer
  - logic
  - execute
- optional PyQt overlay/control window

## What this repo removes
- personalized user-lock calibration
- old experimental benchmark folders
- old duplicate controllers and legacy rule-based layers

## Install
```bash
pip install -r requirements.txt
```

## Run
GUI mode:
```bash
python run.py
```

Headless mode:
```bash
python run.py --headless
```

## Default gesture labels expected from the MLP
- `idle`
- `left_click`
- `right_click`
- `hold`
- `press`
- `toggle`
- `undo`
- `redo`

If your trained model uses different label names, update `hand_controller/config.py`.
