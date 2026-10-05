# ============================================================
# BONUS 2 / 3 - REAL-TIME ARABIC-INDIC DIGIT RECOGNITION
#
# Keys:  q = quit    r = start/stop recording a demo video
# ============================================================

import json
import time
import cv2
import numpy as np
import tensorflow as tf
from pandas._config import display

# ============================================================
# CONFIGURATION
# ============================================================
MODEL_PATH = "Outputs_MADBase/LeNet_MADBase_best.keras"
NORM_PATH = "Outputs_MADBase/madbase_norm.json"   # mean, std, zero_size

CAMERA_INDEX = 0
ROI_SIZE = 300
WINDOW_NAME = "Arabic-Indic Digit Recognition"
CONFIDENCE_THRESHOLD = 0.50

DILATION = True
DIGIT_SIZE = 20          # normal digits: longer side scaled to 20 px
CANVAS = 28
MIN_CONTRAST = 12        # gray std below this = blank paper, no digit
MIN_AREA_RATIO = 0.0008  # ignore blobs smaller than this fraction of the ROI
DOT_RATIO = 0.15         # blob smaller than 15% of the ROI side = "dot" (zero)

# Optional: a font containing Arabic-Indic digits (Arial/Tahoma on Windows)
FONT_PATH = r"C:\Windows\Fonts\arial.ttf"
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"

with open(NORM_PATH) as f:
    NORM = json.load(f)


# ============================================================
# PREPROCESSING (Task 2 pipeline + dot handling)
# ============================================================
def find_digit_contour(binary):
    """Largest valid contour: not a speck, not touching the ROI border."""
    h, w = binary.shape
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    valid = []
    for c in contours:
        x, y, cw, ch = cv2.boundingRect(c)
        if cv2.contourArea(c) < MIN_AREA_RATIO * h * w:
            continue
        if x <= 2 or y <= 2 or x + cw >= w - 2 or y + ch >= h - 2:
            continue
        valid.append(c)
    return max(valid, key=cv2.contourArea) if valid else None


def preprocess(roi):
    """
    Returns (model_input (32,32), is_dot).
    Raises ValueError when nothing digit-like is found.
    """
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if roi.ndim == 3 else roi
    if gray.std() < MIN_CONTRAST:
        raise ValueError("blank ROI")

    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binary = cv2.threshold(blurred, 0, 255,
                              cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    contour = find_digit_contour(binary)
    if contour is None:
        raise ValueError("no contour")

    x, y, w, h = cv2.boundingRect(contour)
    crop = binary[y:y + h, x:x + w]
    side = max(w, h)

    # ---- THE DOT RULE (Arabic-Indic zero) ----------------------
    # A tiny blob is the digit zero. Scaling it to 20 px would turn it
    # into a big disc, unlike the small dots in MADBase. So keep it small:
    # scale it to the median zero size measured on the training data.
    is_dot = side < DOT_RATIO * binary.shape[0]
    target = NORM["zero_size"] if is_dot else DIGIT_SIZE
    scale = target / side

    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))
    resized = cv2.resize(crop, (new_w, new_h), interpolation=cv2.INTER_AREA)

    # Dilation only for strokes; it would inflate the dot
    if DILATION and not is_dot:
        resized = cv2.dilate(resized, np.ones((2, 2), np.uint8))

    # Centre in 28x28 by bounding box, then by centre of mass (like MNIST)
    canvas = np.zeros((CANVAS, CANVAS), np.uint8)
    h2, w2 = resized.shape
    yo, xo = (CANVAS - h2) // 2, (CANVAS - w2) // 2
    canvas[yo:yo + h2, xo:xo + w2] = resized

    m = cv2.moments(canvas)
    if m["m00"] > 0:
        cx, cy = m["m10"] / m["m00"], m["m01"] / m["m00"]
        M = np.float32([[1, 0, round(14 - cx)], [0, 1, round(14 - cy)]])
        canvas = cv2.warpAffine(canvas, M, (CANVAS, CANVAS))

    padded = cv2.copyMakeBorder(canvas, 2, 2, 2, 2,
                                cv2.BORDER_CONSTANT, value=0)
    x32 = padded.astype(np.float32) / 255.0
    x32 = (x32 - NORM["mean"]) / NORM["std"]
    return x32, is_dot


