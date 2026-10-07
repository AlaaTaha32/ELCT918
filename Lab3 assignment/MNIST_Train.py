# ============================================================
# 1. IMPORTS AND GLOBAL CONFIGURATION
# ============================================================
import os
import time
import random
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import tensorflow as tf
import cv2


from PIL import Image
from sklearn.model_selection import train_test_split
# ============================================================
# GLOBAL CONFIGURATION
# ============================================================

# Reproducibility
SEED = 42   # used in creating validation set
random.seed(SEED)
np.random.seed(SEED)
tf.random.set_seed(SEED)

# Dataset paths
TRAIN_DIR = "MNIST/training"
TEST_DIR  = "MNIST/testing"

# Output directory
BASE_DIR = "Outputs_MNSIT"

# Preprocessing images directory
TEST_IMAGE_PATH = r"Preprocessing_Images/digit.png"

# Training settings
BATCH_SIZE = 128
EPOCHS = 30

# Optimizer settings
INITIAL_LR = 0.01
MOMENTUM = 0.9
WEIGHT_DECAY = 5e-4     # Regularization parameter

# MNIST normalization
MNIST_MEAN = 0.1307
MNIST_STD = 0.3081

# Image size and threshold value
TARGET_SIZE = 28    # MNIST 28*28 images
LENET_SIZE = 32     # 32*32 zero-padded images
DIGIT_SIZE = 20     # Original pixel box containing the digit
threshold_value = 127

# Validation set
VALIDATION_SIZE = 5000

# Minimum contrast and area ratio to improve detection accuracy
MIN_CONTRAST = 12        # gray std below this = blank paper
MIN_AREA_RATIO = 0.005   # ignore blobs smaller than 0.5% of the ROI area

#print("TensorFlow version:", tf.__version__)
#print("Random seed:", SEED)
# ============================================================
# 2. LOAD MNIST DATASET
# ============================================================
def load_split(root):
    """
    Load a digit dataset stored in the following structure:

        root/
        ├── 0/
        ├── 1/
        ├── ...
        └── 9/

    Each folder contains grayscale digit images.

    Parameters
    ----------
    root : str
        Root directory containing the ten digit folders.

    Returns
    -------
    images : np.ndarray
        Flattened images with shape (N, 784), normalized to [0, 1].
    labels : np.ndarray
        Integer digit labels with shape (N,).
    """
    images = []
    labels = []
    for digit in range(10):
        folder = os.path.join(root, str(digit))
        filenames = sorted(os.listdir(folder))
        for fname in filenames:
            image_path = os.path.join(folder, fname)
            img = Image.open(image_path).convert("L")
            image = np.array(img,dtype=np.float32)
            # Normalize from [0, 255] to [0, 1]
            image = image / 255.0
            images.append(image.reshape(784))
            labels.append(digit)

    return np.stack(images), np.array(labels, dtype=np.int64)

