"""Local SIGNA prototype server with live, in-memory Phase 2 recognition."""
from __future__ import annotations

import argparse
from collections import deque
import json
import logging
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

APP = Path(__file__).resolve().parent
FRONTEND_DIST = APP / "react" / "dist"
SETTINGS = json.loads((APP / "settings.json").read_text(encoding="utf-8"))
DEFAULT_APPLICATION = Path(r"C:\Users\jyoth\Documents\Codex\SIGNA_Phase2\application_source\Application")
DEFAULT_PROJECT = Path(r"C:\Users\jyoth\OneDrive\Desktop\ISL_Project")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def hand_features(result):
    import numpy as np
    slots = np.zeros((2, 64), np.float32)
    if result is not None:
        for side, slot in zip(("left", "right"), slots):
            matches = [hand for hand, categories in zip(result.hand_landmarks, result.handedness)
                       if categories and categories[0].category_name.lower() == side]
            if len(matches) != 1 or len(matches[0]) != 21:
                continue
            points = np.asarray([(p.x, p.y, p.z) for p in matches[0]], np.float32)
            if np.isfinite(points).all() and np.any(points != points[0]):
                slot[0] = 1
                slot[1:] = points.ravel()
    return slots.ravel()


def pose_anchor(result, aspect):
    import numpy as np
    if result is None or not result.pose_landmarks:
        return np.zeros(3, np.float32)
    left, right = (result.pose_landmarks[0][index] for index in (11, 12))
    coords = np.asarray([(point.x, point.y * aspect) for point in (left, right)], np.float32)
    scale = np.linalg.norm(coords[0] - coords[1])
    if min(left.visibility, right.visibility) < .45 or not np.isfinite(coords).all() or scale < .04:
        return np.zeros(3, np.float32)
    return np.asarray((*coords.mean(axis=0), scale), np.float32)


