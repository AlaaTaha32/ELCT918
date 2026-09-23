# ELCT918 - Lab 1 Assignment

## Overview

This project implements neural-network Design Space Exploration (DSE) for
different combinations of hidden layers and hidden nodes per layer.

For each explored configuration, the implementation measures:

- Test accuracy drop (%)
- Test loss
- Training time
- Number of parameters, as a measure of computational cost 

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


## Program Pipeline
- Load the MNIST dataset.
- Define the training settings (number of epochs, batch size)
- Explore the defined neural-network configurations.
- Train and evaluate each configuration.
- Record the test loss, accuracy, training time, and parameter count.
- Calculate the accuracy drop.
- Identify the Pareto-optimal configurations.
- Generate a Pareto-front visualization.

## Installation and Running

Install the required Python packages using:
```bash
pip install numpy pandas matplotlib tensorflow

python main.py
```
## Implemented Space Exploration

Each neural-network configuration was trained and evaluated using the same
training settings to ensure a fair comparison across the explored design space.

### Training Settings

| Setting | Value |
|---|---|
| Number of epochs | 10 |
| Batch size | 200 |
| Hidden layers (`n`) | 1, 2, 3, 4, 5 |
| Nodes per hidden layer (`m`) | 10, 20, 40, 60, 80, 120, 160, 200 |
| Hidden-layers activation | ReLU |
| Output-layer activation | Softmax |
| Dataset | MNIST |

The design space consists of all combinations of the specified numbers of
hidden layers and nodes per hidden layer. This results in:

**5 × 8 = 40 neural-network configurations.**

For each configuration, the following metrics were recorded:

- Test loss
- Test accuracy
- Accuracy drop
- Training time
- Number of parameters

The **accuracy drop** is calculated as:

```text
Accuracy Drop (%) = 100 - Test Accuracy (%)
```

### Results
The results show how changing the network depth and width affects the
trade-off between model cost and classification performance.

Increasing the number of hidden layers or nodes per hidden layer increases
the number of trainable parameters and therefore the model cost. At the same
time, larger networks may achieve a lower accuracy drop due to their greater
representational capacity.

However, increasing the network size does not necessarily provide a
proportional improvement in accuracy. Some larger configurations can
therefore be dominated by smaller configurations that achieve an equal or
better accuracy with fewer parameters.

To identify the most efficient configurations, the 40 explored architectures
were evaluated using two objectives:

- Minimize model cost — number of trainable parameters.
- Minimize accuracy drop — 100 - test accuracy.

A configuration is considered Pareto-optimal when no other explored
configuration has both a lower or equal parameter count and a lower or equal
accuracy drop, while being strictly better in at least one objective.

The Pareto-optimal configurations represent different trade-offs between
model complexity and classification performance. The Pareto front therefore
provides a way to identify candidate architectures based on the desired
balance between model cost and accuracy.


### Pareto-Optimal Front
The following plot shows all explored neural-network configurations, with
the Pareto-optimal configurations visually distinguished from the dominated
configurations.
![Pareto-Optimal Front](Paret_Optimal_Front.png)  