# ============================================================
# 3. SPLIT TRAINING / VALIDATION DATA
# ============================================================
def prepare_dataset(x_train, y_train, x_test, y_test, validation_size=5000, batch_size=128):
    """
    Split the original MNIST training set into training and
    validation sets and create TensorFlow Dataset objects.

    The official test set remains untouched and is used only
    for final evaluation.

    Parameters
    ----------
    x_train : np.ndarray
        Full training images.
    y_train : np.ndarray
        Full training labels.
    x_test : np.ndarray
        Test images.
    y_test : np.ndarray
        Test labels.
    validation_size : int
        Number of samples reserved for validation.
    batch_size : int
        Batch size.

    Returns
    -------
    x_train, y_train
    x_val, y_val
    x_test, y_test
    train_ds, val_ds, test_ds
    """

    # --------------------------------------------------------
    # Split training data into training and validation sets
    # --------------------------------------------------------
    x_train, x_val, y_train, y_val = train_test_split(x_train,y_train,
        test_size=validation_size,random_state=SEED,stratify=y_train)

    # --------------------------------------------------------
    # Reshape flattened images to 28x28x1
    # --------------------------------------------------------
    x_train = x_train.reshape(-1, 28, 28, 1)
    x_val   = x_val.reshape(-1, 28, 28, 1)
    x_test  = x_test.reshape(-1, 28, 28, 1)

    # --------------------------------------------------------
    # Zero-pad 28x28 images to 32x32
    # Padding: 2 pixels on every side
    # --------------------------------------------------------

    x_train = np.pad(x_train,
        ((0, 0), (2, 2), (2, 2), (0, 0)),
        mode="constant"
    )

    x_val = np.pad(x_val,
        ((0, 0), (2, 2), (2, 2), (0, 0)),
        mode="constant"
    )

    x_test = np.pad(x_test,
        ((0, 0), (2, 2), (2, 2), (0, 0)),
        mode="constant"
    )

    # --------------------------------------------------------
    # Create TensorFlow datasets
    # --------------------------------------------------------

    train_ds = tf.data.Dataset.from_tensor_slices(
        (x_train, y_train)
    )

    val_ds = tf.data.Dataset.from_tensor_slices(
        (x_val, y_val)
    )

    test_ds = tf.data.Dataset.from_tensor_slices(
        (x_test, y_test)
    )

    # --------------------------------------------------------
    # Shuffle training data only to prevent the model from
    # learning the order of your dataset rather than the actual
    # patterns within it.
    # --------------------------------------------------------
    train_ds = train_ds.shuffle(buffer_size=len(x_train),seed=SEED,
        reshuffle_each_iteration=True)

    # --------------------------------------------------------
    # Batch datasets
    # --------------------------------------------------------
    train_ds = train_ds.batch(batch_size)
    val_ds = val_ds.batch(batch_size)
    test_ds = test_ds.batch(batch_size)

    # --------------------------------------------------------
    # Prefetch
    # --------------------------------------------------------
    train_ds = train_ds.prefetch(tf.data.AUTOTUNE)
    val_ds = val_ds.prefetch(tf.data.AUTOTUNE)
    test_ds = test_ds.prefetch(tf.data.AUTOTUNE)

    return (
        x_train, y_train,
        x_val, y_val,
        x_test, y_test,
        train_ds, val_ds, test_ds
    )

# ============================================================
# 4. NORMALIZATION AND PREPROCESSING
# ============================================================
def normalize_dataset(dataset):
    """
    Normalize MNIST images using the standard MNIST mean
    and standard deviation.

    Input:
        Pixel values in [0, 1]

    Output:
        Normalized pixel values using: (x - 0.1307) / 0.3081
    """

    return dataset.map(
        lambda images, labels: (
            (tf.cast(images, tf.float32) - MNIST_MEAN) / MNIST_STD,
            labels
        ),
        num_parallel_calls=tf.data.AUTOTUNE
    )

def preprocess_datasets(train_ds, val_ds, test_ds):
    """
    Apply augmentation to training dataset only.
    Apply identical MNIST normalization to training,
    validation and test datasets.
    """

    augment = tf.keras.Sequential([
        tf.keras.layers.RandomRotation(0.05, fill_mode="constant", fill_value=0.0),
        tf.keras.layers.RandomTranslation(0.1, 0.1, fill_mode="constant", fill_value=0.0),
        tf.keras.layers.RandomZoom(0.15, fill_mode="constant", fill_value=0.0),
    ])

    # augment training data only, Before normalization
    train_ds = train_ds.map(
        lambda x, y: (augment(x, training=True), y),
        num_parallel_calls=tf.data.AUTOTUNE
    )

    train_ds = normalize_dataset(train_ds)
    val_ds = normalize_dataset(val_ds)
    test_ds = normalize_dataset(test_ds)

    train_ds = train_ds.prefetch(tf.data.AUTOTUNE)
    val_ds = val_ds.prefetch(tf.data.AUTOTUNE)
    test_ds = test_ds.prefetch(tf.data.AUTOTUNE)

    return train_ds, val_ds, test_ds