# ============================================================
# HELPERS
# ============================================================
def get_roi(frame, size=ROI_SIZE):
    h, w = frame.shape[:2]
    x1, y1 = max(0, w // 2 - size // 2), max(0, h // 2 - size // 2)
    x2, y2 = min(w, x1 + size), min(h, y1 + size)
    return frame[y1:y2, x1:x2].copy(), (x1, y1, x2, y2)   # .copy(): no box in ROI


def predict(model, x32):
    logits = model(x32[None, ..., None], training=False)
    probs = tf.nn.softmax(logits[0]).numpy()
    d = int(np.argmax(probs))
    return d, float(probs[d])


def put_arabic(frame, text, org, size=64, color=(0, 255, 0)):
    """Draw Arabic-Indic glyphs with PIL; returns False if no font."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        font = ImageFont.truetype(FONT_PATH, size)
    except Exception:
        return False
    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    ImageDraw.Draw(img).text(org, text, font=font, fill=color[::-1])
    frame[:] = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    return True


def show_model_input(x32):
    img = np.clip((x32 * NORM["std"] + NORM["mean"]) * 255, 0, 255).astype(np.uint8)
    cv2.imshow("Model Input", cv2.resize(img, (320, 320),
                                         interpolation=cv2.INTER_NEAREST))


# ============================================================
# MAIN LOOP
# ============================================================
def main():
    model = tf.keras.models.load_model(MODEL_PATH)
    cam = cv2.VideoCapture(CAMERA_INDEX)
    if not cam.isOpened():
        raise RuntimeError("Could not open webcam.")

    writer, prev, fps = None, time.time(), 0.0

    while True:
        ret, frame = cam.read()
        if not ret:
            break

        roi, (x1, y1, x2, y2) = get_roi(frame)     # RAW frame: not mirrored

        digit, conf, is_dot, x32 = -1, 0.0, False, None
        try:
            x32, is_dot = preprocess(roi)
            digit, conf = predict(model, x32)
        except ValueError:
            pass

        now = time.time()
        fps = 0.9 * fps + 0.1 * (1.0 / max(now - prev, 1e-6))
        prev = now

        # Mirror ONLY the displayed image (ROI is centred, so box still matches)
        # display = cv2.flip(frame, 1)
        display = frame
        cv2.rectangle(display, (x1, y1), (x2, y2), (255, 255, 255), 2)

        if digit >= 0:
            ok = conf >= CONFIDENCE_THRESHOLD
            label = f"Digit: {digit if ok else '?'}"
            cv2.putText(display, label, (20, 40), cv2.FONT_HERSHEY_SIMPLEX,
                        1.0, (0, 255, 0), 2)
            cv2.putText(display, f"Confidence: {conf * 100:.1f}%", (20, 75),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            if is_dot:
                cv2.putText(display, "(dot detected)", (20, 140),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)
            if ok:
                put_arabic(display, ARABIC_DIGITS[digit], (display.shape[1] - 110, 10))
        else:
            cv2.putText(display, "No digit detected", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

        cv2.putText(display, f"FPS: {fps:.1f}", (20, 110),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(display, "Write a digit in the box. q = quit, r = record",
                    (20, display.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (200, 255, 100), 2)

        if x32 is not None:
            show_model_input(x32)

        if writer is not None:
            writer.write(display)
            cv2.circle(display, (display.shape[1] - 25, 60), 8, (0, 0, 255), -1)

        cv2.imshow(WINDOW_NAME, display)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        if key == ord("r"):
            if writer is None:
                h, w = display.shape[:2]
                writer = cv2.VideoWriter("Demo-Arabic Numbers.mp4", cv2.VideoWriter_fourcc(*"mp4v"),
                                         20, (w, h))
                print("Recording -> demo.mp4")
            else:
                writer.release()
                writer = None
                print("Recording stopped.")

    if writer is not None:
        writer.release()
    cam.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()