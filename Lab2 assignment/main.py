# ============================================================
# LAB 2 - COMPARATIVE STUDY OF CLASSICAL CNN ARCHITECTURES
# ============================================================
# # Architectures:
#   1. LeNet-5
#   2. AlexNet
#   3. VGG16 
# # Datasets:
#   1. CIFAR-10
#   2. CIFAR-100
# # Framework: TensorFlow / Keras
# ============================================================


# ============================================================
# 1. IMPORTS
# ============================================================
import os
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf
from sklearn.model_selection import train_test_split

from tensorflow import keras
from tensorflow.keras import layers

#print("TensorFlow:", tf.__version__)
print("GPU:", tf.config.list_physical_devices('GPU'))


# ============================================================
# 2. PROJECT DIRECTORIES (Used in Google Colab)
# ============================================================
# Mount Google Drive from google.colab
from google.colab import drive
drive.mount("/content/drive")
# Main project directory
BASE_DIR = "/content/drive/MyDrive/Lab2_CNN"
# Create the complete directory structure
def create_project_directories():
  """
  Create the directory structure used to store: - Training results - Trained models - Figures
  Directory structure: Lab2_CNN/
                          CIFAR_10/
                            LeNet/
                              results/
                              models/
                              figures/
                            AlexNet/
                              results/
                              models/
                              figures/
                            VGG16/
                              results/
                              models/
                              figures/

                          CIFAR_100/
                            LeNet/
                              results/
                              models/
                              figures/
                            AlexNet/
                              results/
                              models/
                              figures/
                            VGG16/
                              results/
                              models/
                              figures/
  """
  datasets = ["CIFAR_10", "CIFAR_100"]
  architectures = ["LeNet", "AlexNet", "VGG16"]
  subfolders = ["results", "models", "figures"]
  for dataset in datasets:
    for architecture in architectures:
      for subfolder in subfolders:
        path = os.path.join( BASE_DIR, dataset, architecture, subfolder )
        os.makedirs(path, exist_ok=True)
  print("Project directories created successfully.")


# ============================================================
# 3. DATASET LOADING AND SAVING
# ============================================================

DATASET_BASE_DIR = "/content/drive/MyDrive/my_datasets"

CIFAR10_DIR = os.path.join(DATASET_BASE_DIR, "cifar_10")
CIFAR100_DIR = os.path.join(DATASET_BASE_DIR, "cifar_100")

CIFAR10_FILE = os.path.join(CIFAR10_DIR, "cifar10.npz")
CIFAR100_FILE = os.path.join(CIFAR100_DIR, "cifar100.npz")


def load_or_download_cifar(dataset_name):
    """
    Load CIFAR-10 or CIFAR-100 from Google Drive if a saved
    copy exists. Otherwise, download it using Keras, save it
    to Drive as a compressed NumPy file, and return it.

    Returns:
        (x_train, y_train), (x_test, y_test)

    Format is identical to:
        tf.keras.datasets.cifar10.load_data()
        tf.keras.datasets.cifar100.load_data()
    """

    # --------------------------------------------------------
    # Select dataset-specific paths
    # --------------------------------------------------------

    if dataset_name == "CIFAR_10":

        dataset_dir = CIFAR10_DIR
        dataset_file = CIFAR10_FILE

        keras_loader = tf.keras.datasets.cifar10.load_data

    elif dataset_name == "CIFAR_100":

        dataset_dir = CIFAR100_DIR
        dataset_file = CIFAR100_FILE

        keras_loader = tf.keras.datasets.cifar100.load_data

    else:
        raise ValueError(
            "dataset_name must be 'CIFAR_10' or 'CIFAR_100'"
        )

    # --------------------------------------------------------
    # Create directory if it does not exist
    # --------------------------------------------------------

    os.makedirs(dataset_dir, exist_ok=True)

    # --------------------------------------------------------
    # Check whether dataset is already saved
    # --------------------------------------------------------

    if os.path.exists(dataset_file):

        print(f"\nLoading {dataset_name} from Google Drive...")
        print(f"File: {dataset_file}")

        data = np.load(dataset_file)

        x_train = data["x_train"]
        y_train = data["y_train"]
        x_test = data["x_test"]
        y_test = data["y_test"]

        print("Dataset loaded successfully.")

    else:

        # ----------------------------------------------------
        # Dataset does not exist locally → download
        # ----------------------------------------------------

        print(f"\n{dataset_name} not found in Google Drive.")
        print("Downloading using TensorFlow/Keras...")

        (x_train, y_train), (x_test, y_test) = keras_loader()
        #if dataset_name == "CIFAR_10":
        #   (x_train, y_train), (x_test, y_test) = cifar10_data
        #elif dataset_name == "CIFAR_100":
        #   (x_train, y_train), (x_test, y_test) = cifar100_data

        print("Download completed.")

        # ----------------------------------------------------
        # Save compressed NumPy arrays to Google Drive
        # ----------------------------------------------------

        print("Saving dataset to Google Drive...")

        np.savez_compressed(
            dataset_file,
            x_train=x_train,
            y_train=y_train,
            x_test=x_test,
            y_test=y_test
        )

        print(f"Dataset saved to:")
        print(dataset_file)

    # --------------------------------------------------------
    # Return exactly the same structure as Keras
    # --------------------------------------------------------
    print("Training images:", x_train.shape)
    print("Training labels:", y_train.shape)
    print("Test images:", x_test.shape)
    print("Test labels:", y_test.shape)

    return (x_train, y_train), (x_test, y_test)


