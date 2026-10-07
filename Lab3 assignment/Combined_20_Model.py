# ============================================================
# OPTIONAL - SINGLE 20-CLASS LeNet-5 (Western + Arabic-Indic digits)
#
# Classes:  0-9   = Western digits 0:9   (MNIST)
#           10-19 = Arabic-Indic digits   (MADBase), class 10+d = digit d
#
# Usage:
#   python combined_20class.py train     -> train, test, then analyse
#   python combined_20class.py analyse   -> reload saved model, redo analysis only
#
# Needs LeNet.py and MADbase_train.py in the same folder.
# ============================================================
import os
import sys
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import tensorflow as tf
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix

from MNIST_Train import (build_lenet, lr_schedule, EpochTimer,
                   load_split, TRAIN_DIR, TEST_DIR)
import MADBase_Train as mb      # load_images, load_labels, pad32, make_ds, ...

# ============================================================
# CONFIGURATION
# ============================================================
SEED = 42
OUT_DIR = "Outputs_Combined"
MODEL_PATH = os.path.join(OUT_DIR, "LeNet_20class_best.keras")
NORM_PATH = os.path.join(OUT_DIR, "norm_20class.json")

EPOCHS = 30
VALIDATION_SIZE = 10000
TOP_PAIRS = 5

WESTERN = [str(d) for d in range(10)]
ARABIC = [f"A{d}" for d in range(10)]     # A0 = ٠ ... A9 = ٩
CLASS_NAMES = WESTERN + ARABIC

os.makedirs(OUT_DIR, exist_ok=True)


# ============================================================
# DATA
# ============================================================
def load_all():
    """Return train/test arrays (N, 28, 28) in [0,1] with 20-class labels."""
    # ---- MNIST (PNG folders) ----
    xw_tr, yw_tr = load_split(TRAIN_DIR)
    xw_te, yw_te = load_split(TEST_DIR)
    xw_tr, xw_te = xw_tr.reshape(-1, 28, 28), xw_te.reshape(-1, 28, 28)

    # ---- MADBase (CSV) ----
    xa_tr = mb.load_images(mb.TRAIN_IMG)
    ya_tr = mb.load_labels(mb.TRAIN_LBL)
    xa_te = mb.load_images(mb.TEST_IMG)
    ya_te = mb.load_labels(mb.TEST_LBL)

    # Same polarity decision for train and test: bright digit on dark background
    if xa_tr.mean() > 0.5:
        print("MADBase is dark-on-light -> inverting train and test.")
        xa_tr, xa_te = 1.0 - xa_tr, 1.0 - xa_te

    print(f"Mean pixel  MNIST: {xw_tr.mean():.3f}   MADBase: {xa_tr.mean():.3f}")

    zero_size = mb.median_zero_size(xa_tr, ya_tr)     # before label offset

    x_train = np.concatenate([xw_tr, xa_tr]).astype(np.float32)
    y_train = np.concatenate([yw_tr, ya_tr + 10])
    x_test = np.concatenate([xw_te, xa_te]).astype(np.float32)
    y_test = np.concatenate([yw_te, ya_te + 10])

    print("Train:", x_train.shape, " Test:", x_test.shape)
    print("Train class counts:", np.bincount(y_train))
    return x_train, y_train, x_test, y_test, zero_size


