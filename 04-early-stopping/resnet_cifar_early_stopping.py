import os
import numpy as np
import datetime

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.callbacks import EarlyStopping

import resnet


NUM_GPUS = 1
BS_PER_GPU = 128

HEIGHT = 32
WIDTH = 32
NUM_CHANNELS = 3
NUM_CLASSES = 10
NUM_TRAIN_SAMPLES = 50000

BASE_LEARNING_RATE = 0.1
LR_SCHEDULE = [(0.1, 10), (0.01, 20)]

NUM_EPOCHS = 10


def normalize(x, y):
  x = tf.image.per_image_standardization(x)
  return x, y


def augmentation(x, y):
    x = tf.image.resize_with_crop_or_pad(
        x, HEIGHT + 8, WIDTH + 8)
    x = tf.image.random_crop(x, [HEIGHT, WIDTH, NUM_CHANNELS])
    x = tf.image.random_flip_left_right(x)
    return x, y 


def schedule(epoch):
  initial_learning_rate = BASE_LEARNING_RATE * BS_PER_GPU / 128
  learning_rate = initial_learning_rate
  for mult, start_epoch in LR_SCHEDULE:
    if epoch >= start_epoch:
      learning_rate = initial_learning_rate * mult
    else:
      break
  tf.summary.scalar('learning rate', data=learning_rate, step=epoch)
  return learning_rate


(x,y), (x_test, y_test) = keras.datasets.cifar10.load_data()

train_dataset = tf.data.Dataset.from_tensor_slices((x,y))
test_dataset = tf.data.Dataset.from_tensor_slices((x_test, y_test))

tf.random.set_seed(22)
train_dataset = train_dataset.shuffle(NUM_TRAIN_SAMPLES).map(augmentation).map(normalize).batch(BS_PER_GPU * NUM_GPUS, drop_remainder=True)
test_dataset = test_dataset.map(normalize).batch(BS_PER_GPU * NUM_GPUS, drop_remainder=True)


input_shape = (HEIGHT, WIDTH, NUM_CHANNELS)
img_input = tf.keras.layers.Input(shape=input_shape)

model = resnet.resnet56(img_input=img_input, classes=NUM_CLASSES)

# define optimizer
sgd = tf.keras.optimizers.SGD(lr=0.1)
model.compile(optimizer=sgd, loss='sparse_categorical_crossentropy', metrics=['accuracy'])

earlystop_callback = EarlyStopping(
  monitor='val_accuracy', min_delta=0.0001,
  patience=1, verbose=1, mode='auto')

model.fit(train_dataset,
          epochs=NUM_EPOCHS, callbacks=[earlystop_callback],
          validation_data=test_dataset,
          validation_freq=1)

model.evaluate(test_dataset)