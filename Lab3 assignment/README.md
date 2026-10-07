# ELCT918 – Lab 3: Real-Time Handwritten Digit Recognition with LeNet-5

A LeNet-5 convolutional network trained on MNIST and deployed in a real-time webcam application. 
The lab also covers two optional extensions: Arabic-Indic digits (MADBase) and a single 20-class model that recognises both digit systems.

---

## Contents

- [Repository structure](#repository-structure)
- [Setup](#setup)
- [Datasets](#datasets)
- [Task 1 – Training LeNet-5 on MNIST](#task-1--training-lenet-5-on-mnist)
- [Task 2 – Preprocessing pipeline](#task-2--preprocessing-pipeline)
- [Task 3 – Real-time application](#task-3--real-time-application)
- [Running on a video file or another camera](#running-on-a-video-file-or-another-camera)
- [Bonus – Arabic-Indic digits (MADBase)](#bonus--arabic-indic-digits-madbase)
- [Optional – Single 20-class model](#optional--single-20-class-model)
- [Trained weights](#trained-weights)
- [Results](#results)
- [Troubleshooting](#troubleshooting)

---

## Repository structure

```
ELCT918/
└── Lab3 assignment/
    ├── MNIST_Train.py              # LeNet-5, training/evaluation, preprocessing pipeline
    ├── realtime_digit.py           # Real-time app (Western digits)
    ├── MADBase_Train.py            # Bonus: orientation check + training on MADBase
    ├── realtime_digit_MAD.py       # Bonus: real-time app (Arabic-Indic digits)
    ├── combined_20_Model.py        # Optional: 20-class training + confusion analysis
    ├── realtime_digit_combined.py        # Optional: real-time app (20-class model)
    ├── Outputs_MNIST/
    │   ├── models/LeNet_MNIST_best.keras
    │   ├── results/                # history and evaluation CSV files
    │   └── figures/                # accuracy / loss curves
    ├── Outputs_MADBase/
    │   ├── LeNet_MADBase_best.keras
    │   └── madbase_norm.json       # mean, std, median zero-dot size
    ├── Outputs_Combined/
    │   ├── LeNet_20class_best.keras
    │   └── norm_20class.json
    ├── Preprocessing_Images/       # sample image for the preprocessing test
    ├── requirements.txt
    └── README.md
```

The datasets are **not** included (see [Datasets](#datasets)).

---

## Setup

Python 3.9 or newer is recommended.

```bash
git clone https://github.com/AlaaTaha32/ELCT918.git
cd "ELCT918/Lab3 assignment"

python -m venv venv
# Windows:  venv\Scripts\activate
# Linux/macOS:  source venv/bin/activate

pip install -r requirements.txt
```

`requirements.txt`:

```
tensorflow
opencv-python
numpy
pandas
matplotlib
scikit-learn
pillow
```

Run all scripts from inside the `Lab3 assignment` folder, because paths are relative to it.

---

## Datasets

**MNIST** (PNG folders), placed next to the scripts:

```
MNIST/
├── training/   0/ 1/ ... 9/
└── testing/    0/ 1/ ... 9/
```

**MADBase / AHDD1** (CSV files, from the Kaggle "Arabic Handwritten Digits Dataset"):

```
AHDD/
├── csvTrainImages 60k x 784.csv
├── csvTrainLabel 60k x 1.csv
├── csvTestImages 10k x 784.csv
└── csvTestLabel 10k x 1.csv
```

---

## Task 1 – Training LeNet-5 on MNIST

`MNIST_Train.py` contains the full experiment.

| Item | Setting |
|---|---|
| Architecture | LeNet-5: Conv(6, 5×5) → AvgPool → Conv(16, 5×5) → AvgPool → FC 120 → FC 84 → 10 logits, tanh activations |
| Input | 28×28 digit zero-padded to 32×32 |
| Normalisation | `(x − 0.1307) / 0.3081` |
| Split | 55,000 train / 5,000 validation (stratified) / 10,000 test |
| Loss | Sparse categorical cross-entropy (`from_logits=True`) |
| Optimiser | SGD, momentum 0.9, weight decay 5e-4 |
| Learning rate | 0.01 → 0.001 → 0.0001 (step schedule) |
| Batch size | 128 |
| Epochs | 30 |
| Seed | 42 |
| Model selection | Best validation accuracy checkpoint |

The output layer has no softmax. Softmax is applied at inference time to get confidence values.

To train, set the task number in the last line of `MNIST_Train.py` to `1` and run:

```bash
python MNIST_Train.py
```

Outputs are saved to `Outputs_MNIST/` (best model, history CSV, accuracy and loss plots, evaluation CSV).

---

## Task 2 – Preprocessing pipeline

`preprocess_image()` in `MNIST_Train.py` converts a camera image into the format the network was trained on:

1. Grayscale conversion
2. Gaussian blur (5×5)
3. Otsu thresholding with inversion (white digit on black background, as in MNIST)
4. Optional dilation
5. Largest valid contour → bounding-box crop (specks and contours touching the border are ignored)
6. Resize so the longer side is 20 px, keeping the aspect ratio
7. Centre in a 28×28 canvas
8. Zero-pad to 32×32
9. Scale to [0, 1] and normalise with the MNIST mean and std

A blank image (very low contrast) or a frame with no valid contour raises a `ValueError`, which the real-time app reports as "No digit detected".

To visualise every step on a test image, set the task number in `MNIST_Train.py` to `2` and run:

```bash
python MNIST_Train.py
```

---

## Task 3 – Real-time application

```bash
python realtime_digit.py
```

- Write a digit (dark ink on white paper, a thick marker works best) inside the white box.
- The window shows the predicted digit, the softmax confidence, and the FPS. Below the confidence threshold (0.50) the prediction is shown as `?`.
- A second window, **Model Input**, shows the exact 32×32 image the network receives.
- The image is mirrored on screen only. The ROI is cropped from the unmirrored frame, so the network always sees correctly oriented digits.
- Press `q` to quit, `r` to start or stop recording a demo video.

---

## Bonus – Arabic-Indic digits (MADBase)

### 1. Training

```bash
python MADBase_Train.py check    # visualise samples to verify orientation and labels
python MADBase_Train.py train    # train, validate, test
```

The `check` step shows each sample both as-is and transposed. The AHDD CSV images are commonly stored transposed, so set `TRANSPOSE` at the top of `MADBase_Train.py` to match whichever row shows upright digits with the correct labels. Training reuses the same architecture and hyperparameters as Task 1, with data augmentation (small rotation, shift, zoom) applied to the training set only. The normalisation mean and std are computed from the MADBase training split and saved to `madbase_norm.json`.

### 2. Real-time application

```bash
python realtime_digit_MAD.py
```

Same interface as Task 3. Arabic-Indic glyphs (٠ – ٩) are drawn on screen if a suitable font is found (set `FONT_PATH` in the script for non-Windows systems).

### 3. The Arabic-Indic zero (٠)

The zero is written as a small dot, which breaks the standard crop-and-resize steps:

- **Crop:** the bounding box of a dot contains almost no shape information.
- **Resize:** scaling the longer side to 20 px turns the dot into a large blob. Size is the main feature that identifies ٠, and normal resizing destroys it. Scaling would also enlarge noise specks in the same way.
- **Blur and dilation:** the 5×5 blur can shrink a small dot below the Otsu threshold, and a 2×2 dilation visibly inflates it.
- **Speck filtering:** a minimum-area filter that removes noise can also remove a real dot if set too high.

How it is handled:

- A contour whose longer side is below 15% of the ROI is treated as a dot (`DOT_RATIO`).
- Instead of 20 px, a dot is scaled to the **median zero size measured on the training data**, so it looks like the zeros in MADBase.
- Dilation is skipped for dots.
- A blank-image contrast check and a small minimum-area filter keep noise from being mistaken for a dot.

---

## Optional – Single 20-class model

One LeNet-5 with 20 outputs: classes 0–9 are the Western digits (MNIST) and classes 10–19 are the Arabic-Indic digits (MADBase).

```bash
python combined_20_Model.py train      # train, test, then analyse
python combined_20_Model.py analyse    # redo only the analysis from the saved model
python realtime_digit_combined.py           # real-time app
```

The analysis step writes to `Outputs_Combined/`:

- `confusion_full.png` – full 20×20 confusion matrix (row-normalised)
- `confusion_W_to_A.png` and `confusion_A_to_W.png` – the cross-system blocks (Western predicted as Arabic-Indic, and the reverse)
- `cross_pairs.csv` – all Western/Arabic digit pairs ranked by confusion rate
- `top_pairs.png` – class-average images of the most confusable pairs

**Most confusable cross-system pairs:**
| Pair | Confusion rate
|---|---|
| Western 0 & Arabic 5 | 18.2% |
| Western 1 & Arabic 1 | 12.8% |
| Western 9 & Arabic 9 | 7.7% |
| Western 7 & Arabic 6 | 3.4% |


The real-time app also displays the runner-up class and its probability, which makes ambiguous pairs visible during the demo.

---

## Running on a video file or another camera

All three real-time applications read from a single setting, `CAMERA_INDEX`, in the configuration block at the top of the script. To change the input, edit that one line and run the script as usual:

```python
CAMERA_INDEX = 0                       # default: laptop webcam
CAMERA_INDEX = 1                       # another camera, e.g. a phone used as a webcam (try 0, 1, 2)
CAMERA_INDEX = "videos/digits.mp4"     # a recorded video file instead of a live camera
```

| Application | Script to edit |
|---|---|
| Western digits (MNIST) | `realtime_digit.py` |
| Arabic-Indic digits (MADBase) | `realtime_digit_MAD.py` |
| 20-class model | `realtime_digit_combined.py` |

Notes:

- The video path is relative to the `Lab3 assignment` folder. On Windows, use forward slashes (`"videos/digits.mp4"`) or a raw string (`r"C:\videos\digits.mp4"`).
- The application stops when the video ends, or when you press `q`.
- The digit is read from the fixed box in the centre of the frame, so record the video with the written digit held in the middle of the picture.
- A video file is processed as fast as the computer allows. To play it at normal speed, change `cv2.waitKey(1)` to `cv2.waitKey(30)` in the main loop.
- If the digits look backwards in the **Model Input** window, the video was recorded with a mirrored camera (for example a phone's front camera). In that case, flip the cropped region instead of the full frame.

---

## Trained weights

All weights are small (well under GitHub's 100 MB limit) and are included in the repository.

| Model | File |
|---|---|
| LeNet-5, MNIST | `Outputs_MNIST/models/LeNet_MNIST_best.keras` |
| LeNet-5, MADBase | `Outputs_MADBase/LeNet_MADBase_best.keras` (+ `madbase_norm.json`) |
| LeNet-5, 20-class | `Outputs_Combined/LeNet_20class_best.keras` (+ `norm_20class.json`) |

The `.json` files hold the normalisation statistics and must stay next to the models they belong to.

---

## Results

| Model | Best validation accuracy | Test accuracy |
|---|---|---|
| MNIST | 99.14% | 99.21% |
| MADBase | 99.42% | 99.17% |
| 20-class (Western + Arabic-Indic) | 94.56% | 94.16% |

---

## Troubleshooting

- **Digits look backwards in the "Model Input" window.** Your camera or driver already mirrors the feed. Flip the ROI instead of the frame.
- **It predicts a digit when nothing is written.** Increase `MIN_CONTRAST` or `MIN_AREA_RATIO` so noise and shadows are rejected.
- **Thin pen strokes are misread.** Use a thick marker, or keep `DILATION = True`.
- **Arabic glyphs appear as plain digits.** The font in `FONT_PATH` was not found. Point it to a font that contains Arabic-Indic digits.
- **`ModuleNotFoundError: MNIST_Train`.** Run the scripts from inside the `Lab3 assignment` folder.
