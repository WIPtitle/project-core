#!/usr/bin/env python3
"""
Standalone motion + person detection tuner.
Replays a video at 1 FPS showing motion and person detection results.

Usage:
    python detection_tuner.py video.mkv
"""

import sys
import cv2
import numpy as np
from ultralytics import YOLO

# ── Tunable constants ────────────────────────────────────────────────
MOTION_SENSITIVITY = 80          # 1-100  (higher = more sensitive)
DETECTION_CONFIDENCE = 75        # 1-100  (higher = stricter YOLO confidence)
# ─────────────────────────────────────────────────────────────────────

YOLO_MODEL = "yolo26n"
DETECTION_WIDTH = 640
DETECTION_HEIGHT = 360
DISPLAY_WIDTH = 1280
DISPLAY_HEIGHT = 720
DIFF_BLUR_KERNEL = 21
DIFF_BINARY_THRESHOLD = 25


def sensitivity_to_threshold(sensitivity: int) -> float:
    """Convert 1-100 sensitivity to motion ratio threshold."""
    return 0.05 * (0.02 ** (sensitivity / 100.0))


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <video_file>")
        sys.exit(1)

    video_path = sys.argv[1]
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Cannot open video: {video_path}")
        sys.exit(1)

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_skip = max(1, int(round(fps)))  # ~1 frame per second

    motion_threshold = sensitivity_to_threshold(MOTION_SENSITIVITY)
    yolo_confidence = DETECTION_CONFIDENCE / 100.0

    print(f"Motion sensitivity: {MOTION_SENSITIVITY} -> threshold: {motion_threshold:.4f}")
    print(f"YOLO confidence:    {DETECTION_CONFIDENCE} -> {yolo_confidence:.2f}")
    print(f"Video FPS: {fps:.1f}, analysing every {frame_skip} frames")
    print("Press 'q' to quit, any other key to pause/resume\n")

    model = YOLO(f"{YOLO_MODEL}.pt")
    prev_gray = None
    frame_idx = 0

    cv2.namedWindow("Detection Tuner", cv2.WINDOW_NORMAL)

    while True:
        ret, raw_frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        if frame_idx % frame_skip != 0:
            continue

        frame = cv2.resize(raw_frame, (DETECTION_WIDTH, DETECTION_HEIGHT))
        display = frame.copy()

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (DIFF_BLUR_KERNEL, DIFF_BLUR_KERNEL), 0)

        motion_detected = False
        motion_ratio = 0.0

        if prev_gray is not None:
            diff = cv2.absdiff(prev_gray, gray)
            _, diff_thresh = cv2.threshold(diff, DIFF_BINARY_THRESHOLD, 255, cv2.THRESH_BINARY)

            motion_pixels = np.count_nonzero(diff_thresh)
            total_pixels = diff_thresh.shape[0] * diff_thresh.shape[1]
            motion_ratio = motion_pixels / total_pixels
            motion_detected = motion_ratio > motion_threshold

        prev_gray = gray

        # YOLO person detection (only if motion detected)
        person_count = 0
        if motion_detected:
            results = model(frame, classes=[0], conf=yolo_confidence, verbose=False)
            boxes = results[0].boxes
            if boxes is not None and len(boxes):
                for box, conf in zip(boxes.xyxy.cpu().numpy().astype(int), boxes.conf.cpu().numpy()):
                    x1, y1, x2, y2 = box
                    cv2.rectangle(display, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(display, f"person {conf:.0%}", (x1, y1 - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                    person_count += 1

        display = cv2.resize(display, (DISPLAY_WIDTH, DISPLAY_HEIGHT))

        # HUD (drawn after resize so text is readable)
        cv2.putText(display, f"MOTION: {'YES' if motion_detected else 'no'}  ratio={motion_ratio:.4f}  thr={motion_threshold:.4f}",
                    (16, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
        cv2.putText(display, f"PERSONS: {person_count}  (conf>={yolo_confidence:.0%})",
                    (16, 76), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
        cv2.putText(display, f"sens={MOTION_SENSITIVITY}  frame={frame_idx}",
                    (16, 112), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
        cv2.imshow("Detection Tuner", display)
        key = cv2.waitKey(333) & 0xFF
        if key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Done.")


if __name__ == "__main__":
    main()