# ============================================================
# TRAINING
# ============================================================
def train(x_train, y_train, x_test, y_test, zero_size):
    x_tr, x_val, y_tr, y_val = train_test_split(
        x_train, y_train, test_size=VALIDATION_SIZE,
        random_state=SEED, stratify=y_train)

    x_tr, x_val = mb.pad32(x_tr), mb.pad32(x_val)

    mean, std = float(x_tr.mean()), float(x_tr.std())
    with open(NORM_PATH, "w") as f:
        json.dump({"mean": mean, "std": std, "zero_size": zero_size}, f)
    print(f"mean={mean:.4f} std={std:.4f}")

    # make_ds: shuffle -> batch -> augment (train only) -> normalise -> prefetch
    train_ds = mb.make_ds(x_tr, y_tr, mean, std, train=True)
    val_ds = mb.make_ds(x_val, y_val, mean, std, train=False)

    model = build_lenet(num_classes=20)
    model.compile(
        optimizer=tf.keras.optimizers.SGD(learning_rate=0.01, momentum=0.9,
                                          weight_decay=5e-4),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
        metrics=["accuracy"])

    history = model.fit(
        train_ds, epochs=EPOCHS, validation_data=val_ds,
        callbacks=[
            tf.keras.callbacks.LearningRateScheduler(lr_schedule, verbose=1),
            tf.keras.callbacks.ModelCheckpoint(MODEL_PATH, monitor="val_accuracy",
                                               save_best_only=True, mode="max",
                                               verbose=1),
            EpochTimer(),
        ])

    pd.DataFrame(history.history).to_csv(
        os.path.join(OUT_DIR, "history.csv"), index=False)

    for key, name in [("accuracy", "Accuracy"), ("loss", "Loss")]:
        plt.figure(figsize=(8, 5))
        plt.plot(history.history[key], label=f"Training {name}")
        plt.plot(history.history[f"val_{key}"], label=f"Validation {name}")
        plt.xlabel("Epoch"); plt.ylabel(name); plt.grid(True); plt.legend()
        plt.title(f"LeNet-5 - 20-class {name}")
        plt.savefig(os.path.join(OUT_DIR, f"{key}.png"), dpi=300,
                    bbox_inches="tight")
        plt.show()


# ============================================================
# PREDICTION ON THE TEST SET
# ============================================================
def predict_test(x_test, y_test):
    with open(NORM_PATH) as f:
        norm = json.load(f)

    x_pad = mb.pad32(x_test)
    test_ds = mb.make_ds(x_pad, y_test, norm["mean"], norm["std"], train=False)

    best = tf.keras.models.load_model(MODEL_PATH)
    y_pred = np.argmax(best.predict(test_ds, verbose=1), axis=1)   # order preserved
    return x_pad, y_pred


# ============================================================
# CONFUSION ANALYSIS
# ============================================================
def plot_full_matrix(cm_norm):
    fig, ax = plt.subplots(figsize=(10, 9))
    im = ax.imshow(cm_norm * 100, cmap="Blues", vmin=0, vmax=100)
    ax.set_xticks(range(20)); ax.set_xticklabels(CLASS_NAMES, rotation=90)
    ax.set_yticks(range(20)); ax.set_yticklabels(CLASS_NAMES)
    ax.axhline(9.5, color="red", lw=1.5)      # Western | Arabic boundary
    ax.axvline(9.5, color="red", lw=1.5)
    ax.set_xlabel("Predicted"); ax.set_ylabel("True")
    ax.set_title("20-class confusion matrix (row-normalised, %)")
    plt.colorbar(im, ax=ax)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "confusion_full.png"), dpi=300)
    plt.show()


def plot_block(block, title, row_names, col_names, fname, ylabel, xlabel):
    """Annotated 10x10 block of the row-normalised confusion matrix (%)."""
    vals = block * 100
    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(vals, cmap="Blues", vmin=0)
    ax.set_xticks(range(10)); ax.set_xticklabels(col_names)
    ax.set_yticks(range(10)); ax.set_yticklabels(row_names)
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel); ax.set_title(title)
    for r in range(10):
        for c in range(10):
            if vals[r, c] >= 0.1:
                ax.text(c, r, f"{vals[r, c]:.1f}", ha="center", va="center",
                        color="white" if vals[r, c] > vals.max() / 2 else "black",
                        fontsize=9)
    plt.colorbar(im, ax=ax, label="% of true class")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, fname), dpi=300)
    plt.show()


