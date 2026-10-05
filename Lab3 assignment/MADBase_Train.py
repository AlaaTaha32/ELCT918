# ============================================================
# BONUS 1 - LeNet-5 ON MADBase (Arabic-Indic digits)
#
# Usage:
#   python madbase_train.py check   -> visualise samples (orientation / labels)
#   python madbase_train.py train   -> train, validate, test, save everything
# ============================================================

import os
import sys
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import tensorflow as tf
from sklearn.model_selection import train_test_split

# Reuse the architecture, LR schedule and timer from your Task 1 file
from MNIST_Train import build_lenet, lr_schedule, EpochTimer

# ============================================================
# CONFIGURATION
# ============================================================
SEED = 42
np.random.seed(SEED)
tf.random.set_seed(SEED)

DATA_DIR = "AHDD"
TRAIN_IMG = os.path.join(DATA_DIR, "csvTrainImages 60k x 784.csv")
TRAIN_LBL = os.path.join(DATA_DIR, "csvTrainLabel 60k x 1.csv")
TEST_IMG = os.path.join(DATA_DIR, "csvTestImages 10k x 784.csv")
TEST_LBL = os.path.join(DATA_DIR, "csvTestLabel 10k x 1.csv")

OUT_DIR = "Outputs_MADBase"  # separate folder: does not overwrite MNIST model
MODEL_PATH = os.path.join(OUT_DIR, "LeNet_MADBase_best.keras")
NORM_PATH = os.path.join(OUT_DIR, "madbase_norm.json")

BATCH_SIZE = 128
EPOCHS = 30  # lr_schedule is written for 30 epochs
VALIDATION_SIZE = 5000

# Set after running `check`: the CSV images are usually stored transposed
TRANSPOSE = True

os.makedirs(OUT_DIR, exist_ok=True)


# ============================================================
# LOADING
# ============================================================
def load_images(path, transpose=TRANSPOSE):
    """CSV (N, 784), no header -> float array (N, 28, 28) in [0, 1]."""
    x = pd.read_csv(path, header=None).values.astype(np.float32) / 255.0
    x = x.reshape(-1, 28, 28)
    if transpose:
        x = x.transpose(0, 2, 1)
    return x


def load_labels(path):
    return pd.read_csv(path, header=None).values.ravel().astype(np.int64)


def fix_polarity(x):
    """Make digits bright on a dark background (MNIST convention)."""
    if x.mean() > 0.5:
        print("Images are dark-on-light -> inverting.")
        return 1.0 - x
    return x


# ============================================================
# VISUALISATION (do this BEFORE training)
# ============================================================
def check_orientation():
    """
    One sample per class, shown two ways:
      row 1: plain reshape(28, 28)
      row 2: transposed
    The correct row shows upright digits that match the titles.
    """
    x_raw = load_images(TRAIN_IMG, transpose=False)
    y = load_labels(TRAIN_LBL)
    print("Images:", x_raw.shape, "Labels:", y.shape)
    print("Label counts:", np.bincount(y))

    idx = [np.where(y == d)[0][0] for d in range(10)]

    fig, axes = plt.subplots(2, 10, figsize=(16, 4))
    for col, i in enumerate(idx):
        axes[0, col].imshow(x_raw[i], cmap="gray")
        axes[0, col].set_title(f"label {y[i]}")
        axes[1, col].imshow(x_raw[i].T, cmap="gray")
        axes[0, col].axis("off")
        axes[1, col].axis("off")
    axes[0, 0].text(-0.1, 0.5, "raw", transform=axes[0, 0].transAxes, ha="right")
    axes[1, 0].text(-0.1, 0.5, "transposed", transform=axes[1, 0].transAxes, ha="right")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "orientation_check.png"), dpi=200)
    plt.show()
    print("Pick the row with upright digits and set TRANSPOSE accordingly.")


def show_samples(x, y, n=20, title="Training samples"):
    plt.figure(figsize=(14, 6))
    for i in range(n):
        plt.subplot(2, 10, i + 1)
        plt.imshow(x[i], cmap="gray")
        plt.title(f"{y[i]}")
        plt.axis("off")
    plt.suptitle(title)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "samples.png"), dpi=200)
    plt.show()


# ============================================================
# DATASET
# ============================================================
augment = tf.keras.Sequential([
    tf.keras.layers.RandomRotation(0.05, fill_mode="constant", fill_value=0.0),
    tf.keras.layers.RandomTranslation(0.1, 0.1, fill_mode="constant", fill_value=0.0),
    tf.keras.layers.RandomZoom(0.1, fill_mode="constant", fill_value=0.0),
])


