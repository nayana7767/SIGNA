# SIGNA bidirectional communication prototype

This local web app integrates the existing Phase 2 eight-label ISL pilot. Sign recognition uses the pretrained `phase2/pilot_model.npz` and the existing `dual_isl_v1.pilot.describe` feature pipeline. The ESP32 MJPEG stream is the only camera source; the laptop webcam is never opened. Sampled frames and landmarks remain in a short in-memory window and are discarded when stopped. No video is saved.

## Frontend

The dashboard is implemented in React under `web_app/react`. Its JSX, CSS and
browser-side service integration live in `react/src`; the existing Python
service continues to provide camera recognition and message APIs.

For frontend development, run the Python service and the React dev server in
separate PowerShell windows. From `web_app/react`, install the dependencies
once, then start the dev server:

```powershell
npm install
npm run dev
```

Vite proxies `/api` and `/assets/signs` to the Python service on port 8765.
For a standalone launch, create the production frontend first:

```powershell
npm install
npm run build
```

Run those commands while in `web_app/react`.

The Python service then serves the React build at `http://127.0.0.1:8765`.

## Launch on this computer

Open PowerShell and run:

```powershell
$app = 'C:\Users\jyoth\Documents\Codex\SIGNA_Phase2\application_source\Application'
$project = 'C:\Users\jyoth\OneDrive\Desktop\ISL_Project'
$python = Join-Path $project '.venv\Scripts\python.exe'
Set-Location (Join-Path $app 'web_app\react')
npm run build
Set-Location (Join-Path $app 'web_app')
& $python .\run_webapp.py --application-dir $app --project-dir $project --host 0.0.0.0 --port 8765
```

Keep the PowerShell window open. On this computer, visit [http://127.0.0.1:8765](http://127.0.0.1:8765); from another device on the same Wi-Fi/LAN, visit [http://192.168.0.110:8765](http://192.168.0.110:8765). If this computer uses a different project location, change only `$project` to the folder containing `.venv`, `hand_landmarker.task`, `pose_landmarker.task`, and `MiVOLO`. The extracted Phase 2 `$app` path should remain as written.

Required installed packages are NumPy, OpenCV, MediaPipe, Requests, PyTorch, Transformers, Hugging Face Hub, and Ultralytics. The checked `.venv` already contains these. Age estimation uses the local MiVOLO directory and YOLO face/person checkpoint under the project folder. It starts on the first live frame, calibrates for 10 seconds, then terminates its inference process; if model loading fails, the audience age is locked as unknown. **Continue with age unknown** is available during calibration.

## Run checks

```powershell
& $python -m unittest discover -s (Join-Path $app 'web_app\tests') -v
& $python -m unittest discover -s (Join-Path $app 'tests') -v
& $python -m unittest discover -s (Join-Path $app 'tests_dual_v1') -v
```

## What the app does

- **Sign → Speech:** configurable ESP32 MJPEG URL (default `http://192.168.0.105/stream`), local preview proxy with hand/pose landmark overlay, live camera/frame/task/input/error diagnostics, hand and shoulder landmark tracking, three-window stable predictions, commit/rearm, undo, clear, sentence preview, supported sentence history, browser text-to-speech, and optional display-controller message send.
- **Speech → Sign:** browser microphone speech recognition when supported, editable typed text fallback, exact phrase mapping for the model's eight labels, and only signer-approved licensed clips listed as verified in `assets/signs/manifest.json`.
- **Testing & setup:** eight repeatable camera-only label trials with per-trial expected/predicted labels, raw uncalibrated score gaps and pass/fail results; sentence-rule checks; and a separate manual composer. Manual words are never counted as live-camera test results.

The existing model supports **GO, HELLO, I, SCHOOL, THANK_YOU, TOMORROW, WHERE, YOU** only. The recorded evaluation was 20/24 held-out clips (83.3%; macro F1 0.838). It is a small isolated-clip result, not a live accuracy estimate or an 85% guarantee. The classifier returns Ridge decision scores, not calibrated probabilities; the UI shows their raw top-score gap and never calls it confidence. The configured margin threshold is therefore an uncalibrated screening control.

Sentence output is restricted to the existing rules: `HELLO`; `THANK_YOU`; `WHERE YOU GO`; `YOU WHERE GO`; and `I TOMORROW SCHOOL GO`. Other sequences remain unsupported rather than being rewritten as invented English. The age estimate does not generate or change the English sentence; users select the audience wording preference themselves.

## Current limits and device protocol

There are no bundled verified ISL signing videos. `assets/signs/manifest.json` names the eight needed labels and intentionally marks each clip missing/unverified. Supply signer-approved ISL clips there before the app will display them. The speech recognizer is the browser's Web Speech implementation where available; browser/provider audio handling depends on that browser. The Speak action uses the computer's browser audio output.

The existing `dual_isl_v1.signa.SignaSender` sends a completed sentence as an HTTP GET to `<display-base>/update?message=...` and marks it acknowledged only when the device responds HTTP 200 with JSON `{"ok":true}`. This updates the receiving display message only; the available project source does not include touchscreen firmware or a speaker/TTS trigger command. Configure a display base URL in the app only when its receiver implements this endpoint. Physical display, touch input, and ESP32 speaker output still require the corresponding firmware and hardware validation.

If camera reception shows frames but no landmarks, inspect the diagnostics preview and confirm the signer, face, shoulders and hands are in frame. The diagnostics panel distinguishes decoded frames from actual detections and shows the exact RGB input, task modes, errors and landmark overlay; it does not convert a camera connection into a successful recognition claim. The current supplied ESP32 image shows a tilted ceiling view, which explains the observed zero detections. That firmware reports grayscale and IR=90%; its `/control` path returns 404, and camera firmware source was not present to change modes. The camera may be on another Wi-Fi subnet; update the stream URL in the UI or `settings.json`. All tunable sampling, stabilization, detector-confidence, camera-default, and score-gap values are in `settings.json`.
