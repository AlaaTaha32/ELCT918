# ELCT918 - Lab 1 Assignment

## Overview

This project implements neural-network Design Space Exploration (DSE) for
different combinations of hidden layers and hidden nodes per layer.

For each explored configuration, the implementation measures:

- Test accuracy
- Test loss
- Training time
- Number of trainable parameters

The explored configurations are then analyzed using Pareto-optimality,
considering model cost and accuracy drop as the two optimization objectives.

Accuracy drop is calculated as:

Accuracy Drop (%) = 100 - Test Accuracy (%)

## Requirements

- Python 3.x
- NumPy
- Pandas
- Matplotlib
- TensorFlow / Keras

## Installation

Install the required Python packages using:

```bash
pip install numpy pandas matplotlib tensorflow