cifar10_data = load_or_download_cifar("CIFAR_10")
cifar100_data = load_or_download_cifar("CIFAR_100")


# ============================================================
# 4. SPLIT TRAINING / VALIDATION DATA AND CREATE DATASETS
# ============================================================
def prepare_dataset(dataset_data, validation_size=5000, batch_size=128):
  """
  Split the original training set into training and validation sets, then create TensorFlow Dataset objects.
  The official test set remains untouched and is only used for final evaluation.
  Parameters ----------
  dataset_data : tuple ((x_train, y_train), (x_test, y_test))
  validation_size : int Number of samples reserved for validation.
  batch_size : int Batch size used during training/evaluation.
  Returns -------
  x_train, y_train x_val, y_val x_test, y_test train_ds val_ds test_ds
  """
  (x_train, y_train), (x_test, y_test) = dataset_data

  # Remove the redundant label dimension:
  # CIFAR labels originally have shape (N, 1)
  y_train = y_train.squeeze()
  y_test = y_test.squeeze()

  # Split training data into training and validation sets.
  # Stratification preserves the class distribution.
  x_train, x_val, y_train, y_val = train_test_split( x_train, y_train, test_size=validation_size, random_state=42, stratify=y_train )

  # Create TensorFlow datasets
  train_ds = tf.data.Dataset.from_tensor_slices( (x_train, y_train) )
  val_ds = tf.data.Dataset.from_tensor_slices( (x_val, y_val) )
  test_ds = tf.data.Dataset.from_tensor_slices( (x_test, y_test) )

  # Shuffle only the training dataset
  train_ds = train_ds.shuffle( buffer_size=len(x_train), reshuffle_each_iteration=True )

  # Batch datasets
  train_ds = train_ds.batch(batch_size)
  val_ds = val_ds.batch(batch_size)
  test_ds = test_ds.batch(batch_size)
  return ( x_train, y_train, x_val, y_val, x_test, y_test, train_ds, val_ds, test_ds )

# Batch size used for all architectures
BATCH_SIZE = 128
# CIFAR-10
( x10_train, y10_train, x10_val, y10_val, x10_test, y10_test, cifar10_train_ds, cifar10_val_ds, cifar10_test_ds ) = prepare_dataset( cifar10_data, validation_size=5000, batch_size=BATCH_SIZE )
# CIFAR-100
( x100_train, y100_train, x100_val, y100_val, x100_test, y100_test, cifar100_train_ds, cifar100_val_ds, cifar100_test_ds ) = prepare_dataset( cifar100_data, validation_size=5000, batch_size=BATCH_SIZE )
print("\nCIFAR-10:")
print("Training:", x10_train.shape)
print("Validation:", x10_val.shape)
print("Test:", x10_test.shape)
print("\nCIFAR-100:")
print("Training:", x100_train.shape)
print("Validation:", x100_val.shape)
print("Test:", x100_test.shape)



# ============================================================
# 5. DATA AUGMENTATION AND NORMALIZATION
# ============================================================
def normalize_dataset(dataset):
  """ Normalize image pixel values from [0, 255] to [0, 1].
  """
  return dataset.map( lambda images, labels: ( tf.cast(images, tf.float32) / 255.0, labels ), num_parallel_calls=tf.data.AUTOTUNE )

# Data augmentation applied only to training data
data_augmentation = tf.keras.Sequential([ tf.keras.layers.RandomFlip( mode="horizontal" ),
                                         tf.keras.layers.RandomTranslation( height_factor=0.125, width_factor=0.125 ) ], name="data_augmentation")