HAND_CONNECTIONS = ((0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
                    (5, 9), (9, 10), (10, 11), (11, 12), (9, 13), (13, 14), (14, 15),
                    (15, 16), (13, 17), (0, 17), (17, 18), (18, 19), (19, 20))
POSE_CONNECTIONS = ((11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
                    (11, 23), (12, 24), (23, 24))


def draw_landmarks(frame, hand_result, pose_result, cv2_module=None):
    """Return a preview-only overlay; never modify the recognition frame."""
    if cv2_module is None:
        import cv2 as cv2_module
    annotated = frame.copy()
    height, width = annotated.shape[:2]

    def point(landmark):
        return (max(0, min(width - 1, round(landmark.x * width))),
                max(0, min(height - 1, round(landmark.y * height))))

    if hand_result is not None:
        for landmarks in getattr(hand_result, "hand_landmarks", ()):
            for first, second in HAND_CONNECTIONS:
                cv2_module.line(annotated, point(landmarks[first]), point(landmarks[second]),
                                (40, 220, 255), 2, cv2_module.LINE_AA)
            for landmark in landmarks:
                cv2_module.circle(annotated, point(landmark), 3, (30, 70, 255), -1, cv2_module.LINE_AA)
    if pose_result is not None and getattr(pose_result, "pose_landmarks", None):
        landmarks = pose_result.pose_landmarks[0]
        for first, second in POSE_CONNECTIONS:
            if min(float(landmarks[first].visibility), float(landmarks[second].visibility)) >= .35:
                cv2_module.line(annotated, point(landmarks[first]), point(landmarks[second]),
                                (80, 255, 100), 2, cv2_module.LINE_AA)
        for index in (11, 12, 13, 14, 15, 16, 23, 24):
            if float(landmarks[index].visibility) >= .35:
                cv2_module.circle(annotated, point(landmarks[index]), 4,
                                  (80, 255, 100), -1, cv2_module.LINE_AA)
    return annotated


class PredictionStabilizer:
    """Require repeated matching model outputs above the configured raw-score gap."""
    def __init__(self, windows: int, minimum_margin: float):
        self.windows = max(1, int(windows))
        self.minimum_margin = float(minimum_margin)
        self.recent = deque(maxlen=self.windows)

    def reset(self):
        self.recent.clear()

    def observe(self, label: str, margin: float) -> bool:
        self.recent.append((label, float(margin)))
        return (len(self.recent) == self.windows
                and len({item[0] for item in self.recent}) == 1
                and all(item[1] >= self.minimum_margin for item in self.recent))


class LiveRecognizer:
    """Run the pilot on a rolling RAM-only window from an MJPEG camera."""
    def __init__(self, application_dir: Path, project_dir: Path, settings=None):
        self.application_dir = application_dir.resolve()
        self.project_dir = project_dir.resolve()
        self.settings = dict(SETTINGS if settings is None else settings)
        for path in (self.application_dir / "phase2" / "pilot_model.npz",
                     self.project_dir / "hand_landmarker.task", self.project_dir / "pose_landmarker.task"):
            if not path.is_file():
                raise FileNotFoundError(f"Required model/task file missing: {path}")
        sys.path.insert(0, str(self.application_dir))
        from dual_isl_v1.pilot import PilotModel
        self.model = PilotModel(self.application_dir / "phase2" / "pilot_model.npz")
        if tuple(self.model.labels) != tuple(self.settings["model_labels"]):
            raise ValueError("settings.json model_labels do not match phase2/pilot_model.npz")
        for key in ("age_seconds", "rolling_buffer_seconds", "sample_fps",
                    "inference_interval_seconds", "stability_windows", "minimum_tracked_frames",
                    "minimum_tracked_seconds", "hand_confidence", "pose_confidence", "pose_every"):
            value = float(self.settings[key])
            if not (value > 0 and value < float("inf")):
                raise ValueError(f"settings.json {key} must be positive and finite")
        if float(self.settings["minimum_score_margin"]) < 0:
            raise ValueError("settings.json minimum_score_margin must be nonnegative")
        self.lock = threading.RLock()
        self.stop_event = None
        self.thread = None
        self.camera = None
        self.latest_preview_frame = None
        self.acknowledged = None
        self.age = None
        self.hardware = {"status": "Not configured", "acknowledged": False}
        self.state = {"running": False, "status": "Ready", "prediction": None,
                      "stable": False, "labels": list(self.model.labels), "frames": 0,
                      "window_seconds": 0, "saved_video": False, "error": None,
                      "camera_connected": False, "frames_received": 0, "frames_decoded": 0,
                      "hand_landmarks_detected": False, "hand_frames": 0,
                      "pose_landmarks_detected": False, "pose_frames": 0,
                      "hand_detections_total": 0, "latest_hand_count": 0,
                      "latest_pose_detected": False, "pose_anchor_frames": 0,
                      "landmark_errors": 0,
                      "last_landmark_error": None, "frame_shape": None,
                      "frame_dtype": None, "frame_grayscale": None,
                      "mp_input_status": "Waiting for camera", "tasks_status": "Not started",
                      "model_loaded": True, "recognition_active": False,
                      "age_status": "Not started", "age_locked": False,
                      "age_estimate": None, "age_samples": 0, "score_margin": None}

    def snapshot(self):
        with self.lock:
            state = dict(self.state)
            age = self.age
        state["age_remaining"] = (max(0.0, age.deadline - time.monotonic())
                                  if age is not None and age.deadline is not None and not age.locked
                                  else None)
        return state

    def start(self, stream_url: str):
        from urllib.parse import urlsplit
        parsed = urlsplit(stream_url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError("Enter a full HTTP(S) camera stream URL")
        with self.lock:
            if self.state["running"]:
                if self.state.get("stream_url") == stream_url:
                    return self.snapshot()
                raise RuntimeError("Stop live recognition before changing the camera URL")
            self.stop_event = threading.Event()
            self.acknowledged = None
            from dual_isl_v1.age_runtime import AgeController
            from dual_isl_v1.reference_runtime import Config
            age_scratch = Path(tempfile.gettempdir()) / "signa-age-runtime"
            cfg = Config(project_dir=str(age_scratch), stream_url=stream_url,
                         age_enabled=True, age_seconds=float(self.settings["age_seconds"]), age_every=4,
                         age_min_interval=.5, age_startup_timeout=180.0,
                         age_model_id=str(self.project_dir / "MiVOLO" / "models" / "mivolo_v2"),
                         detector_file=str(self.project_dir / "MiVOLO" / "models" / "yolov8x_person_face.pt"),
                         hand_mode="video", pose_every=3, tts_enabled=False,
                         mic_enabled=False, oled_backend="off")
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            self.age = AgeController(cfg)
            self.age.start()
            self.state.update(running=True, status="Connecting to camera", prediction=None,
                              stable=False, frames=0, window_seconds=0, error=None,
                              stream_url=stream_url, camera_connected=False,
                              frames_received=0, frames_decoded=0, hand_landmarks_detected=False,
                              hand_frames=0, pose_landmarks_detected=False, pose_frames=0,
                              hand_detections_total=0, latest_hand_count=0,
                              latest_pose_detected=False, pose_anchor_frames=0, landmark_errors=0,
                              last_landmark_error=None, frame_shape=None, frame_dtype=None,
                              frame_grayscale=None, mp_input_status="Waiting for camera",
                              tasks_status="Loading hand and pose tasks",
                              recognition_active=False, age_status="Warming age models",
                              age_locked=False, age_estimate=None, age_samples=0, score_margin=None)
            self.thread = threading.Thread(target=self._run, args=(stream_url, self.stop_event),
                                           daemon=True, name="SIGNA-live-recognition")
            self.thread.start()
        return self.snapshot()

    def serve_preview(self, handler):
        import cv2
        with self.lock:
            camera, stop_event = self.camera, self.stop_event
        if camera is None or stop_event is None:
            payload = b"Camera is not started"
            handler.send_response(503)
            handler.send_header("Content-Type", "text/plain; charset=utf-8")
            handler.send_header("Content-Length", str(len(payload)))
            handler.end_headers()
            handler.wfile.write(payload)
            return
        handler.send_response(200)
        handler.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        handler.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        handler.send_header("Connection", "close")
        handler.end_headers()
        after = 0
        try:
            while not stop_event.is_set():
                packet = camera.read(after=after, timeout=.8)
                if packet is None:
                    continue
                after = packet.sequence
                frame = packet.frame
                with self.lock:
                    preview_frame = self.latest_preview_frame
                if preview_frame is not None:
                    frame = preview_frame
                if frame.shape[1] > 640:
                    frame = cv2.resize(frame, (640, round(frame.shape[0] * 640 / frame.shape[1])),
                                       interpolation=cv2.INTER_AREA)
                ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 78])
                if not ok:
                    continue
                data = encoded.tobytes()
                handler.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                                    + str(len(data)).encode("ascii") + b"\r\n\r\n" + data + b"\r\n")
        except (BrokenPipeError, ConnectionResetError, OSError):
            return

    def stop(self):
        with self.lock:
            event = self.stop_event
            thread = self.thread
        if event:
            event.set()
        if self.age is not None:
            self.age.stop()
        if thread and thread.is_alive():
            thread.join(timeout=8)
        with self.lock:
            self.state.update(running=False, status="Stopped", prediction=None, stable=False,
                              frames=0, window_seconds=0, error=None, camera_connected=False,
                              hand_landmarks_detected=False, latest_hand_count=0,
                              pose_landmarks_detected=False, latest_pose_detected=False,
                              tasks_status="Stopped", mp_input_status="Waiting for camera")
            self.latest_preview_frame = None
            self.acknowledged = None
            self.stop_event = None
            self.thread = None
            self.age = None
        return self.snapshot()

    def skip_age(self):
        with self.lock:
            age = self.age
        if age is not None and not age.locked:
            age.lock_unknown("SKIPPED BY USER")
        return self.snapshot()

    def compose(self, labels):
        from dual_isl_v1.sentences import compose_english, is_gloss
        if not isinstance(labels, list) or not all(is_gloss(x) for x in labels):
            raise ValueError("labels must be a list of uppercase glosses")
        sentence = compose_english(labels)
        return {"labels": labels, "sentence": sentence, "supported": sentence is not None}

    def send_hardware(self, base_url, message):
        from dual_isl_v1.signa import SignaSender, update_url
        update_url(base_url)
        if not isinstance(message, str) or not message.strip():
            raise ValueError("Finish a supported sentence before sending")
        sender = SignaSender(base_url)
        sender.send(message.strip())
        with self.lock:
            self.hardware = {"status": sender.status, "acknowledged": False,
                             "base_url": base_url, "message": message.strip(), "sender": sender}
        return self.hardware_status()

    def hardware_status(self):
        with self.lock:
            state = dict(self.hardware)
        sender = state.pop("sender", None)
        if sender is not None:
            state["status"] = sender.status
            state["acknowledged"] = sender.status == "Sent to SIGNA"
        return state

    def _run(self, stream_url, stop_event):
        import cv2
        import mediapipe as mp
        import numpy as np
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision
        from dfr1154_camera import CameraConfig, MJPEGCamera
        from dual_isl_v1.pilot import describe

        camera = None
        hands_task = pose_task = None
        age = self.age
        try:
            camera = MJPEGCamera(CameraConfig(stream_url, stale_after=1.5)).start()
            with self.lock:
                self.camera = camera
            hands_task = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
                base_options=mp_python.BaseOptions(model_asset_path=str(self.project_dir / "hand_landmarker.task")),
                running_mode=vision.RunningMode.VIDEO, num_hands=2,
                min_hand_detection_confidence=float(self.settings["hand_confidence"]),
                min_hand_presence_confidence=float(self.settings["hand_confidence"]),
                min_tracking_confidence=float(self.settings["hand_confidence"])))
            pose_task = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
                base_options=mp_python.BaseOptions(model_asset_path=str(self.project_dir / "pose_landmarker.task")),
                running_mode=vision.RunningMode.VIDEO, num_poses=1,
                min_pose_detection_confidence=float(self.settings["pose_confidence"]),
                min_pose_presence_confidence=float(self.settings["pose_confidence"]),
                min_tracking_confidence=float(self.settings["pose_confidence"])))
            with self.lock:
                self.state["tasks_status"] = (
                    f"Hand VIDEO mode · 2 hands · {self.settings['hand_confidence']:.2f} confidence; "
                    f"Pose VIDEO mode · 1 pose · {self.settings['pose_confidence']:.2f} confidence")
            sample_fps = max(1, int(self.settings["sample_fps"]))
            frames = deque(maxlen=max(2, round(float(self.settings["rolling_buffer_seconds"]) * sample_fps)))
            after = 0
            timestamp_ms = 0
            frame_count = 0
            pose_count = 0
            pose_anchor_count = 0
            last_sample = 0.0
            last_predict = 0.0
            hands_off_since = None
            stabilizer = PredictionStabilizer(self.settings["stability_windows"],
                                                self.settings["minimum_score_margin"])
            with self.lock:
                self.state["status"] = "Live · warming up"
            while not stop_event.is_set():
                packet = camera.read(after=after, timeout=.5)
                if age is not None:
                    age.poll()
                if packet is None:
                    stats = camera.stats()
                    with self.lock:
                        self.state.update(camera_connected=stats.get("state") == "streaming",
                                          frames_received=stats.get("received", 0),
                                          frames_decoded=stats.get("decoded", 0),
                                          age_status=age.status.get() if age else "Unavailable",
                                          age_locked=bool(age and age.locked),
                                          age_estimate=age.age if age else None,
                                          age_samples=len(age.samples) if age else 0,
                                          status="Waiting for fresh camera frame")
                    continue
                after = packet.sequence
                now = packet.received_at
                if now - last_sample < 1 / sample_fps:
                    continue
                last_sample = now
                frame = packet.frame
                height, width = frame.shape[:2]
                if width > 640:
                    frame = cv2.resize(frame, (640, round(height * 640 / width)), interpolation=cv2.INTER_AREA)
                    height, width = frame.shape[:2]
                timestamp_ms = max(timestamp_ms + 1, round(now * 1000))
                hand_result = pose_result = None
                landmark_error = None
                if frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3:
                    landmark_error = f"Invalid camera frame: {frame.shape}/{frame.dtype}; expected H×W×3 uint8"
                    input_status = landmark_error
                    grayscale_input = None
                else:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    channel_delta = max(
                        int(cv2.absdiff(frame[:, :, 0], frame[:, :, 1]).max()),
                        int(cv2.absdiff(frame[:, :, 1], frame[:, :, 2]).max()),
                        int(cv2.absdiff(frame[:, :, 0], frame[:, :, 2]).max()))
                    grayscale_input = channel_delta <= 1
                    rgb = np.ascontiguousarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                    input_status = (f"MediaPipe SRGB {rgb.shape} {rgb.dtype} C-contiguous; "
                                    f"source BGR {width}×{height} {frame.dtype}; "
                                    f"grayscale={'yes' if grayscale_input else 'no'} (max channel delta {channel_delta}), "
                                    f"mean={float(gray.mean()):.1f}, std={float(gray.std()):.1f}; "
                                    f"VIDEO timestamps={timestamp_ms}ms; raw orientation, no mirror")
                    try:
                        hand_result = hands_task.detect_for_video(image, timestamp_ms)
                    except Exception as exc:
                        landmark_error = f"HandLandmarker: {type(exc).__name__}: {exc}"
                    frame_count += 1
                    if frame_count % max(1, int(self.settings["pose_every"])) == 0:
                        try:
                            pose_result = pose_task.detect_for_video(image, timestamp_ms)
                        except Exception as exc:
                            landmark_error = f"PoseLandmarker: {type(exc).__name__}: {exc}"
                with self.lock:
                    self.state.update(frame_shape=[height, width, int(frame.shape[2])]
                                      if frame.ndim == 3 else list(frame.shape),
                                      frame_dtype=str(frame.dtype), frame_grayscale=grayscale_input,
                                      mp_input_status=input_status)
                    if landmark_error:
                        self.state["landmark_errors"] += 1
                        self.state["last_landmark_error"] = landmark_error
                hand_vector = hand_features(hand_result)
                pose_vector = pose_anchor(pose_result, height / width)
                pose_detected = bool(pose_result is not None and pose_result.pose_landmarks)
                if pose_detected:
                    pose_count += 1
                if pose_vector[2] > 0:
                    pose_anchor_count += 1
                if age is not None:
                    age.submit(frame, now, frame_count, every=4)
                    age.poll()
                frames.append((now, hand_vector, pose_vector, height / width))
                recent = list(frames)
                hands_seen = [i for i, row in enumerate(recent) if row[1][0] or row[1][64]]
                window_seconds = (recent[-1][0] - recent[0][0]) if len(recent) > 1 else 0
                if not hands_seen:
                    hands_off_since = hands_off_since or now
                    if now - hands_off_since >= .45:
                        stabilizer.reset()
                        with self.lock:
                            self.acknowledged = None
                else:
                    hands_off_since = None
                camera_stats = camera.stats()
                hand_detected = bool(hand_vector[0] or hand_vector[64])
                annotated = draw_landmarks(frame, hand_result, pose_result, cv2)
                with self.lock:
                    self.latest_preview_frame = annotated
                    self.state.update(status=("Live · age calibration" if age is not None and not age.locked
                                              else "Live · recognizing rolling window"),
                                      frames=frame_count, window_seconds=round(window_seconds, 1),
                                      camera_connected=camera_stats.get("state") == "streaming",
                                      frames_received=camera_stats.get("received", 0),
                                      frames_decoded=camera_stats.get("decoded", 0),
                                      hand_landmarks_detected=hand_detected,
                                      hand_frames=sum(1 for row in recent if row[1][0] or row[1][64]),
                                      hand_detections_total=(self.state["hand_detections_total"]
                                          + (len(hand_result.hand_landmarks) if hand_result is not None else 0)),
                                      latest_hand_count=(len(hand_result.hand_landmarks)
                                          if hand_result is not None else 0),
                                      pose_landmarks_detected=pose_detected, pose_frames=pose_count,
                                      latest_pose_detected=pose_detected,
                                      pose_anchor_frames=pose_anchor_count,
                                      model_loaded=True,
                                      recognition_active=bool(age is None or age.locked),
                                      age_status=age.status.get() if age else "Unavailable",
                                      age_locked=bool(age and age.locked),
                                      age_estimate=age.age if age else None,
                                      age_samples=len(age.samples) if age else 0)
                if age is not None and not age.locked:
                    continue
                if (len(hands_seen) < int(self.settings["minimum_tracked_frames"])
                        or recent[hands_seen[-1]][0] - recent[hands_seen[0]][0] < float(self.settings["minimum_tracked_seconds"])
                        or now - last_predict < float(self.settings["inference_interval_seconds"])):
                    continue
                last_predict = now
                # Use only a short recent sequence; arrays remain in process memory.
                clip = recent[-min(len(recent), round(float(self.settings["rolling_buffer_seconds"]) * sample_fps)):]
                times = np.asarray([row[0] for row in clip], np.float64)
                hand_values = np.stack([row[1] for row in clip])
                pose_values = np.stack([row[2] for row in clip])
                try:
                    features = np.stack([describe(times, hand_values, pose_values, clip[0][3], mirrored=m)
                                         for m in (False, True)])
                except ValueError:
                    continue
                scores = self.model.scores(features).mean(axis=0)
                order = np.argsort(scores)
                label = self.model.labels[int(order[-1])]
                score_margin = float(scores[order[-1]] - scores[order[-2]])
                stable = stabilizer.observe(label, score_margin)
                with self.lock:
                    prediction = label if stable and label != self.acknowledged else None
                    self.state.update(prediction=prediction, stable=prediction is not None,
                                      score_margin=score_margin,
                                      status=(f"Live suggestion · {label}" if prediction else
                                              "Sign held · release to rearm" if stable else
                                              "Live · stabilizing prediction"))
        except Exception as exc:
            logging.exception("Live recognition stopped")
            with self.lock:
                error = f"{type(exc).__name__}: {exc}"
                self.state.update(status="Recognition unavailable", error=error,
                                  tasks_status=f"Task/worker failure: {error}")
        finally:
            stop_event.set()
            for task in (hands_task, pose_task):
                if task is not None:
                    try:
                        task.close()
                    except Exception:
                        pass
            if camera is not None:
                try:
                    camera.stop()
                except Exception:
                    logging.exception("Camera shutdown issue")
            with self.lock:
                self.camera = None
                self.latest_preview_frame = None
            if age is not None:
                try:
                    age.stop()
                except Exception:
                    logging.exception("Age process shutdown issue")
            with self.lock:
                self.state["running"] = False