def analyse(x_pad, y_true, y_pred):
    cm = confusion_matrix(y_true, y_pred, labels=list(range(20)))
    cm_norm = cm / cm.sum(axis=1, keepdims=True)
    np.savetxt(os.path.join(OUT_DIR, "confusion_matrix.csv"), cm,
               fmt="%d", delimiter=",")

    # ---- Summary numbers ----
    acc = np.mean(y_true == y_pred)
    sys_true, sys_pred = y_true >= 10, y_pred >= 10
    errors = y_true != y_pred
    cross = sys_true != sys_pred
    print("\n" + "=" * 60)
    print(f"20-class test accuracy         : {acc:.4%}")
    print(f"  Western digits accuracy      : {np.mean(y_true[~sys_true] == y_pred[~sys_true]):.4%}")
    print(f"  Arabic-Indic digits accuracy : {np.mean(y_true[sys_true] == y_pred[sys_true]):.4%}")
    print(f"Writing-system accuracy        : {np.mean(sys_true == sys_pred):.4%}")
    print(f"Errors: {errors.sum()}  of which cross-system: {(errors & cross).sum()} "
          f"({(errors & cross).sum() / max(errors.sum(), 1):.1%})")

    # ---- Matrices ----
    plot_full_matrix(cm_norm)
    plot_block(cm_norm[:10, 10:],
               "Western digit predicted as Arabic-Indic digit",
               WESTERN, ARABIC, "confusion_W_to_A.png",
               "True (Western)", "Predicted (Arabic-Indic)")
    plot_block(cm_norm[10:, :10],
               "Arabic-Indic digit predicted as Western digit",
               ARABIC, WESTERN, "confusion_A_to_W.png",
               "True (Arabic-Indic)", "Predicted (Western)")

    # ---- Rank cross-system pairs ----
    rows = []
    for i in range(10):
        for j in range(10):
            w2a, a2w = cm[i, 10 + j], cm[10 + j, i]
            n_w, n_a = cm[i].sum(), cm[10 + j].sum()
            rows.append({
                "western": i, "arabic": j,
                "W_to_A_pct": 100 * w2a / n_w,
                "A_to_W_pct": 100 * a2w / n_a,
                "pair_rate_pct": 100 * (w2a + a2w) / (n_w + n_a),
            })
    pairs = pd.DataFrame(rows).sort_values("pair_rate_pct", ascending=False)
    pairs.to_csv(os.path.join(OUT_DIR, "cross_pairs.csv"), index=False)

    print("\nMost confusable cross-system pairs:")
    print(pairs.head(10).round(2).to_string(index=False))

    # ---- Show the top pairs (mean test image of each class) ----
    top = pairs.head(TOP_PAIRS)
    fig, axes = plt.subplots(2, TOP_PAIRS, figsize=(3 * TOP_PAIRS, 6.5))
    for k, (_, r) in enumerate(top.iterrows()):
        wi, aj = int(r["western"]), int(r["arabic"])
        axes[0, k].imshow(x_pad[y_true == wi].mean(axis=0).squeeze(), cmap="gray")
        axes[0, k].set_title(f"Western {wi}")
        axes[1, k].imshow(x_pad[y_true == 10 + aj].mean(axis=0).squeeze(), cmap="gray")
        axes[1, k].set_title(f"Arabic A{aj}")
        axes[1, k].set_xlabel(f"pair confusion {r['pair_rate_pct']:.1f}%")
        axes[0, k].axis("off")
        axes[1, k].set_xticks([]); axes[1, k].set_yticks([])
    plt.suptitle("Top confusable pairs (class-average test images)")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "top_pairs.png"), dpi=300)
    plt.show()


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "train"
    if mode not in ("train", "analyse"):
        sys.exit("Use: python combined_20class.py [train|analyse]")

    x_train, y_train, x_test, y_test, zero_size = load_all()

    if mode == "train":
        train(x_train, y_train, x_test, y_test, zero_size)

    x_pad, y_pred = predict_test(x_test, y_test)
    analyse(x_pad, y_test, y_pred)