def preprocess_datasets(train_ds, val_ds, test_ds):
  """ Apply normalization to all datasets. Apply data augmentation only to the training dataset. Validation and test data are NOT augmented.
  """
  # Normalize all datasets
  train_ds = normalize_dataset(train_ds)
  val_ds = normalize_dataset(val_ds)
  test_ds = normalize_dataset(test_ds)

  # Apply augmentation only during training
  def augment(images, labels):
    images = data_augmentation( images, training=True )
    return images, labels

  train_ds = train_ds.map( augment, num_parallel_calls=tf.data.AUTOTUNE )

  # Prefetch for improved input pipeline performance (fecth next batch while current batch is being trained)
  train_ds = train_ds.prefetch(tf.data.AUTOTUNE)
  val_ds = val_ds.prefetch(tf.data.AUTOTUNE)
  test_ds = test_ds.prefetch(tf.data.AUTOTUNE)

  return train_ds, val_ds, test_ds

( cifar10_train_ds, cifar10_val_ds, cifar10_test_ds ) = preprocess_datasets( cifar10_train_ds, cifar10_val_ds, cifar10_test_ds )
( cifar100_train_ds, cifar100_val_ds, cifar100_test_ds ) = preprocess_datasets( cifar100_train_ds, cifar100_val_ds, cifar100_test_ds )



# ============================================================
# 6. LOCAL RESPONSE NORMALIZATION
# ============================================================
class LRN(tf.keras.layers.Layer):
  """ Local Response Normalization layer.
  Used in the original AlexNet architecture after the first two convolutional layers.
  """
  def call(self, inputs):
    return tf.nn.local_response_normalization( inputs, depth_radius=2, bias=1.0, alpha=1e-4, beta=0.75 )



# ============================================================
# 7. ALEXNET ARCHITECTURE
# ============================================================
def build_alexnet(num_classes=10):
    """
    This method builds an AlexNet network based on the number of output class
    The classifier layer would have 10 neurons for the CIFAR 10 case and 100 neurons for CIFAR 100 case
    :param num_classes: number of output classes (classifications)
    :return: a Keras model
    """

    # Input size = 32*32 RGB image
    inputs = tf.keras.Input(shape=(32, 32, 3))

    # Conv1: 11*11*3, number of kernels = 96, strides = 1, padding = 5 (keeps dimensions the same)
    # Produced Feature map: 32*32*96
    x = tf.keras.layers.Conv2D(
        filters=96,
        kernel_size=(11, 11),
        strides=1,
        padding="same"
    )(inputs)

    # ReLU and Normalization layers
    x = tf.keras.layers.ReLU()(x)
    x = LRN()(x)

    # Pool1: 3*3, strides = 2
    # Produced Feature map: 16*16*96
    x = tf.keras.layers.MaxPooling2D(
        pool_size=(3, 3),
        strides=2
    )(x)

    # Conv2: 5*5*96, number of kernels = 256, strides = 1, padding = 2 (keeps dimensions the same)
    # Produced Feature map: 16*16*256
    x = tf.keras.layers.Conv2D(
        filters=256,
        kernel_size=(5, 5),
        strides=1,
        padding="same"
    )(x)

    x = tf.keras.layers.ReLU()(x)
    x = LRN()(x)

    # Pool2: 3*3, strides = 2
    # Produced Feature map: 8*8*96
    x = tf.keras.layers.MaxPooling2D(
        pool_size=(3, 3),
        strides=2
    )(x)

    # Conv3: 3*3*96, number of kernels = 384, strides = 1, padding = 1
    # Produced Feature map: 8*8*384
    x = tf.keras.layers.Conv2D(
        filters=384,
        kernel_size=(3, 3),
        strides=1,
        padding="same"
    )(x)

    x = tf.keras.layers.ReLU()(x)

    # Conv4: 3*3*384, number of kernels = 384, strides = 1, padding = 1
    # Produced Feature map: 8*8*384
    x = tf.keras.layers.Conv2D(
        filters=384,
        kernel_size=(3, 3),
        strides=1,
        padding="same"
    )(x)

    x = tf.keras.layers.ReLU()(x)

    # Conv5: 3*3*384, number of kernels = 256, strides = 1, padding = 1
    # Produced Feature map: 8*8*256
    x = tf.keras.layers.Conv2D(
        filters=256,
        kernel_size=(3, 3),
        strides=1,
        padding="same"
    )(x)

    x = tf.keras.layers.ReLU()(x)

    # Pool5: 3*3, strides = 2
    # Produced Feature map: 4*4*256
    x = tf.keras.layers.MaxPooling2D(
        pool_size=(3, 3),
        strides=2
    )(x)

    # Flatten features (4*4*256 --> 4096)
    x = tf.keras.layers.Flatten()(x)

    # Fully connected layers
    x = tf.keras.layers.Dense(
        4096,
        activation="relu"
    )(x)

    # Regularization by dropout
    x = tf.keras.layers.Dropout(0.5)(x)

    x = tf.keras.layers.Dense(
        4096,
        activation="relu"
    )(x)

    x = tf.keras.layers.Dropout(0.5)(x)

    # Classification layer (parameterized based on number of output classes)
    outputs = tf.keras.layers.Dense(
        num_classes
    )(x)

    return tf.keras.Model(
        inputs=inputs,
        outputs=outputs,
        name="AlexNet"
    )