# ============================================================
# 5. VISUALIZE PREPARED MNIST SAMPLES
# ============================================================
def show_samples(images, labels, num_samples=10):
    """
    Display sample MNIST images after resizing/padding but
    before normalization visualization.
    """

    plt.figure(figsize=(15, 3))

    for i in range(num_samples):

        plt.subplot(2, 5, i + 1)

        plt.imshow(
            images[i].squeeze(),
            cmap="gray"
        )

        plt.title(f"Label: {labels[i]}")
        plt.axis("off")

    plt.tight_layout()
    plt.show()

# ============================================================
# 6. LENET-5 ARCHITECTURE
# ============================================================
def build_lenet(num_classes=10):
    """
    Build the LeNet-5 architecture adapted for MNIST.

    Input:
        32x32 grayscale image

    Architecture:
        C1: 6 x 5x5 convolution + tanh
        S2: 2x2 average pooling
        C3: 16 x 5x5 convolution + tanh
        S4: 2x2 average pooling
        F5: 120 neurons + tanh
        F6: 84 neurons + tanh
        Output: num_classes logits
    """

    # --------------------------------------------------------
    # Input
    # --------------------------------------------------------

    inputs = tf.keras.Input(
        shape=(32, 32, 1),
        name="Input"
    )

    # --------------------------------------------------------
    # C1: Convolution
    # 6 filters, 5x5, stride 1, tanh
    # Output: 28x28x6
    # --------------------------------------------------------

    x = tf.keras.layers.Conv2D(
        filters=6,
        kernel_size=(5, 5),
        strides=1,
        padding="valid",
        activation="tanh",
        name="C1"
    )(inputs)

    # --------------------------------------------------------
    # S2: Average Pooling
    # 2x2, stride 2
    # Output: 14x14x6
    # --------------------------------------------------------

    x = tf.keras.layers.AveragePooling2D(
        pool_size=(2, 2),
        strides=2,
        padding="valid",
        name="S2"
    )(x)

    # --------------------------------------------------------
    # C3: Convolution
    # 16 filters, 5x5, stride 1, tanh
    # Output: 10x10x16
    # --------------------------------------------------------

    x = tf.keras.layers.Conv2D(
        filters=16,
        kernel_size=(5, 5),
        strides=1,
        padding="valid",
        activation="tanh",
        name="C3"
    )(x)

    # --------------------------------------------------------
    # S4: Average Pooling
    # 2x2, stride 2
    # Output: 5x5x16
    # --------------------------------------------------------

    x = tf.keras.layers.AveragePooling2D(
        pool_size=(2, 2),
        strides=2,
        padding="valid",
        name="S4"
    )(x)

    # --------------------------------------------------------
    # Flatten
    # 5x5x16 = 400
    # --------------------------------------------------------

    x = tf.keras.layers.Flatten(
        name="Flatten"
    )(x)

    # --------------------------------------------------------
    # F5: Fully Connected
    # 120 neurons, tanh
    # --------------------------------------------------------

    x = tf.keras.layers.Dense(
        120,
        activation="tanh",
        name="F5"
    )(x)

    # --------------------------------------------------------
    # F6: Fully Connected
    # 84 neurons, tanh
    # --------------------------------------------------------

    x = tf.keras.layers.Dense(
        84,
        activation="tanh",
        name="F6"
    )(x)

    # --------------------------------------------------------
    # Output
    # 10 classes
    #
    # No softmax: outputs are logits.
    # --------------------------------------------------------

    outputs = tf.keras.layers.Dense(
        num_classes,
        name="Output"
    )(x)

    # --------------------------------------------------------
    # Functional model
    # --------------------------------------------------------

    return tf.keras.Model(
        inputs=inputs,
        outputs=outputs,
        name="LeNet_MNIST"
    )

# ============================================================
# 7. LEARNING RATE SCHEDULE
# ============================================================
def lr_schedule(epoch):
    """
    Learning-rate schedule.

    Epochs 1-15  : 0.01
    Epochs 16-24 : 0.001
    Epochs 25-30 : 0.0001
    """

    if epoch < 15:
        return 0.01

    elif epoch < 24:
        return 0.001

    else:
        return 0.0001

