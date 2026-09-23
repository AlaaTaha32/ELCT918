"""
Pareto-Optimal Design Space Exploration
========================================

This module analyzes the results of neural-network design space exploration
(DSE) and identifies the Pareto-optimal configurations based on:

    1. Model cost, represented by the number of trainable parameters.
    2. Accuracy drop, defined as:
           Accuracy Drop (%) = 100 - Test Accuracy (%)

A configuration is Pareto-optimal if no other configuration has both:
    - lower or equal cost, and
    - lower or equal accuracy drop,
while being strictly better in at least one objective.

The module also visualizes the explored configurations and highlights the
Pareto-optimal front.

"""

import os
import numpy as np
import tensorflow as tf
from PIL import Image
import matplotlib.pyplot as plt
import time
import pandas as pd

def load_split(root):
    images, labels = [], []
    for digit in range(10):
        folder = os.path.join(root, str(digit))
        for fname in os.listdir(folder):
            img = Image.open(os.path.join(folder, fname)).convert("L")
            images.append(np.array(img, dtype=np.float32).reshape(784) / 255.0)
            labels.append(digit)
    return np.stack(images), np.array(labels, dtype=np.int64)

def build_model(n, m):
    """
    Build a fully-connected neural network.

    Parameters:
        n: number of hidden layers
        m: number of nodes in each hidden layer
    """

    model = tf.keras.Sequential()

    # Input layer + first hidden layer
    model.add(tf.keras.layers.Dense(
        m,
        activation="relu",
        input_shape=(784,)
    ))

    # Remaining hidden layers
    for _ in range(n - 1):
        model.add(tf.keras.layers.Dense(
            m,
            activation="relu"
        ))


    # Output layer using the softmax activation function
    model.add(tf.keras.layers.Dense(
        10,
        activation="softmax"
    ))

    return model

def train_and_evaluate(model, x_train, y_train, x_test, y_test, epoch_count, batch_size):
    """
    Train the model and evaluate its performance on the test set.

    Parameters:
        model: current built model architecture
        x_train: training set inputs
        y_train: training set labels
        x_test: testing set inputs
        y_test: testing set labels
        epoch_count: number of epochs
        batch_size: batch size
    """

    model.compile(
        optimizer="adam",
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )

    model.summary()

    model.fit(x_train, y_train, epochs=epoch_count, batch_size=batch_size)

    loss, accuracy = model.evaluate(x_test, y_test)

    return loss, accuracy

def dominates(a, b):
    """
    Checks if a candidate model dominates b candidate mode.
    """

    dominated = (
        (a["Parameters Count (Cost)"] < b["Parameters Count (Cost)"] and a["Accuracy Drop (%)"] <= b["Accuracy Drop (%)"])
        or
         (a["Accuracy Drop (%)"] < b["Accuracy Drop (%)"] and a["Parameters Count (Cost)"] <= b["Parameters Count (Cost)"])
    )

    return dominated

def find_pareto_front(results):
    """
    Find the non-dominated candidates list (pareto_front) from all candidates set.
    """

    # Find non-dominated configurations list
    pareto_front = []

    for i, candidate in enumerate(results):
        dominated = False
        for j, other in enumerate(results):
            if i != j and dominates(other, candidate):
                dominated = True # if ith candidate is dominated by any other candidate, it is not in the pareto front
                break
        if not dominated:
            pareto_front.append(candidate)

    return pareto_front

def plot_pareto_front(results, pareto_front):
    """
    Plotting the pareto front plot along with the dominated candidates with x-axis representing cost and
    y-axis representing accuracy drop.
    """

    # Creating a list of dominated candidates by removing any candidate in the pareto_front list from the all candidates' list
    pareto_ids = {id(x) for x in pareto_front}
    dominated = [
        r for r in results
        if id(r) not in pareto_ids
    ]

    # Dominated configurations
    plt.scatter(
        [r["Parameters Count (Cost)"] for r in dominated],
        [r["Accuracy Drop (%)"] for r in dominated],
        label="Dominated"
    )

    # Pareto-optimal configurations, marked as x
    plt.scatter(
        [r["Parameters Count (Cost)"] for r in pareto_front],
        [r["Accuracy Drop (%)"] for r in pareto_front],
        marker="x",
        s=100,
        label="Pareto-optimal"
    )

    # Connect Pareto points
    pareto_sorted = sorted(
        pareto_front,
        key=lambda r: r["Parameters Count (Cost)"]
    )

    plt.plot(
        [r["Parameters Count (Cost)"] for r in pareto_sorted],
        [r["Accuracy Drop (%)"] for r in pareto_sorted],
        linestyle="--"
    )

    plt.xlabel("Cost (Number of Parameters)")
    plt.ylabel("Accuracy Drop (%)")
    plt.title("Pareto-Optimal Front")
    plt.legend()
    plt.grid(True)
    plt.show()

def main():

    # Loading MNIST training and testing datasets (folders of digits)
    print("loading MNIST PNG dataset...")
    x_train, y_train = load_split("MNIST/training")
    x_test, y_test = load_split("MNIST/testing")
    print(f"train: {x_train.shape}, test: {x_test.shape}")

    # Training settings
    epochs = 10
    batch_size = 200

    # Vector of number of hidden layers
    n = [1, 2, 3, 4]

    # Vector of number of nodes per hidden layer
    m = [10, 20, 40, 60, 80, 160, 200]

    # History of each candidate's results
    results = []

    # Building, training, evaluating, and recording the results of the different architecture configurations
    for i in n:
        for j in m:
            print(f"\n{'=' * 70}")
            print(f"Network: {i} hidden layers, {j} nodes/layer")
            print(f"{'=' * 70}")

            start = time.perf_counter()

            model = build_model(i, j)

            loss, accuracy = train_and_evaluate(model,
                                                x_train,y_train,
                                                x_test,y_test,
                                                epochs, batch_size)

            # histories[(i, j)] = history

            training_time = time.perf_counter() - start

            num_params = model.count_params()

            print(f"Training time: {training_time:.2f} seconds")
            print(f"Test loss: {loss:.4f}")
            print(f"Test accuracy: {accuracy:.4f}\n")

            accuracy_drop = (1 - accuracy) * 100

            #if accuracy >= 0.965 and num_params < 70000:
            results.append({
                "Hidden Layers": i,
                "Nodes / Layer": j,
                "Training Time (s)": training_time,
                "Test Loss": loss,
                "Accuracy Drop (%)": accuracy_drop,
                "Parameters Count (Cost)": num_params
            })

    # Displaying the results of every candidate architecture as a table
    df = pd.DataFrame(results)
    print(df.to_string(index=False))

    # Finding, displaying, and plotting the pareto_front (non-dominated configurations)
    pareto_front = find_pareto_front(results)
    print("\nPareto-optimal configurations:")
    for config in pareto_front:
        print(
            f"Hidden Layers = {config['Hidden Layers']}, "
            f"Nodes / Layer = {config['Nodes / Layer']}, "
            f"Training Time (s) = {config['Training Time (s)']:.3f}, "
            f"Test Loss = {config['Test Loss']:.2f}, "
            f"Accuracy Drop (%) = {config['Accuracy Drop (%)']:.3f}%, "
            f"Parameters Count (Cost) = {config['Parameters Count (Cost)']}"
        )

    plot_pareto_front(results, pareto_front)

if __name__ == "__main__":
    main()