# ============================================================
# 8. LENET ARCHITECTURE
# ============================================================

def build_lenet(num_classes=10):

    # --------------------------------------------------------
    # Input
    # --------------------------------------------------------

    inputs = tf.keras.Input(
        shape=(32, 32, 3),
        name="Input"
    )

    # --------------------------------------------------------
    # C1: Convolution
    # 6 filters, 5x5, stride 1, tanh
    # Output: 28 x 28 x 6
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
    # Output: 14 x 14 x 6
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
    # Output: 10 x 10 x 16
    #
    # Original LeNet-5 uses sparse connectivity between
    # S2 and C3. Standard Conv2D is used here as an adaptation.
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
    # Output: 5 x 5 x 16
    # --------------------------------------------------------

    x = tf.keras.layers.AveragePooling2D(
        pool_size=(2, 2),
        strides=2,
        padding="valid",
        name="S4"
    )(x)

    # --------------------------------------------------------
    # Flatten
    # 5 x 5 x 16 = 400
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
    # num_classes = 10 for CIFAR-10
    # num_classes = 100 for CIFAR-100
    #
    # No softmax: outputs are logits.
    # --------------------------------------------------------

    outputs = tf.keras.layers.Dense(
        num_classes,
        name="Output"
    )(x)

    # --------------------------------------------------------
    # Create Functional Model
    # --------------------------------------------------------

    return tf.keras.Model(
        inputs=inputs,
        outputs=outputs,
        name="LeNet"
    )



# ============================================================
# 9. VGG16 ARCHITECTURE
# ============================================================