def pad32(x):
    return np.pad(x[..., None], ((0, 0), (2, 2), (2, 2), (0, 0)), mode="constant")


def make_ds(x, y, mean, std, train):
    ds = tf.data.Dataset.from_tensor_slices((x, y))
    if train:
        ds = ds.shuffle(len(x), seed=SEED, reshuffle_each_iteration=True)
    ds = ds.batch(BATCH_SIZE)
    if train:  # augmentation: training only, after batching, BEFORE normalization
        ds = ds.map(lambda a, b: (augment(a, training=True), b),
                    num_parallel_calls=tf.data.AUTOTUNE)
    ds = ds.map(lambda a, b: ((a - mean) / std, b),
                num_parallel_calls=tf.data.AUTOTUNE)
    return ds.prefetch(tf.data.AUTOTUNE)


def median_zero_size(x, y, max_samples=2000):
    """
    Typical size (longer bounding-box side, in the 28x28 image) of the
    Arabic-Indic zero (a dot). The real-time app uses it so that a dot is
    NOT blown up to 20 px like the other digits.
    """
    sizes = []
    for img in x[y == 0][:max_samples]:
        ys, xs = np.where(img > 0.3)
        if len(xs):
            sizes.append(max(xs.max() - xs.min() + 1, ys.max() - ys.min() + 1))
    return float(np.median(sizes))


# ============================================================
# TRAIN / VALIDATE / TEST
# ============================================================
def train():
    x_full = fix_polarity(load_images(TRAIN_IMG))
    y_full = load_labels(TRAIN_LBL)
    x_test = load_images(TEST_IMG)
    x_test = (1.0 - x_test) if x_full.mean() < x_test.mean() - 0.3 else x_test
    y_test = load_labels(TEST_LBL)

    show_samples(x_full, y_full)  # sanity check before training

    x_train, x_val, y_train, y_val = train_test_split(
        x_full, y_full, test_size=VALIDATION_SIZE,
        random_state=SEED, stratify=y_full)

    x_train, x_val, x_test = pad32(x_train), pad32(x_val), pad32(x_test)

    # Normalisation statistics from the TRAINING split only
    mean, std = float(x_train.mean()), float(x_train.std())
    zero_size = median_zero_size(x_full, y_full)
    with open(NORM_PATH, "w") as f:
        json.dump({"mean": mean, "std": std, "zero_size": zero_size}, f)
    print(f"mean={mean:.4f} std={std:.4f} median zero size={zero_size:.1f}px")

    train_ds = make_ds(x_train, y_train, mean, std, train=True)
    val_ds = make_ds(x_val, y_val, mean, std, train=False)
    test_ds = make_ds(x_test, y_test, mean, std, train=False)

    model = build_lenet(num_classes=10)
    model.compile(
        optimizer=tf.keras.optimizers.SGD(learning_rate=0.01, momentum=0.9,
                                          weight_decay=5e-4),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
        metrics=["accuracy"])

    timer = EpochTimer()
    history = model.fit(
        train_ds, epochs=EPOCHS, validation_data=val_ds,
        callbacks=[
            tf.keras.callbacks.LearningRateScheduler(lr_schedule, verbose=1),
            tf.keras.callbacks.ModelCheckpoint(MODEL_PATH, monitor="val_accuracy",
                                               save_best_only=True, mode="max",
                                               verbose=1),
            timer,
        ])

    pd.DataFrame(history.history).to_csv(
        os.path.join(OUT_DIR, "history.csv"), index=False)

    # Curves
    for key, name in [("accuracy", "Accuracy"), ("loss", "Loss")]:
        plt.figure(figsize=(8, 5))
        plt.plot(history.history[key], label=f"Training {name}")
        plt.plot(history.history[f"val_{key}"], label=f"Validation {name}")
        plt.xlabel("Epoch");
        plt.ylabel(name);
        plt.grid(True);
        plt.legend()
        plt.title(f"LeNet-5 - MADBase {name}")
        plt.savefig(os.path.join(OUT_DIR, f"{key}.png"), dpi=300, bbox_inches="tight")
        plt.show()

    # Final test with the BEST checkpoint
    best = tf.keras.models.load_model(MODEL_PATH)
    loss, acc = best.evaluate(test_ds, verbose=1)
    print(f"\nBest val accuracy: {max(history.history['val_accuracy']):.4%}")
    print(f"MADBase test accuracy: {acc:.4%}   (loss {loss:.4f})")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "train"
    {"check": check_orientation, "train": train}[mode]()