# ============================================================
# 8. EPOCH TIMING CALLBACK
# ============================================================
class EpochTimer(tf.keras.callbacks.Callback):
    """
    Measure training time for every epoch.
    """

    def on_train_begin(self, logs=None):
        self.epoch_times = []

    def on_epoch_begin(self, epoch, logs=None):
        self.start_time = time.time()

    def on_epoch_end(self, epoch, logs=None):

        elapsed = time.time() - self.start_time

        self.epoch_times.append(elapsed)

        print(
            f"Epoch {epoch + 1} training time: "
            f"{elapsed:.2f} seconds"
        )

# ============================================================
# 9. TRAINING AND RESULT SAVING
# ============================================================
def train_and_save( model,train_ds, val_ds, epochs=30):
    """
    Compile and train LeNet-5 on MNIST.

    The function:
        1. Creates the optimizer.
        2. Compiles the model.
        3. Creates training callbacks.
        4. Trains the model.
        5. Records epoch times.
        6. Saves the best model.
        7. Saves training history.
        8. Generates accuracy and loss plots.

    Returns
    -------
    history : Keras History object
    results_df : pandas DataFrame
    timer : EpochTimer
    """

    # --------------------------------------------------------
    # Output directories
    # --------------------------------------------------------
    model_dir = os.path.join(BASE_DIR,"models")

    results_dir = os.path.join(BASE_DIR,"results")

    figures_dir = os.path.join(BASE_DIR,"figures")

    os.makedirs(model_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(figures_dir, exist_ok=True)

    # --------------------------------------------------------
    # Optimizer
    # --------------------------------------------------------

    optimizer = tf.keras.optimizers.SGD(
        learning_rate=INITIAL_LR,
        momentum=MOMENTUM,
        weight_decay=WEIGHT_DECAY
    )

    # --------------------------------------------------------
    # Compile
    # --------------------------------------------------------

    model.compile(
        optimizer=optimizer,
        loss=tf.keras.losses.SparseCategoricalCrossentropy(
            from_logits=True
        ),
        metrics=["accuracy"]
    )

    # --------------------------------------------------------
    # Callbacks
    # --------------------------------------------------------
    checkpoint_path = os.path.join(model_dir,"LeNet_MNIST_best.keras")

    checkpoint = tf.keras.callbacks.ModelCheckpoint(
        checkpoint_path,
        monitor="val_accuracy",
        save_best_only=True,
        mode="max",
        verbose=1
    )

    lr_callback = tf.keras.callbacks.LearningRateScheduler(
        lr_schedule,
        verbose=1
    )

    timer = EpochTimer()

    # --------------------------------------------------------
    # Training
    # --------------------------------------------------------
    history = model.fit(train_ds,
        epochs=epochs,validation_data=val_ds,
        callbacks=[
            lr_callback,
            checkpoint,
            timer
        ]
    )

    # --------------------------------------------------------
    # Create results table
    # --------------------------------------------------------
    results = {
        "epoch": range(1, epochs + 1),
        "train_accuracy": history.history["accuracy"],
        "val_accuracy": history.history["val_accuracy"],
        "train_loss": history.history["loss"],
        "val_loss": history.history["val_loss"],
        "learning_rate": history.history["learning_rate"],
        "epoch_time_sec": timer.epoch_times
    }

    results_df = pd.DataFrame(results)

    # --------------------------------------------------------
    # Save history
    # --------------------------------------------------------

    history_path = os.path.join(results_dir,"LeNet_MNIST_history.csv")

    results_df.to_csv(
        history_path,
        index=False
    )

    # --------------------------------------------------------
    # Accuracy plot
    # --------------------------------------------------------

    plt.figure(figsize=(8, 5))

    plt.plot(
        results_df["epoch"],
        results_df["train_accuracy"],
        label="Training Accuracy"
    )

    plt.plot(
        results_df["epoch"],
        results_df["val_accuracy"],
        label="Validation Accuracy"
    )

    plt.xlabel("Epoch")
    plt.ylabel("Accuracy")

    plt.title(
        "LeNet-5 - MNIST Accuracy"
    )

    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    accuracy_path = os.path.join(
        figures_dir,
        "LeNet_MNIST_accuracy.png"
    )

    plt.savefig(
        accuracy_path,
        dpi=300,
        bbox_inches="tight"
    )

    plt.show()

    # --------------------------------------------------------
    # Loss plot
    # --------------------------------------------------------

    plt.figure(figsize=(8, 5))

    plt.plot(
        results_df["epoch"],
        results_df["train_loss"],
        label="Training Loss"
    )

    plt.plot(
        results_df["epoch"],
        results_df["val_loss"],
        label="Validation Loss"
    )

    plt.xlabel("Epoch")
    plt.ylabel("Loss")

    plt.title(
        "LeNet-5 - MNIST Loss"
    )

    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    loss_path = os.path.join(
        figures_dir,
        "LeNet_MNIST_loss.png"
    )

    plt.savefig(
        loss_path,
        dpi=300,
        bbox_inches="tight"
    )

    plt.show()

    # --------------------------------------------------------
    # Training summary
    # --------------------------------------------------------

    best_epoch = (
        results_df["val_accuracy"].idxmax() + 1
    )

    best_val_accuracy = (
        results_df["val_accuracy"].max()
    )

    average_epoch_time = (
        results_df["epoch_time_sec"].mean()
    )

    total_training_time = (
        results_df["epoch_time_sec"].sum()
    )

    print("\n" + "=" * 60)
    print("TRAINING SUMMARY")
    print("=" * 60)

    print(
        f"Architecture       : LeNet-5"
    )

    print(
        f"Dataset            : MNIST"
    )

    print(
        f"Epochs             : {epochs}"
    )

    print(
        f"Best epoch         : {best_epoch}"
    )

    print(
        f"Best validation acc: "
        f"{best_val_accuracy:.4%}"
    )

    print(
        f"Average epoch time : "
        f"{average_epoch_time:.2f} sec"
    )

    print(
        f"Total training time: "
        f"{total_training_time:.2f} sec"
    )

    print(
        f"\nBest model saved to:\n"
        f"{checkpoint_path}"
    )

    print(
        f"\nTraining history saved to:\n"
        f"{history_path}"
    )

    return history, results_df, timer

# ============================================================
# 10. EVALUATE BEST MODEL
# ============================================================
def evaluate_and_save(test_ds):
    """
    Load the best validation model and evaluate it on the
    untouched MNIST test set.
    """

    model_path = os.path.join(BASE_DIR,"models","LeNet_MNIST_best.keras")
    results_dir = os.path.join(BASE_DIR,"results")

    print("\n" + "=" * 60)
    print("EVALUATING LENET-5 ON MNIST TEST SET")
    print("=" * 60)

    # --------------------------------------------------------
    # Load best model
    # --------------------------------------------------------
    best_model = tf.keras.models.load_model(model_path)

    # --------------------------------------------------------
    # Evaluate
    # --------------------------------------------------------
    test_metrics = best_model.evaluate(
        test_ds,
        return_dict=True,
        verbose=1
    )

    test_loss = test_metrics["loss"]
    test_accuracy = test_metrics["accuracy"]

    # --------------------------------------------------------
    # Store results
    # --------------------------------------------------------

    evaluation_results = {
        "architecture": "LeNet-5",
        "dataset": "MNIST",
        "test_loss": test_loss,
        "test_accuracy": test_accuracy * 100.0,
        "num_parameters": best_model.count_params()
    }

    evaluation_df = pd.DataFrame(
        [evaluation_results]
    )

    evaluation_path = os.path.join(
        results_dir,
        "LeNet_MNIST_evaluation.csv"
    )

    evaluation_df.to_csv(
        evaluation_path,
        index=False
    )

    # --------------------------------------------------------
    # Print results
    # --------------------------------------------------------

    print("\nTest Results:")
    print(
        f"Test Loss       : {test_loss:.4f}"
    )

    print(
        f"Test Accuracy   : "
        f"{test_accuracy * 100:.2f}%"
    )

    print(
        f"Parameters      : "
        f"{best_model.count_params():,}"
    )

    print(
        f"\nEvaluation saved to:"
    )

    print(evaluation_path)

    return evaluation_results

# ============================================================
# 11. RUN MNIST LENET EXPERIMENT
# ============================================================
def run_experiment( train_ds, val_ds, test_ds):
    """
    Run the complete LeNet-5 MNIST experiment.
    """

    print("\n")
    print("#" * 80)
    print("# LeNet-5 - MNIST")
    print("#" * 80)

    # --------------------------------------------------------
    # Build model
    # --------------------------------------------------------
    print("\nBuilding LeNet-5...")
    model = build_lenet(num_classes=10)

    # --------------------------------------------------------
    # Model summary
    # --------------------------------------------------------
    print("\nModel Summary:")
    model.summary()

    # --------------------------------------------------------
    # Train
    # --------------------------------------------------------
    history, training_results, timer = train_and_save(
        model=model,
        train_ds=train_ds,
        val_ds=val_ds,
        epochs=EPOCHS
    )

    # --------------------------------------------------------
    # Evaluate
    # --------------------------------------------------------
    evaluation_results = evaluate_and_save(test_ds=test_ds)

    # --------------------------------------------------------
    # Experiment summary
    # --------------------------------------------------------
    experiment_results = {

        "architecture": "LeNet-5",

        "dataset": "MNIST",

        "num_parameters":
            model.count_params(),

        "best_val_accuracy":
            training_results["val_accuracy"].max() * 100.0,

        "best_epoch":
            training_results["val_accuracy"].idxmax() + 1,

        "test_accuracy":
            evaluation_results["test_accuracy"],

        "total_training_time_sec":
            training_results["epoch_time_sec"].sum(),

        "average_epoch_time_sec":
            training_results["epoch_time_sec"].mean()
    }

    print("\n" + "=" * 70)
    print("EXPERIMENT SUMMARY")
    print("=" * 70)

    for key, value in experiment_results.items():
        print(f"{key}: {value}")

    return experiment_results

# ============================================================
# 12. PREPROCESSING PIPELINE
# ============================================================
def preprocess_image(image, dilation=False, return_steps=False):
    """
        Complete handwritten digit preprocessing pipeline.

        Inputs:
            image: OpenCV image.
            dilation: Whether to apply morphological dilation.
            return_steps: If True, return all intermediate preprocessing stages (for debugging).

        Returns:
            normalized: Final normalized 32x32 image.
            steps: Dictionary containing intermediate images if requested (for debugging).
    """

    def convert_to_grayscale(image):
        """
        Convert an input image to grayscale.
        If the image is already grayscale, it is returned unchanged.
        """
        if len(image.shape) == 2:
            return image
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    def apply_gaussian_blur(gray):
        """
        Apply Gaussian blur to reduce image noise.
        """
        return cv2.GaussianBlur(gray, (5, 5), 0)

    def apply_threshold(gray):
        """
        Convert the grayscale image to a binary image.

        Otsu automatically determines the threshold.
        THRESH_BINARY_INV makes the digit white on a black background,
        matching the MNIST convention.
        """
        #_, binary = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY_INV)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        return binary

    def apply_dilation(binary, enabled=False):
        """
        Optionally dilate the digit.

        Dilation can make thin handwritten strokes more prominent.
        It is disabled by default.
        """

        if not enabled:
            return binary

        kernel = np.ones((2, 2), np.uint8)

        return cv2.dilate(
            binary,
            kernel,
            iterations=1
        )

    def find_digit_contour(binary):
        """
        Largest valid contour: not a speck, not touching the ROI border.
        """
        h, w = binary.shape

        contours, _ = cv2.findContours(
            binary,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        valid = []
        for c in contours:
            x, y, cw, ch = cv2.boundingRect(c)

            if cv2.contourArea(c) < MIN_AREA_RATIO * h * w:
                continue  # noise specks

            if x <= 2 or y <= 2 or x + cw >= w - 2 or y + ch >= h - 2:
                continue  # touches border (shadow, ROI edge)

            valid.append(c)

        if not valid:
            return None

        return max(valid, key=cv2.contourArea)

    def crop_digit(binary, contour):
        """
        Crop the digit using the bounding rectangle of its contour.
        """
        x, y, w, h = cv2.boundingRect(contour)

        cropped = binary[
            y:y + h,
            x:x + w
        ]

        return cropped

    def resize_digit(cropped, target_size=DIGIT_SIZE):
        """
        Resize the digit so that its larger dimension is target_size,
        while preserving its original aspect ratio.
        """

        height, width = cropped.shape

        scale = target_size / max(height, width)

        new_width = max(1, int(round(width * scale)))
        new_height = max(1, int(round(height * scale)))

        resized = cv2.resize(
            cropped,
            (new_width, new_height),
            interpolation=cv2.INTER_AREA
        )

        return resized

    def center_digit(resized, canvas_size=TARGET_SIZE):
        """
        Place the resized digit in the center of a 28x28 canvas.
        """
        height, width = resized.shape

        canvas = np.zeros(
            (canvas_size, canvas_size),
            dtype=np.uint8
        )

        # Calculate top-left position
        x_offset = (canvas_size - width) // 2
        y_offset = (canvas_size - height) // 2

        canvas[
            y_offset:y_offset + height,
            x_offset:x_offset + width
        ] = resized

        return canvas

    def center_by_mass(img):
        m = cv2.moments(img)
        if m["m00"] == 0:
            return img
        cx, cy = m["m10"] / m["m00"], m["m01"] / m["m00"]
        M = np.float32([[1, 0, round(14 - cx)], [0, 1, round(14 - cy)]])
        return cv2.warpAffine(img, M, (28, 28))

    def pad_to_lenet(image, target_size=LENET_SIZE):
        """
        Zero-pad the 28x28 image to 32x32.

        This preserves the original LeNet-5 input dimensions.
        """
        current_size = image.shape[0]
        total_padding = target_size - current_size
        if total_padding < 0:
            raise ValueError(
                "Input image is larger than the target size."
            )

        top = total_padding // 2
        bottom = total_padding - top

        left = total_padding // 2
        right = total_padding - left

        padded = cv2.copyMakeBorder(
            image,
            top,
            bottom,
            left,
            right,
            borderType=cv2.BORDER_CONSTANT,
            value=0
        )

        return padded

    def scale_image(image):
        """
        Convert uint8 [0,255] image to float [0,1].
        """
        return image.astype(np.float32) / 255.0

    def normalize_mnist(image):
        """
        Apply the same normalization used during LeNet training.
        """
        return (image - MNIST_MEAN) / MNIST_STD

    gray = convert_to_grayscale(image)

    if gray.std() < MIN_CONTRAST:
        raise ValueError("Blank image: no ink detected.")

    blurred = apply_gaussian_blur(gray)

    binary = apply_threshold(blurred)

    dilated = apply_dilation(binary, enabled=dilation)

    contour = find_digit_contour(dilated)
    if contour is None:
        raise ValueError(
            "No digit contour was detected."
        )

    cropped = crop_digit(dilated, contour)

    resized = resize_digit(cropped, target_size=DIGIT_SIZE)

    if dilation:
        resized = cv2.dilate(resized, np.ones((2, 2), np.uint8))

    centered = center_digit(resized,canvas_size=TARGET_SIZE)

    centered_mass = center_by_mass(centered)

    padded = pad_to_lenet(centered_mass,target_size=LENET_SIZE)

    scaled = scale_image(padded)

    normalized = normalize_mnist(scaled)

    if return_steps:
        steps = {
            "Original": image,
            "Grayscale": gray,
            "Gaussian Blur": blurred,
            "Threshold": binary,
            "Dilation": dilated,
            "Cropped": cropped,
            "Resized": resized,
            "Centered 28x28": centered,
            "Centered by mass": centered_mass,
            "Padded 32x32": padded,
            "Scaled [0,1]": scaled,
            "Normalized": normalized
        }

        return normalized, steps

    return normalized

# ============================================================
# 13. VISUALIZE PREPROCESSING PIPELINE
# ============================================================
def visualize_preprocessing(steps):
    """
    Display the intermediate preprocessing stages.
    """

    display_steps = [
        ("Original", steps["Original"]),
        ("Grayscale", steps["Grayscale"]),
        ("Gaussian Blur", steps["Gaussian Blur"]),
        ("Threshold", steps["Threshold"]),
        ("Dilation", steps["Dilation"]),
        ("Cropped", steps["Cropped"]),
        ("Resized", steps["Resized"]),
        ("Centered 28x28", steps["Centered 28x28"]),
        ("Padded 32x32", steps["Padded 32x32"])
    ]

    plt.figure(figsize=(15, 7))

    for i, (title, image) in enumerate(display_steps):

        plt.subplot(2, 5, i + 1)

        if len(image.shape) == 2:
            plt.imshow(image, cmap="gray")
        else:
            plt.imshow(
                cv2.cvtColor(
                    image,
                    cv2.COLOR_BGR2RGB
                )
            )

        plt.title(title)
        plt.axis("off")

    plt.tight_layout()

    images_path = os.path.join(
        BASE_DIR,
        "Image_outputs.png"
    )

    plt.savefig(
        images_path,
        dpi=300,
        bbox_inches="tight"
    )

    plt.show()

# ============================================================
# 14. Test PREPROCESSING PIPELINE
# ============================================================
def test_preprocessing_pipeline(dilation=False):
    image = cv2.imread(TEST_IMAGE_PATH)

    if image is None:
        raise FileNotFoundError(
            f"Could not load image: {TEST_IMAGE_PATH}"
        )

    processed, steps = preprocess_image(image,
        dilation=dilation, return_steps=True)

    visualize_preprocessing(steps)

    print("Final image shape:", processed.shape)
    print("Final image dtype:", processed.dtype)
    print("Final image minimum:", processed.min())
    print("Final image maximum:", processed.max())

def main(task = 1):
    if task == 1:

        # ------------------------------------------------------------
        # Load training and testing data
        # ------------------------------------------------------------

        print("Loading MNIST PNG dataset...")

        x_train_full, y_train_full = load_split(TRAIN_DIR)
        x_test, y_test = load_split(TEST_DIR)

        print(f"Training set: {x_train_full.shape}")
        print(f"Training labels: {y_train_full.shape}")

        print(f"Test set: {x_test.shape}")
        print(f"Test labels: {y_test.shape}")

        (x_train, y_train, x_val, y_val, x_test, y_test,
         mnist_train_ds, mnist_val_ds, mnist_test_ds) = prepare_dataset(x_train_full, y_train_full, x_test, y_test,
                                                        validation_size=VALIDATION_SIZE, batch_size=BATCH_SIZE)

        print("\nMNIST Dataset:")
        print("Training:  ", x_train.shape)
        print("Validation:", x_val.shape)
        print("Test:      ", x_test.shape)

        mnist_train_ds, mnist_val_ds, mnist_test_ds = preprocess_datasets(mnist_train_ds, mnist_val_ds, mnist_test_ds)

        show_samples(x_train, y_train)

        experiment_results = run_experiment(
            train_ds=mnist_train_ds,
            val_ds=mnist_val_ds,
            test_ds=mnist_test_ds
        )

    elif task == 2:
        print("Loading MNIST PNG dataset...")
        x_train_full, y_train_full = load_split(TRAIN_DIR)
        x_test, y_test = load_split(TEST_DIR)
        print(f"Training set: {x_train_full.shape}")
        print(f"Training labels: {y_train_full.shape}")
        print(f"Test set: {x_test.shape}")
        print(f"Test labels: {y_test.shape}")

        model_path = "Outputs/models/LeNet_MNIST_best.keras"
        model = tf.keras.models.load_model(model_path)


        test_preprocessing_pipeline(True)

        # Testing the preprocessing pipeline on MNIST dataset
        correct, n = 0, 100
        for i in range(n):
            img = (x_test[i].reshape(28, 28) * 255).astype(np.uint8)
            fake = cv2.resize(255 - img, (300, 300), interpolation=cv2.INTER_CUBIC)  # dark ink on white
            inp = preprocess_image(fake)[np.newaxis, ..., np.newaxis].astype(np.float32)
            correct += int(np.argmax(model.predict(inp, verbose=0)) == y_test[i])
        print("Pipeline accuracy:", correct / n)


    else:
        raise ValueError("Invalid task. Choose 1, 2, or 3.")


if __name__ == '__main__':
    main(2)