def build_vgg16(num_classes=10):

    # --------------------------------------------------------
    # Input
    # --------------------------------------------------------

    inputs = tf.keras.Input(
        shape=(32, 32, 3),
        name="Input"
    )

    # --------------------------------------------------------
    # Block 1
    # 2 × Conv3x3, 64 filters
    # Output: 32 x 32 x 64
    # --------------------------------------------------------

    x = tf.keras.layers.Conv2D(
        64,
        (3, 3),
        strides=1,
        padding="same",
        activation="relu",
        name="Conv1_1"
    )(inputs)

    x = tf.keras.layers.Conv2D(
        64,
        (3, 3),
        strides=1,
        padding="same",
        activation="relu",
        name="Conv1_2"
    )(x)

    x = tf.keras.layers.MaxPooling2D(
        pool_size=(2, 2),
        strides=2,
        padding="valid",
        name="Pool1"
    )(x)

    # Output: 16 x 16 x 64

    # --------------------------------------------------------
    # Block 2
    # 2 × Conv3x3, 128 filters
    # Output: 16 x 16 x 128
    # --------------------------------------------------------

    x = tf.keras.layers.Conv2D(
        128,
        (3, 3),
        strides=1,
        padding="same",
        activation="relu",
        name="Conv2_1"
    )(x)

    x = tf.keras.layers.Conv2D(
        128,
        (3, 3),
        strides=1,
        padding="same",
        activation="relu",
        name="Conv2_2"
    )(x)

    x = tf.keras.layers.MaxPooling2D(
        pool_size=(2, 2),
        strides=2,
        padding="valid",
        name="Pool2"
    )(x)

    # Output: 8 x 8 x 128

    # --------------------------------------------------------
    # Block 3
    # 3 × Conv3x3, 256 filters
    # Output: 8 x 8 x 256
    # --------------------------------------------------------

    x = tf.keras.layers.Conv2D(
        256,
        (3, 3),
        strides=1,
        padding="same",
        activation="relu",
        name="Conv3_1"
    )(x)

    x = tf.keras.layers.Conv2D(
        256,
        (3, 3),
        strides=1,
        padding="same",
        activation="relu",
        name="Conv3_2"
    )(x)

    x = tf.keras.layers.Conv2D(
        256,
        (3, 3),
        strides=1,
        padding="same",
        activation="relu",
        name="Conv3_3"
    )(x)

    
    x = tf.keras.layers.MaxPooling2D(
        pool_size=(2, 2),
        strides=2,
        padding="valid",
        name="Pool3"
    )(x)
    
    # Output: 4 x 4 x 256

    # --------------------------------------------------------
    # Block 4
    # 3 × Conv3x3, 512 filters
    # Output: 4 x 4 x 512
    # --------------------------------------------------------

    x = tf.keras.layers.Conv2D(
        512,
        (3, 3),
        strides=1,
        padding="same",
        activation="relu",
        name="Conv4_1"
    )(x)

    x = tf.keras.layers.Conv2D(
        512,
        (3, 3),
        strides=1,
        padding="same",
        activation="relu",
        name="Conv4_2"
    )(x)

    x = tf.keras.layers.Conv2D(
        512,
        (3, 3),
        strides=1,
        padding="same",
        activation="relu",
        name="Conv4_3"
    )(x)

    x = tf.keras.layers.MaxPooling2D(
        pool_size=(2, 2),
        strides=2,
        padding="valid",
        name="Pool4"
    )(x)

    # Output: 2 x 2 x 512

    # --------------------------------------------------------
    # Block 5
    # 3 × Conv3x3, 512 filters
    # Output: 2 x 2 x 512
    # --------------------------------------------------------

    x = tf.keras.layers.Conv2D(
        512,
        (3, 3),
        strides=1,
        padding="same",
        activation="relu",
        name="Conv5_1"
    )(x)

    x = tf.keras.layers.Conv2D(
        512,
        (3, 3),
        strides=1,
        padding="same",
        activation="relu",
        name="Conv5_2"
    )(x)

    x = tf.keras.layers.Conv2D(
        512,
        (3, 3),
        strides=1,
        padding="same",
        activation="relu",
        name="Conv5_3"
    )(x)

    
    x = tf.keras.layers.MaxPooling2D(
        pool_size=(2, 2),
        strides=2,
        padding="valid",
        name="Pool5"
    )(x)
    

    # Output: 1 x 1 x 512

    # --------------------------------------------------------
    # Classifier
    # --------------------------------------------------------

    x = tf.keras.layers.Flatten(
        name="Flatten"
    )(x)

    # 512 features

    x = tf.keras.layers.Dense(
        4096,
        activation="relu",
        name="FC6"
    )(x)

    x = tf.keras.layers.Dropout(
        0.5,
        name="Dropout6"
    )(x)

    x = tf.keras.layers.Dense(
        4096,
        activation="relu",
        name="FC7"
    )(x)

    x = tf.keras.layers.Dropout(
        0.5,
        name="Dropout7"
    )(x)

    # --------------------------------------------------------
    # Output
    # No softmax: output is logits
    # --------------------------------------------------------

    outputs = tf.keras.layers.Dense(
        num_classes,
        name="Output"
    )(x)

    # --------------------------------------------------------
    # Create Functional Model
    # --------------------------------------------------------

    return tf.keras.Model(
        inputs=inputs,
        outputs=outputs,
        name="VGG16"
    )


# ============================================================
# 10. TRAINING SETTINGS, LR SCHEDULE AND TIMING CALLBACK
# ============================================================
EPOCHS = 30
INITIAL_LR = 0.01
MOMENTUM = 0.9
WEIGHT_DECAY = 5e-4
def lr_schedule(epoch):
  """ Learning-rate schedule.
  Epochs 1-15: LR = 0.01
  Epochs 16-24: LR = 0.001
  Epochs 25-30: LR = 0.0001
  """
  if epoch < 15:
    return 0.01
  elif epoch < 24:
    return 0.001
  else:
    return 0.0001

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
    print( f"Epoch {epoch + 1} training time: " f"{elapsed:.2f} seconds" )



