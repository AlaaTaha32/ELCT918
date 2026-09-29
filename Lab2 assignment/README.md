# ELCT918 — Lab Assignment 2

## Comparative Study of Classical CNN Architectures

This assignment implements and compares three classical Convolutional Neural Network (CNN) architectures:

* **LeNet-5**
* **AlexNet**
* **VGG16**

The architectures are adapted where necessary for **32×32 CIFAR images** and trained from scratch on both **CIFAR-10** and **CIFAR-100** using the same deep-learning framework and training configuration for a fair comparison.

---

## Objectives

The main objectives of this assignment are to:

1. Implement LeNet-5, AlexNet, and VGG16.
2. Adapt the architectures to CIFAR-sized inputs where necessary.
3. Compare their architectural characteristics, including:

   * Layer structure
   * Filter sizes and strides
   * Feature-map dimensions
   * Network depth
   * Number of trainable parameters
4. Train and evaluate all three architectures on CIFAR-10 and CIFAR-100.
5. Compare their classification accuracy, training behavior, and computational cost.
6. Analyze the relationship between network depth, model capacity, and performance.

---

## Architectures

### LeNet-5

The original LeNet architecture is a relatively shallow CNN designed primarily for handwritten digit recognition. Its structure relies on convolutional and pooling layers followed by fully connected layers.

For this assignment, LeNet-5 is adapted to accept **32×32 RGB CIFAR images** and produce either 10 or 100 output classes.

### AlexNet

AlexNet is a deeper and wider CNN architecture originally developed for large-scale image classification. Its characteristic features include relatively large early convolutional filters, multiple convolutional stages, pooling, and fully connected layers.

The architecture is adapted for the smaller **32×32 CIFAR input resolution** while preserving its main structural characteristics.

### VGG16

VGG16 uses a much deeper architecture based primarily on stacks of **3×3 convolutional filters**, followed by pooling and fully connected layers.

The CIFAR implementation adapts the spatial dimensions where necessary while maintaining the characteristic VGG design philosophy of using small filters and increased depth.

---

## Datasets

Each architecture is trained and evaluated independently on:

| Dataset   | Classes | Input     |
| --------- | ------: | --------- |
| CIFAR-10  |      10 | 32×32 RGB |
| CIFAR-100 |     100 | 32×32 RGB |

This results in **six model/dataset combinations**:

| Architecture | CIFAR-10 | CIFAR-100 |
| ------------ | -------- | --------- |
| LeNet-5      | ✓        | ✓         |
| AlexNet      | ✓        | ✓         |
| VGG16        | ✓        | ✓         |

---

## Experimental Setup

To make the comparison as consistent as possible, the same training configuration is used for all three architectures within each dataset.

The following settings are kept fixed:

* Framework
* Number of epochs
* Optimizer
* Batch size
* Learning rate
* Data augmentation, if used

All models are **trained from scratch**; no pretrained weights are used.

Specific implementation and training details are documented in the corresponding source files and report.

---

## Evaluation Metrics

The following metrics are collected for each experiment:

* **Top-1 test accuracy**
* **Top-5 test accuracy** for CIFAR-100
* Training accuracy
* Validation accuracy
* Training loss
* Validation loss
* Training time per epoch
* Total trainable parameters
* Model depth

The **accuracy drop** is also calculated as:

```text
Accuracy Drop (%) = 100% − Test Accuracy (%)
```

This provides a consistent measure for comparing the classification performance of all six experiments.

---


## Requirements

The implementation uses **TensorFlow/Keras** for all three architectures.

Required Python packages include:

```text
Python 3.x
TensorFlow
NumPy
os
Panda
Matplotlib
```
---


**Course:** ELCT918
**Assignment:** Lab Assignment 2
**Topic:** Comparative Study of Classical CNN Architectures
**Architectures:** LeNet-5, AlexNet, VGG16
**Datasets:** CIFAR-10, CIFAR-100
**Framework:** TensorFlow / Keras
