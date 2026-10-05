# ============================================================
# LAB 3 — TASK 3
# REAL-TIME HANDWRITTEN DIGIT RECOGNITION
# ============================================================

import cv2
import time
import numpy as np
import tensorflow as tf
from MNIST_Train import preprocess_image

# ============================================================
# CONFIGURATION
# ============================================================

MODEL_PATH = "Outputs/models/LeNet_MNIST_best.keras"

CAMERA_INDEX = 0

ROI_SIZE = 300

WINDOW_NAME = "Real-Time Digit Recognition"

CONFIDENCE_THRESHOLD = 0.50

DILATION = True


# ============================================================
# LOAD TRAINED MODEL
# ============================================================
def load_model(model_path=MODEL_PATH):
    """
    Load the trained LeNet-MNIST model.

    No training is performed in this script.
    """

    model = tf.keras.models.load_model(model_path)

    print("Model loaded successfully.")
    print(f"Model path: {model_path}")

    return model

# ============================================================
# CREATE CENTERED ROI
# ============================================================
def get_roi(frame, roi_size=ROI_SIZE):
    """
    Extract a square Region of Interest (ROI) from the
    center of the webcam frame.

    Returns:
        roi:
            Cropped ROI image.

        coordinates:
            (x1, y1, x2, y2)
    """

    frame_height, frame_width = frame.shape[:2]

    center_x = frame_width // 2
    center_y = frame_height // 2

    half_size = roi_size // 2

    x1 = center_x - half_size
    y1 = center_y - half_size

    x2 = center_x + half_size
    y2 = center_y + half_size

    # Make sure ROI stays inside the frame
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(frame_width, x2)
    y2 = min(frame_height, y2)

    #roi = frame[y1:y2, x1:x2]
    roi = frame[y1:y2, x1:x2].copy()

    return roi, (x1, y1, x2, y2)


# ============================================================
# PREPARE IMAGE FOR MODEL
# ============================================================
def prepare_model_input(roi):
    """
    Apply Task 2 preprocessing and convert the result into
    the tensor format expected by LeNet.

    Final shape:
        (1, 32, 32, 1)
    """

    processed = preprocess_image(
        roi,
        dilation=DILATION,
        return_steps=False
    )

    # Add channel dimension
    processed = processed[..., np.newaxis]

    # Add batch dimension
    processed = processed[np.newaxis, ...]

    return processed.astype(np.float32)

# ============================================================
# PREDICT DIGIT
# ============================================================
def predict_digit(model, model_input):
    """
    Run inference and return predicted digit and confidence.
    """

    #logits = model.predict(model_input,verbose=0)
    logits = model(model_input, training=False)

    # Convert logits to probabilities
    probabilities = tf.nn.softmax(logits[0]).numpy()

    predicted_digit = int(
        np.argmax(probabilities)
    )

    confidence = float(
        probabilities[predicted_digit]
    )

    return predicted_digit, confidence


# ============================================================
# DRAW ROI
# ============================================================
def draw_roi(frame, coordinates):
    """
    Draw the square ROI on the webcam frame.
    """

    x1, y1, x2, y2 = coordinates

    cv2.rectangle(
        frame,
        (x1, y1),
        (x2, y2),
        (255, 255, 255),
        2
    )


# ============================================================
# DRAW PREDICTION
# ============================================================
def draw_overlay(frame, digit, confidence, fps):

    if digit >= 0:
        ok = confidence >= CONFIDENCE_THRESHOLD
        cv2.putText(frame, f"Digit: {digit if ok else '?'}", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
        cv2.putText(frame, f"Confidence: {confidence * 100:.1f}%", (20, 75),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    else:
        cv2.putText(frame, "No digit detected", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

    cv2.putText(frame, f"FPS: {fps:.1f}", (20, 110),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(frame, "Write a digit in the box. q = quit, r = record",
                (20, frame.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX,
                0.6, (200, 255, 100), 2)


# ============================================================
# DISPLAY MODEL INPUT
# ============================================================
def display_model_input(model_input):
    """
    Display the 32x32 image used by the CNN, enlarged for
    visualization.

    The model input is normalized, so it is first converted
    back to a displayable grayscale image.
    """

    image = model_input[0, :, :, 0]

    # Undo MNIST normalization
    image = (
        image * 0.3081
        + 0.1307
    )

    # Convert [0,1] → [0,255]
    image = np.clip(
        image * 255.0,
        0,
        255
    ).astype(np.uint8)

    # Enlarge using nearest-neighbor interpolation
    image = cv2.resize(
        image,
        (320, 320),
        interpolation=cv2.INTER_NEAREST
    )

    cv2.imshow(
        "Model Input",
        image
    )


# ============================================================
# REAL-TIME WEBCAM LOOP
# ============================================================

def run_webcam(model):
    camera = cv2.VideoCapture(CAMERA_INDEX)
    if not camera.isOpened():
        raise RuntimeError("Could not open webcam.")

    writer, previous_time, fps = None, time.time(), 0.0

    while True:
        ret, frame = camera.read()
        if not ret:
            print("Failed to capture frame.")
            break

        roi, coordinates = get_roi(frame)        # raw frame, not mirrored

        digit, confidence, model_input = -1, 0.0, None
        try:
            model_input = prepare_model_input(roi)
            digit, confidence = predict_digit(model, model_input)
        except ValueError:
            pass                                  # blank / no valid contour

        now = time.time()
        fps = 0.9 * fps + 0.1 * (1.0 / max(now - previous_time, 1e-6))
        previous_time = now

        # Mirror only what is shown on screen
        # display = cv2.flip(frame, 1)
        display = frame
        draw_roi(display, coordinates)
        draw_overlay(display, digit, confidence, fps)

        if model_input is not None:
            display_model_input(model_input)

        if writer is not None:
            writer.write(display)
            cv2.circle(display, (display.shape[1] - 25, 25), 8, (0, 0, 255), -1)

        cv2.imshow(WINDOW_NAME, display)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        if key == ord("r"):
            if writer is None:
                h, w = display.shape[:2]
                writer = cv2.VideoWriter("demo.mp4",
                                         cv2.VideoWriter_fourcc(*"mp4v"),
                                         20, (w, h))
                print("Recording -> demo.mp4")
            else:
                writer.release()
                writer = None
                print("Recording stopped.")

    if writer is not None:
        writer.release()
    camera.release()
    cv2.destroyAllWindows()


# ============================================================
# MAIN
# ============================================================

def main():

    # --------------------------------------------------------
    # Load trained model
    # --------------------------------------------------------

    model = load_model()

    # --------------------------------------------------------
    # Start real-time recognition
    # --------------------------------------------------------

    run_webcam(model)


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