# ============================================================
# 11. TRAINING AND RESULT SAVING METHOD
# ============================================================
def train_and_save( model, architecture_name, dataset_name, train_ds, val_ds, num_classes, epochs=30 ):
  """
  Compile, train, and save a CNN model.
  The method:
    1. Creates the optimizer.
    2. Compiles the model.
    3. Creates callbacks.
    4. Trains the model.
    5. Records epoch training time.
    6. Saves the best model.
    7. Saves training history as CSV.
    8. Saves accuracy and loss figures.

  Parameters ----------
   model : tf.keras.Model CNN model to train.
   architecture_name : str Model name, e.g. "AlexNet".
   dataset_name : str Dataset name, e.g. "CIFAR_10".
   train_ds : tf.data.Dataset Training dataset.
   val_ds : tf.data.Dataset Validation dataset.
   num_classes : int Number of output classes.
   epochs : int Number of training epochs.

  Returns -------
    history : tf.keras.callbacks.History Keras training history.
    results_df : pandas.DataFrame Complete epoch-level results.
    timer : EpochTimer Epoch timing callback.
  """
  # --------------------------------------------------------
  # Create output directories
  # --------------------------------------------------------
  model_dir = os.path.join( BASE_DIR, dataset_name, architecture_name, "models" )
  results_dir = os.path.join( BASE_DIR, dataset_name, architecture_name, "results" )
  figures_dir = os.path.join( BASE_DIR, dataset_name, architecture_name, "figures" )
  os.makedirs(model_dir, exist_ok=True)
  os.makedirs(results_dir, exist_ok=True)
  os.makedirs(figures_dir, exist_ok=True)

  # --------------------------------------------------------
  # Optimizer
  # --------------------------------------------------------
  optimizer = tf.keras.optimizers.SGD( learning_rate=INITIAL_LR, momentum=MOMENTUM, weight_decay=WEIGHT_DECAY )

  # --------------------------------------------------------
  # Metrics
  # --------------------------------------------------------
  metrics = [ "accuracy" ]
  # Top-5 accuracy is required for CIFAR-100
  if num_classes == 100:
    metrics.append( tf.keras.metrics.SparseTopKCategoricalAccuracy( k=5, name="top5_accuracy" ) )


  # --------------------------------------------------------
  # Compile
  # --------------------------------------------------------
  model.compile( optimizer=optimizer, loss=tf.keras.losses.SparseCategoricalCrossentropy( from_logits=True ), metrics=metrics )

  # --------------------------------------------------------
  # Callbacks (Best model, learning rate, training time)
  # --------------------------------------------------------
  checkpoint_path = os.path.join( model_dir, f"{architecture_name}_{dataset_name}_best.keras" )
  checkpoint = tf.keras.callbacks.ModelCheckpoint( checkpoint_path, monitor="val_accuracy", save_best_only=True, mode="max", verbose=1 )
  lr_callback = tf.keras.callbacks.LearningRateScheduler( lr_schedule, verbose=1 )
  timer = EpochTimer()

  # --------------------------------------------------------
  # Training
  # --------------------------------------------------------
  history = model.fit( train_ds, epochs=epochs, validation_data=val_ds, callbacks=[ lr_callback, checkpoint, timer ] )

  # --------------------------------------------------------
  # Create complete results table
  # --------------------------------------------------------
  results = { "epoch": range(1, epochs + 1), "train_accuracy": history.history["accuracy"],
             "val_accuracy": history.history["val_accuracy"], "train_loss": history.history["loss"], "val_loss": history.history["val_loss"],
              "learning_rate": history.history["learning_rate"], "epoch_time_sec": timer.epoch_times }

  # Add CIFAR-100 top-5 training/validation results
  if num_classes == 100:
    results["train_top5_accuracy"] = ( history.history["top5_accuracy"] )
    results["val_top5_accuracy"] = ( history.history["val_top5_accuracy"] )

  results_df = pd.DataFrame(results)

  # --------------------------------------------------------
  # Save training history
  # --------------------------------------------------------
  history_path = os.path.join( results_dir, f"{architecture_name}_{dataset_name}_history.csv" )
  results_df.to_csv( history_path, index=False )

  # --------------------------------------------------------
  # Accuracy graph
  # --------------------------------------------------------
  plt.figure(figsize=(8, 5))
  plt.plot( results_df["epoch"], results_df["train_accuracy"], label="Training Accuracy" )
  plt.plot( results_df["epoch"], results_df["val_accuracy"], label="Validation Accuracy" )
  plt.xlabel("Epoch")
  plt.ylabel("Accuracy")
  plt.title( f"{architecture_name} - {dataset_name} Accuracy" )
  plt.legend()
  plt.grid(True)
  plt.tight_layout()

  accuracy_path = os.path.join( figures_dir, f"{architecture_name}_{dataset_name}_accuracy.png" )
  plt.savefig( accuracy_path, dpi=300, bbox_inches="tight" )
  plt.show()

  # --------------------------------------------------------
  # Loss graph
  # --------------------------------------------------------
  plt.figure(figsize=(8, 5))
  plt.plot( results_df["epoch"], results_df["train_loss"], label="Training Loss" )
  plt.plot( results_df["epoch"], results_df["val_loss"], label="Validation Loss" )
  plt.xlabel("Epoch")
  plt.ylabel("Loss")
  plt.title( f"{architecture_name} - {dataset_name} Loss" )
  plt.legend()
  plt.grid(True)
  plt.tight_layout()

  loss_path = os.path.join( figures_dir, f"{architecture_name}_{dataset_name}_loss.png" )
  plt.savefig( loss_path, dpi=300, bbox_inches="tight" )
  plt.show()

  # --------------------------------------------------------
  # Print training summary
  # --------------------------------------------------------
  best_epoch = ( results_df["val_accuracy"].idxmax() + 1 )
  best_val_accuracy = ( results_df["val_accuracy"].max() )
  average_epoch_time = ( results_df["epoch_time_sec"].mean() )
  total_training_time = ( results_df["epoch_time_sec"].sum() )
  print("\n" + "=" * 60)
  print("TRAINING SUMMARY")
  print("=" * 60)
  print(f"Architecture: {architecture_name}")
  print(f"Dataset: {dataset_name}")
  print(f"Epochs: {epochs}")
  print( f"Best epoch: {best_epoch}" )
  print( f"Best val acc: {best_val_accuracy:.4%}" )
  print( f"Average epoch time: " f"{average_epoch_time:.2f} sec" )
  print( f"Total training time: " f"{total_training_time:.2f} sec" )
  print( f"\nBest model saved to:\n" f"{checkpoint_path}" )
  print( f"\nTraining history saved to:\n" f"{history_path}" )


  return history, results_df, timer


