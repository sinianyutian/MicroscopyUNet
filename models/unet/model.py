import numpy as np
import tensorflow as tf

import math

from tqdm import tqdm
from skimage import io
from skimage.transform import resize
from skimage.morphology import label

from common import IoU, mIoU, SEGMENTATION_THRESHOLD
from data_provider import TestDataProvider

class UNetTrainConfig():
    def __init__(self, **kwargs):
        if 'num_epochs' in kwargs:
            self.num_epochs = kwargs['num_epochs']
        else:
            self.num_epochs = 100

        if 'val_rate' in kwargs:
            self.val_rate = kwargs['val_rate']
        else:
            self.val_rate = 0

        if 'starter_learning_rate' in kwargs:
            self.starter_learning_rate = kwargs['starter_learning_rate']
        else:
            self.starter_learning_rate = 0.01

class Model():
    # this is where checkpoints from this model will be saved
    CHECKPOINT_DIR = "./checkpoints/unet"

    IMG_WIDTH = 300
    IMG_HEIGHT = 300
    IMG_CHANNELS = 1 # we try with only gray or L value
    #IMG_CHANNELS = 3

    #NUM_CLASSES = 2
    NUM_CLASSES = 1

    def __init__(self, num_scales = 1, alpha=0.3):
        '''
        alpha signifies the weight given to the inner mask loss
        compared to the edge mask loss'''
        #self.sess = tf.Session()
        #tf.keras.backend.set_session(self.sess)

        #vgg16 = tf.keras.applications.VGG16(include_top=False, 
        #    input_shape=(Model.IMG_WIDTH,Model.IMG_HEIGHT,Model.IMG_CHANNELS))

        self.X = tf.placeholder(tf.float32, [None, Model.IMG_WIDTH, Model.IMG_HEIGHT, Model.IMG_CHANNELS], name='input')
        self.Y_ = tf.placeholder(tf.float32, [None, Model.IMG_WIDTH, Model.IMG_HEIGHT, Model.NUM_CLASSES], name='ground_truth')

        self.global_step = tf.Variable(0, trainable=False, dtype=tf.int32)
        self.increment_global_step_op = tf.assign_add(self.global_step, 1)
        self.starter_learning_rate = tf.placeholder(tf.float32, name='starter_learning_rate')
        self.learning_rate = tf.train.exponential_decay(self.starter_learning_rate, 
            self.global_step, 5, 0.1)

        # build the scales and append them to list
        scales = [self.X]
        for i in range(1, num_scales):
            scales.append(tf.image.resize_bilinear(scales[i-1], [scales[i-1].shape[1] // 2, scales[i-1].shape[2] // 2])) 

        scales_out = []
        for i, scale in enumerate(scales):
            with tf.name_scope('scale_{0}'.format(i)):
                skip_4, skip_3, skip_2, skip_1 = self._build_encoder(scale)
                scales_out.append(self._build_decoder(skip_4, skip_3, skip_2, skip_1))

        # upsample all scales to original scale
        for i in range(1, len(scales_out)):
            scales_out[i] = tf.image.resize_bilinear(scales_out[i], [scales_out[0].shape[1], scales_out[0].shape[2]])

        scale_cat = tf.concat(scales_out, axis=3)

        # fully connected layers for final
        logits = tf.layers.conv2d(scale_cat, 32, [1, 1], padding='same')
        logits = tf.layers.conv2d(logits, Model.NUM_CLASSES, [1, 1], padding='same')
        self.Y_p = tf.nn.sigmoid(logits)

        self.loss = tf.losses.sigmoid_cross_entropy(self.Y_, logits)

        self.tb_train_loss = tf.summary.scalar('training_loss', self.loss)

        self.optimizer = tf.train.AdamOptimizer(self.learning_rate).minimize(self.loss)
        self.initializers = [tf.global_variables_initializer(), tf.local_variables_initializer()]
        self.saver = tf.train.Saver(max_to_keep=100)

    def _build_encoder(self, X):
        with tf.name_scope('encoder'):
            conv1 = tf.layers.conv2d(X, 32, [3, 3], activation=tf.nn.relu, padding='same',
                kernel_initializer=tf.contrib.layers.xavier_initializer())
            print("conv1 shape: {0}".format(conv1.shape))
            pool1 = tf.layers.max_pooling2d(conv1, [2, 2], [2, 2])
            print("pool1 shape: {0}".format(pool1.shape))

            conv2 = tf.layers.conv2d(pool1, 64, [3, 3], activation=tf.nn.relu, padding='same',
                kernel_initializer=tf.contrib.layers.xavier_initializer())
            print("conv2 shape: {0}".format(conv2.shape))
            pool2 = tf.layers.max_pooling2d(conv2, [2, 2], [2, 2])
            print("pool2 shape: {0}".format(pool2.shape))

            conv3 = tf.layers.conv2d(pool2, 128, [3, 3], activation=tf.nn.relu, padding='same',
                kernel_initializer=tf.contrib.layers.xavier_initializer())
            print("conv3 shape: {0}".format(conv3.shape))
            pool3 = tf.layers.max_pooling2d(conv3, [2, 2], [2, 2])
            print("pool3 shape: {0}".format(pool3.shape))

            conv4 = tf.layers.conv2d(pool3, 512, [1, 1], activation=tf.nn.relu, padding='same',
                kernel_initializer=tf.contrib.layers.xavier_initializer())
            print("conv4 shape: {0}".format(conv3.shape))
            drop4 = tf.layers.dropout(conv4, rate=0.5)






            # conv1 = tf.layers.conv2d(X, 64, [3, 3], activation=tf.nn.relu, padding='same',
            #     kernel_initializer=tf.contrib.layers.xavier_initializer())
            # print("conv1 shape: {0}".format(conv1.shape))
            # conv1 = tf.layers.conv2d(conv1, 64, [3, 3], activation=tf.nn.relu, padding='same',
            #     kernel_initializer=tf.contrib.layers.xavier_initializer())
            # print("conv1 shape: {0}".format(conv1.shape))
            # pool1 = tf.layers.max_pooling2d(conv1, [2, 2], [2, 2])
            # print("pool1 shape: {0}".format(pool1.shape))

            # conv2 = tf.layers.conv2d(pool1, 128, [3, 3], activation=tf.nn.relu, padding='same',
            #     kernel_initializer=tf.contrib.layers.xavier_initializer())
            # print("conv2 shape: {0}".format(conv2.shape))
            # conv2 = tf.layers.conv2d(conv2, 128, [3, 3], activation=tf.nn.relu, padding='same',
            #     kernel_initializer=tf.contrib.layers.xavier_initializer())
            # print("conv2 shape: {0}".format(conv2.shape))
            # pool2 = tf.layers.max_pooling2d(conv2, [2, 2], [2, 2])
            # print("pool2 shape: {0}".format(pool2.shape))

            # conv3 = tf.layers.conv2d(pool2, 256, [3, 3], activation=tf.nn.relu, padding='same',
            #     kernel_initializer=tf.contrib.layers.xavier_initializer())
            # print("conv3 shape: {0}".format(conv3.shape))
            # conv3 = tf.layers.conv2d(conv3, 256, [3, 3], activation=tf.nn.relu, padding='same',
            #     kernel_initializer=tf.contrib.layers.xavier_initializer())
            # print("conv3 shape: {0}".format(conv3.shape))
            # pool3 = tf.layers.max_pooling2d(conv3, [2, 2], [2, 2])
            # print("pool3 shape: {0}".format(pool3.shape))

            # conv4 = tf.layers.conv2d(pool3, 512, [3, 3], activation=tf.nn.relu, padding='same',
            #     kernel_initializer=tf.contrib.layers.xavier_initializer())
            # print("conv4 shape: {0}".format(conv4.shape))
            # conv4 = tf.layers.conv2d(conv4, 512, [3, 3], activation=tf.nn.relu, padding='same',
            #     kernel_initializer=tf.contrib.layers.xavier_initializer())
            # print("conv4 shape: {0}".format(conv4.shape))
            # drop4 = tf.layers.dropout(conv4, rate=0.5)
            # pool4 = tf.layers.max_pooling2d(drop4, [2, 2], [2, 2])
            # print("pool4 shape: {0}".format(pool4.shape))

            # conv5 = tf.layers.conv2d(pool4, 1024, [3, 3], activation=tf.nn.relu, padding='same',
            #     kernel_initializer=tf.contrib.layers.xavier_initializer())
            # print("conv5 shape: {0}".format(conv5.shape))
            # conv5 = tf.layers.conv2d(conv5, 1024, [3, 3], activation=tf.nn.relu, padding='same',
            #     kernel_initializer=tf.contrib.layers.xavier_initializer())
            # print("conv5 shape: {0}".format(conv5.shape))
            # drop5 = tf.layers.dropout(conv5, rate=0.5)

        return drop4, conv3, conv2, conv1

    def _build_decoder(self, skip_4, skip_3, skip_2, skip_1):
        up3 = tf.image.resize_bilinear(skip_4, [skip_4.shape[1] * 2, skip_4.shape[2] * 2])
        up3 = tf.layers.conv2d(up3, 128, [3, 3], padding='same', activation=tf.nn.relu)
        merge3 = tf.concat([skip_3, up3], 3)

        up2 = tf.image.resize_bilinear(merge3, [merge3.shape[1] * 2, merge3.shape[2] * 2])
        up2 = tf.layers.conv2d(up2, 64, [3, 3], padding='same')
        merge2 = tf.concat([skip_2, up2], 3)

        up1 = tf.image.resize_bilinear(merge2, [merge2.shape[1] * 2, merge2.shape[2] * 2])
        up1 = tf.layers.conv2d(up1, 32, [3, 3], padding='same')
        merge1 = tf.concat([skip_1, up1], 3)

        conv1 = tf.layers.conv2d(merge1, 32, [3, 3], padding='same')
        
        
        
        # up6 = tf.image.resize_nearest_neighbor(skip_5, [skip_5.shape[1] * 2, skip_5.shape[2] * 2])
        # up6 = tf.layers.conv2d(up6, 512, [3, 3], activation=tf.nn.relu, padding='same',
        #     kernel_initializer=tf.contrib.layers.xavier_initializer())
        # merge6 = tf.concat([skip_4, up6], 3)
        # conv6 = tf.layers.conv2d(merge6, 512, [3, 3], activation=tf.nn.relu, padding='same',
        #     kernel_initializer=tf.contrib.layers.xavier_initializer())
        # conv6 = tf.layers.conv2d(conv6, 512, [3, 3], activation=tf.nn.relu, padding='same',
        #     kernel_initializer=tf.contrib.layers.xavier_initializer())


        # up7 = tf.image.resize_nearest_neighbor(conv6, [conv6.shape[1] * 2, conv6.shape[2] * 2])
        # up7 = tf.layers.conv2d(up7, 256, [3, 3], activation=tf.nn.relu, padding='same',
        #     kernel_initializer=tf.contrib.layers.xavier_initializer())
        # merge7 = tf.concat([skip_3, up7], 3)
        # conv7 = tf.layers.conv2d(merge7, 256, [3, 3], activation=tf.nn.relu, padding='same',
        #     kernel_initializer=tf.contrib.layers.xavier_initializer())
        # conv7 = tf.layers.conv2d(conv7, 256, [3, 3], activation=tf.nn.relu, padding='same',
        #     kernel_initializer=tf.contrib.layers.xavier_initializer())


        # up8 = tf.image.resize_nearest_neighbor(conv7, [conv7.shape[1] * 2, conv7.shape[2] * 2])
        # up8 = tf.layers.conv2d(up8, 128, [3, 3], activation=tf.nn.relu, padding='same',
        #     kernel_initializer=tf.contrib.layers.xavier_initializer())
        # merge8 = tf.concat([skip_2, up8], 3)
        # conv8 = tf.layers.conv2d(merge8, 128, [3, 3], activation=tf.nn.relu, padding='same',
        #     kernel_initializer=tf.contrib.layers.xavier_initializer())
        # conv8 = tf.layers.conv2d(conv8, 128, [3, 3], activation=tf.nn.relu, padding='same',
        #     kernel_initializer=tf.contrib.layers.xavier_initializer())


        # up9 = tf.image.resize_nearest_neighbor(conv8, [conv8.shape[1] * 2, conv8.shape[2] * 2])
        # up9 = tf.layers.conv2d(up9, 64, [3, 3], activation=tf.nn.relu, padding='same',
        #     kernel_initializer=tf.contrib.layers.xavier_initializer())
        # merge9 = tf.concat([skip_1, up9], 3)
        # conv9 = tf.layers.conv2d(merge9, 64, [3, 3], activation=tf.nn.relu, padding='same',
        #     kernel_initializer=tf.contrib.layers.xavier_initializer())
        # conv9 = tf.layers.conv2d(conv9, 64, [3, 3], activation=tf.nn.relu, padding='same',
        #     kernel_initializer=tf.contrib.layers.xavier_initializer())
        # conv9 = tf.layers.conv2d(conv9, 64, [3, 3], activation=tf.nn.relu, padding='same',
        #     kernel_initializer=tf.contrib.layers.xavier_initializer())

        return conv1

    def train(self, config, data_provider_train, restore=False, data_provider_val=None):
        has_validation = data_provider_val is not None
        num_batches_train = data_provider_train.num_batches()
        num_batches_val = data_provider_val.num_batches()

        with tf.Session() as sess:
            if restore == True:
                checkpoint_path = tf.train.latest_checkpoint(Model.CHECKPOINT_DIR)
                self.saver.restore(sess, checkpoint_path)
            else:
                sess.run(self.initializers)

            train_writer = tf.summary.FileWriter(".tensorboard/unet", sess.graph)

            for i in range(0, config.num_epochs):
                for j, batch in tqdm(enumerate(data_provider_train), total=num_batches_train):
                    feed_dict = {self.X: batch[0], self.Y_: batch[1], 
                        self.starter_learning_rate: config.starter_learning_rate}
                    summary,loss_value,_ = sess.run([self.tb_train_loss, self.loss, self.optimizer], 
                        feed_dict=feed_dict)
                    print("Loss: {0}".format(loss_value))
                    
                    train_writer.add_summary(summary, num_batches_train*i + j)

                if (config.val_rate != 0) and (i % config.val_rate == 0) and (has_validation == True):
                    Y_p_vals = []
                    loss_vals = np.zeros(num_batches_val, dtype=np.float32)

                    for j, batch in enumerate(data_provider_val):
                        feed_dict = {self.X: batch[0], self.Y_: batch[1]}
                        loss_vals[j], Y_p_ = sess.run([self.loss, self.Y_p], feed_dict=feed_dict)
                        Y_p_vals.append(Y_p_)

                    # calculate mIoU for predicted segmentation labels
                    Y_p_vals = np.concatenate(Y_p_vals)
                    Y_p_vals = Y_p_vals > SEGMENTATION_THRESHOLD
                    true_Y = data_provider_val.get_true_Y()
                    mIoU_value = mIoU(true_Y, Y_p_vals)
                    loss_value = np.mean(loss_vals)

                    # tensorboard
                    summary = tf.Summary()
                    summary.value.add(tag='validation_loss', simple_value=loss_value)
                    summary.value.add(tag='validation_IoU', simple_value=mIoU_value)
                    train_writer.add_summary(summary, i)
                    train_writer.flush()
                    print("Epoch {0}: Validation loss: {1}, Mean IoU: {2}".format(i, loss_value, mIoU_value))

                    data_provider_val.reset()

                # save model checkpoint each epoch
                self.saver.save(sess, Model.CHECKPOINT_DIR + "/unet", global_step=i)
                data_provider_train.reset()

                # increment global step
                sess.run(self.increment_global_step_op)

    def test(self, data_provider):
        is_labeled_data = not isinstance(data_provider, TestDataProvider)
        num_batches = data_provider.num_batches()

        Y_p_vals = []
        loss_vals = np.zeros(num_batches, dtype=np.float32)
        loss_value = None

        with tf.Session() as sess:
            checkpoint_path = tf.train.latest_checkpoint(Model.CHECKPOINT_DIR)
            self.saver.restore(sess, checkpoint_path)

            for j, batch in tqdm(enumerate(data_provider), total=num_batches):
                if not is_labeled_data:
                    feed_dict = {self.X: batch}
                    Y_p_ = sess.run(self.Y_p, feed_dict=feed_dict)
                    Y_p_vals.append(Y_p_)
                    loss_vals[j] = None

                else:
                    feed_dict = {self.X: batch[0], self.Y_: batch[1]}
                    loss_vals[j], Y_p_ = sess.run([self.loss, self.Y_p], feed_dict=feed_dict)
                    Y_p_vals.append(Y_p_)

            if is_labeled_data:
               loss_value = np.mean(loss_vals)

        return loss_value, Y_p_vals