class Handler(SimpleHTTPRequestHandler):
    recognizer = None
    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIST), **kwargs)

    def translate_path(self, path):
        if path.startswith("/assets/signs/"):
            from urllib.parse import unquote, urlsplit
            relative = Path(unquote(urlsplit(path).path).lstrip("/"))
            if ".." in relative.parts:
                return str(APP / "missing-asset")
            return str(APP / relative)
        return super().translate_path(path)

    def log_message(self, fmt, *args):
        logging.info("%s - %s", self.address_string(), fmt % args)

    def _json(self, status, data):
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == "/api/preview.mjpeg":
            return self.recognizer.serve_preview(self)
        if self.path == "/api/state":
            state = self.recognizer.snapshot()
            state["hardware"] = self.recognizer.hardware_status()
            return self._json(200, state)
        if self.path == "/api/health":
            return self._json(200, {"model_loaded": True,
                                    "labels": list(self.recognizer.model.labels),
                                    "age_assets": "configured from --project-dir",
                                    "settings": self.recognizer.settings,
                                    "default_stream_url": self.recognizer.settings["camera_stream_url"],
                                    "default_display_url": self.recognizer.settings["display_base_url"],
                                    "video_files_saved": False})
        if self.path == "/api/sentence-tests":
            cases = [
                (["HELLO"], "Hello!"),
                (["THANK_YOU"], "Thank you."),
                (["WHERE", "YOU", "GO"], "Where are you going?"),
                (["YOU", "WHERE", "GO"], "Where are you going?"),
                (["I", "TOMORROW", "SCHOOL", "GO"], "I will go to school tomorrow."),
            ]
            results = [{"labels": labels, "expected": expected,
                        "actual": self.recognizer.compose(labels)["sentence"],
                        "passed": self.recognizer.compose(labels)["sentence"] == expected}
                       for labels, expected in cases]
            return self._json(200, {"results": results,
                                    "passed": sum(1 for row in results if row["passed"]),
                                    "total": len(results)})
        if self.path == "/api/hardware-status":
            return self._json(200, self.recognizer.hardware_status())
        if not FRONTEND_DIST.is_dir() and not self.path.startswith("/assets/signs/"):
            return self.send_error(503, "Build the React frontend with npm run build first.")
        return super().do_GET()

    def do_POST(self):
        if self.path not in ("/api/start", "/api/stop", "/api/ack", "/api/compose",
                             "/api/age/skip", "/api/hardware/send"):
            return self._json(404, {"error": "Unknown endpoint"})
        try:
            if self.path == "/api/stop":
                return self._json(200, self.recognizer.stop())
            if self.path == "/api/age/skip":
                return self._json(200, self.recognizer.skip_age())
            length = min(int(self.headers.get("Content-Length", "0")), 8192)
            body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            if self.path == "/api/compose":
                return self._json(200, self.recognizer.compose(body.get("labels")))
            if self.path == "/api/hardware/send":
                return self._json(200, self.recognizer.send_hardware(
                    str(body.get("base_url", "")), str(body.get("message", ""))))
            if self.path == "/api/ack":
                label = str(body.get("label", ""))
                if label not in self.recognizer.model.labels:
                    return self._json(400, {"error": "Unknown pilot label"})
                with self.recognizer.lock:
                    self.recognizer.acknowledged = label
                    self.recognizer.state.update(prediction=None, stable=False,
                                                 status="Sign added · release before repeating")
                return self._json(200, self.recognizer.snapshot())
            return self._json(200, self.recognizer.start(str(body.get("stream_url", ""))))
        except (ValueError, RuntimeError, OSError, TypeError, KeyError) as exc:
            return self._json(400, {"error": str(exc)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--application-dir", type=Path, default=DEFAULT_APPLICATION)
    parser.add_argument("--project-dir", type=Path, default=DEFAULT_PROJECT)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    recognizer = LiveRecognizer(args.application_dir, args.project_dir)
    Handler.recognizer = recognizer
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    logging.info("SIGNA prototype ready at http://%s:%s", args.host, args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        recognizer.stop()
        server.server_close()


if __name__ == "__main__":
    main()