# ============================================================
# 10. Evaluate Best Model and Save Test Results
# ============================================================

def evaluate_and_save(architecture_name, dataset_name, num_classes,test_ds):
    """
    Load the best saved model, evaluate it on the test set, and save the evaluation results.

    Returns:
        evaluation_results: Dictionary containing test metrics.
    """

    model_dir = os.path.join(
        BASE_DIR,
        dataset_name,
        architecture_name,
        "models"
    )

    results_dir = os.path.join(
        BASE_DIR,
        dataset_name,
        architecture_name,
        "results"
    )

    checkpoint_path = os.path.join(
        model_dir,
        f"{architecture_name}_{dataset_name}_best.keras"
    )

    print("\n" + "=" * 70)
    print(f"Evaluating {architecture_name} on {dataset_name}")
    print("=" * 70)

    # --------------------------------------------------------
    # Load the best model based on validation accuracy
    # --------------------------------------------------------

    best_model = tf.keras.models.load_model(
        checkpoint_path,
        custom_objects={"LRN": LRN}
    )

    # --------------------------------------------------------
    # Evaluate on the untouched test set
    # --------------------------------------------------------

    test_metrics = best_model.evaluate(
        test_ds,
        return_dict=True,
        verbose=1
    )

    test_loss = test_metrics["loss"]
    test_accuracy = test_metrics["accuracy"]

    # Accuracy drop
    accuracy_drop = 100.0 * (1.0 - test_accuracy)

    # --------------------------------------------------------
    # Store results
    # --------------------------------------------------------

    evaluation_results = {
        "architecture": architecture_name,
        "dataset": dataset_name,
        "test_loss": test_loss,
        "test_accuracy": test_accuracy * 100.0,
        "accuracy_drop": accuracy_drop,
        "num_parameters": best_model.count_params()
    }

    # Add Top-5 accuracy for CIFAR-100
    if num_classes == 100:
        test_top5 = test_metrics["top5_accuracy"]

        evaluation_results["test_top5_accuracy"] = (
            test_top5 * 100.0
        )

    # --------------------------------------------------------
    # Save evaluation results
    # --------------------------------------------------------

    evaluation_df = pd.DataFrame([evaluation_results])

    evaluation_path = os.path.join(
        results_dir,
        f"{architecture_name}_{dataset_name}_evaluation.csv"
    )

    evaluation_df.to_csv(
        evaluation_path,
        index=False
    )

    # --------------------------------------------------------
    # Print results
    # --------------------------------------------------------

    print("\nTest Results:")
    print(f"Test Loss       : {test_loss:.4f}")
    print(f"Test Top-1 Acc. : {test_accuracy * 100:.2f}%")
    print(f"Accuracy Drop   : {accuracy_drop:.2f}%")

    if num_classes == 100:
        print(
            f"Test Top-5 Acc. : "
            f"{test_metrics['top5_accuracy'] * 100:.2f}%"
        )

    print(f"Parameters      : {best_model.count_params():,}")

    print(f"\nEvaluation saved to:")
    print(evaluation_path)

    return evaluation_results


# ============================================================
# 11. Generic Experiment Runner
# ============================================================

