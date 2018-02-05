import numpy as np
import tensorflow as tf

from models.unet.model import Model, UNetTrainConfig
#from models.pspnet.model import Model, PSPNetTrainConfig
from common import create_folder, load_train_images, train_val_split, shuffle_dataset

# create checkpoint folder
create_folder(Model.CHECKPOINT_DIR)

TRAIN_PATH = './data/stage1_train/'
#TRAIN_PATH = './data/stage1_train_small/'

# load training data
print("Getting and resizing train images and masks ... ")
X_train, Y_train, sizes_train, _ = load_train_images(TRAIN_PATH, 
   Model.IMG_HEIGHT, Model.IMG_WIDTH, preprocessing=['Lab'], augmentation={'elastic_rnd': 5})
print("Done loading images!")

# split training data for training and validation
X_train, Y_train, X_val, Y_val = train_val_split(X_train, Y_train, 0.2)

# random shuffle training dataset
X_train, Y_train = shuffle_dataset(X_train, Y_train)

# initialize model
print("Initializing model ...")
model = Model()

print("Beginning training ... ")
model.train(X_train, Y_train, UNetTrainConfig(display_rate = 10), X_val, Y_val)
#model.train(X_train, Y_train, PSPNetTrainConfig(display_rate = 10), X_val, Y_val)
print("Done training!")