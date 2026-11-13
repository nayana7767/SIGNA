# SIGNA web prototype validation

Run date: 2026-11-12. The test target was the extracted `SIGNA_Phase2\application_source\Application`; the existing `.venv` under `OneDrive\Desktop\ISL_Project` supplied OpenCV, MediaPipe, and model dependencies. Existing pretrained models and source recordings were not modified. Normal application mode retains frames in memory only. Four stills were saved separately for this requested diagnostic in `Application\diagnostics_tmp\camera_20261112_214104`; no video was saved.

## Passed

- Python compilation for the web app and tests — passed.
- JavaScript syntax check for `web_app/index.html` — passed.
- Web app tests — **7/7 passed**: existing Phase 2 model and labels; settings match; thresholded multi-window stabilization; preview overlay draws synthetic landmarks without changing the input frame; empty overlay behavior; all five existing sentence outputs; unsupported sentence remains unsupported.
- In-process HTTP smoke test — `GET /`, `/api/health`, and `/api/sentence-tests` returned successfully; model and exact labels loaded; sentence rules **5/5 passed**.
- Live app camera/preview smoke test — camera connected, **5 frames received and decoded**, the landmark diagnostic state was returned, and `/api/preview.mjpeg` returned HTTP 200 with a complete JPEG part. `video_files_saved=false`.
- ESP32 `/status` — HTTP 200 and `camera_ready=true`; 640×480, grayscale, IR enabled, 90% target. The stream used the expected multipart MJPEG boundary and decoded without errors.
- Four still camera frames were inspected and measured. Each is 480×640×3 `uint8`; all BGR channel means match exactly, saturation is 0, grayscale mean is about 167–168 and standard deviation about 54, with 1st–99th percentile around 55–59 to 254. The image is not simply black or low contrast. Visual inspection shows a tilted ceiling, wall, window and ceiling fan; no person, face, torso, shoulders or hands are visible.
- MediaPipe input audit — app sends contiguous `(480, 640, 3)` `uint8` RGB in SRGB format after OpenCV BGR→RGB conversion. On a grayscale source the channel values are equal, so the conversion is valid and has no channel-order effect. No mirroring, rotation, crop or contrast adjustment is applied. The live task modes are VIDEO, two hands at 0.50 confidence, one pose at 0.60 confidence, pose every three processed frames, and increasing monotonic timestamps.
- Exact replay preprocessing comparison — `phase2.extract.extract_video()` and its `DualLandmarkEngine`/`pilot` feature path detected hands and poses on the existing training replays: GO **23/82 hand-present frames, 28/82 pose frames**; HELLO **21/81 hand-present frames, 27/81 pose frames**. Replay and camera both use the same BGR→RGB task input and Phase 2 feature path. The model preprocessing was left unchanged.
- Root cause for the zero live landmarks — confirmed by the saved actual frames: the camera is aimed upward at the ceiling, outside any signer’s field of view. MediaPipe initialized without landmark runtime errors. This explains why it returned 0 hands and 0 poses; grayscale/IR is not established as the cause.
- Camera mode investigation — camera root page states grayscale and IR PWM target 90%; read-only `GET /control` returns 404. No ESP32 firmware source (`.ino`, `.cpp`, or `.h`) was found in the inspected application or project tree. A visible-color mode could not be safely configured or tested from the available project.
- Sentence composer was rerun for `HELLO`, `THANK_YOU`, `WHERE YOU GO`, `YOU WHERE GO`, and `I TOMORROW SCHOOL GO`: **5/5 passed**.

Frame captures and measured properties are in [diagnostics_tmp/camera_20261112_214104](../diagnostics_tmp/camera_20261112_214104/README.txt). For example, [frame_01.jpg](../diagnostics_tmp/camera_20261112_214104/frame_01.jpg) shows the current camera aim.

## Failed

- **Live hand detection: 0 detections.** This is a failed readiness condition, with the measured cause being no signer in frame.
- **Live pose detection: 0 detections.** This is a failed readiness condition, with the measured cause being no signer/body in frame.
- Individual live recognition trials and live accuracy: no valid hands/shoulders were available, so none of GO, HELLO, I, SCHOOL, THANK_YOU, TOMORROW, WHERE, YOU was scored. The UI does not mark any as passed.

## Not tested

- Repeat trials for the eight signs and empirical live word accuracy; requires a signer to stand in the camera field of view, upright with shoulders and both hands visible. Per-word UI retains every actual stabilized expected/predicted trial; manual text remains separate.
- Any image-processing workaround: none was justified by evidence, so the training preprocessing was preserved. No transformed camera frame was adopted.
- Browser microphone and audible speech output in a live browser.
- Visual sign playback; there are no supplied signer-verified ISL clips.

## Hardware dependent

- The current camera needs to be physically aimed at the signer before detections can be demonstrated. Its available root/status endpoints expose configuration facts, while `/control` is unavailable; hardware support for visible-light color mode remains unverified.
- The display receiver can be sent text through the existing `/update?message=...` protocol, but actual acknowledgment requires its HTTP 200 JSON `{"ok":true}` response. Display firmware, touchscreen input and ESP32 speaker playback were not available for this test.

## Existing project suites

These project suites were rerun after the diagnostic changes:

- `Application\tests`: **26/27 passed**. The remaining camera diagnostic subprocess returned exit code 2 without stderr because its child received no test frames.
- `Application\tests_dual_v1`: **31/34 passed**. Three legacy tests remain blocked by environment/path issues: two need TensorFlow (not installed in the selected `.venv`), and one references a missing old `S:\Samanvay\outputs\final_integrated_prototype.py` path.

The Phase 2 model’s previously reported **20/24 (83.3%)** is from held-out isolated clips, not a live-camera result or an 85% guarantee. Its Ridge scores are not calibrated probabilities; the web app reports only the raw decision-score gap.