def run_experiment(architecture_name, dataset_name, num_classes,
    train_ds, val_ds, test_ds, build_model):
    """
    Run one complete architecture-dataset experiment.

    Steps:
        1. Build model
        2. Print model summary
        3. Train model
        4. Save training history/results/figures
        5. Evaluate best model on test set
        6. Save test results

    Returns:
        experiment_results: Dictionary containing training
        and evaluation results.
    """

    print("\n")
    print("#" * 80)
    print(f"# {architecture_name} - {dataset_name}")
    print("#" * 80)

    # --------------------------------------------------------
    # 1. Build model
    # --------------------------------------------------------

    print("\nBuilding model...")

    model = build_model(
        num_classes=num_classes
    )

    # --------------------------------------------------------
    # 2. Print model summary
    # --------------------------------------------------------

    print("\nModel Summary:")
    model.summary()

    print(
        f"\nTotal parameters: "
        f"{model.count_params():,}"
    )

    # --------------------------------------------------------
    # 3. Train and save training results
    # --------------------------------------------------------

    history, training_results, timer = train_and_save(
        model=model,
        architecture_name=architecture_name,
        dataset_name=dataset_name,
        train_ds=train_ds,
        val_ds=val_ds,
        num_classes=num_classes,
        epochs=EPOCHS
    )

    # --------------------------------------------------------
    # 4. Evaluate best model and save test results
    # --------------------------------------------------------

    evaluation_results = evaluate_and_save(
        architecture_name=architecture_name,
        dataset_name=dataset_name,
        num_classes=num_classes,
        test_ds=test_ds
    )

    # --------------------------------------------------------
    # 5. Combine experiment information
    # --------------------------------------------------------

    experiment_results = {
        "architecture": architecture_name,
        "dataset": dataset_name,
        "num_parameters": model.count_params(),
        "best_val_accuracy": max(
            training_results["val_accuracy"]
        ) * 100.0,
        "best_epoch": (
            training_results["val_accuracy"].idxmax() + 1
        ),
        "test_accuracy": evaluation_results[
            "test_accuracy"
        ],
        "accuracy_drop": evaluation_results[
            "accuracy_drop"
        ],
        "total_training_time_sec": (
            training_results["epoch_time_sec"].sum()
        ),
        "average_epoch_time_sec": (
            training_results["epoch_time_sec"].mean()
        )
    }

    # Add Top-5 for CIFAR-100
    if num_classes == 100:
        experiment_results["test_top5_accuracy"] = (
            evaluation_results["test_top5_accuracy"]
        )

    print("\n" + "-" * 70)
    print(f"{architecture_name} / {dataset_name} completed.")
    print("-" * 70)

    return experiment_results


# ============================================================
# 12. Main Program
# ============================================================

def main():

    # --------------------------------------------------------
    # Load and prepare datasets
    # --------------------------------------------------------
    """
    datasets = load_datasets()

    cifar10_train_ds = datasets["CIFAR_10"]["train"]
    cifar10_val_ds   = datasets["CIFAR_10"]["val"]
    cifar10_test_ds  = datasets["CIFAR_10"]["test"]

    cifar100_train_ds = datasets["CIFAR_100"]["train"]
    cifar100_val_ds   = datasets["CIFAR_100"]["val"]
    cifar100_test_ds  = datasets["CIFAR_100"]["test"]
    """
    # --------------------------------------------------------
    # Define architectures
    # --------------------------------------------------------

    architectures = {
        "LeNet": build_lenet,
        "AlexNet": build_alexnet,
        "VGG16": build_vgg16
    }

    # --------------------------------------------------------
    # Define datasets
    # --------------------------------------------------------

    dataset_configs = {

        "CIFAR_10": {
            "num_classes": 10,
            "train_ds": cifar10_train_ds,
            "val_ds": cifar10_val_ds,
            "test_ds": cifar10_test_ds
        },

        "CIFAR_100": {
            "num_classes": 100,
            "train_ds": cifar100_train_ds,
            "val_ds": cifar100_val_ds,
            "test_ds": cifar100_test_ds
        }
    }

    # --------------------------------------------------------
    # Run all six experiments
    # --------------------------------------------------------

    all_results = []

    for dataset_name, dataset_config in dataset_configs.items():

        for architecture_name, build_model in architectures.items():

            result = run_experiment(
                architecture_name=architecture_name,
                dataset_name=dataset_name,
                num_classes=dataset_config["num_classes"],
                train_ds=dataset_config["train_ds"],
                val_ds=dataset_config["val_ds"],
                test_ds=dataset_config["test_ds"],
                build_model=build_model
            )

            all_results.append(result)

    # --------------------------------------------------------
    # Create overall comparison table
    # --------------------------------------------------------

    comparison_df = pd.DataFrame(all_results)

    comparison_path = os.path.join(
        BASE_DIR,
        "comparison_results.csv"
    )

    comparison_df.to_csv(
        comparison_path,
        index=False
    )

    print("\n")
    print("=" * 80)
    print("ALL EXPERIMENTS COMPLETED")
    print("=" * 80)

    print("\nComparison Results:")
    print(comparison_df.to_string(index=False))

    print(
        f"\nComparison table saved to:\n"
        f"{comparison_path}"
    )


if __name__ == "__main__":
    main()


create_project_directories()
