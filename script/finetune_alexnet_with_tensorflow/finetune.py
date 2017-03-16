#encoding=utf-8
"""
With this script you can finetune AlexNet as provided in the alexnet.py
class on any given dataset. 
Specify the configuration settings at the beginning according to your 
problem.
This script was written for TensorFlow 1.0 and come with a blog post 
you can find here:
  
https://kratzert.github.io/2017/02/24/finetuning-alexnet-with-tensorflow.html

Author: Frederik Kratzert 
contact: f.kratzert(at)gmail.com
"""
import os
import time
import numpy as np
import tensorflow as tf
from datetime import datetime
from alexnet import AlexNet
from datagenerator import ImageDataGenerator
import argparse
"""
Configuration settings
"""

parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('-tf','--train_file',action='store',type=str,
		default='../../data/dogvscat/train.txt',help='train file')
parser.add_argument('-vf','--val_file',action='store',type=str,
		default='../../data/dogvscat/val.txt',help='validation file')
parser.add_argument('-lr','--learning_rate',action='store',type=float,
		default=0.01,help='learning_rate file')
parser.add_argument('-ne','--num_epochs',action='store',type=int,
		default=10,help='num_epochs')
parser.add_argument('-bs','--batch_size',action='store',type=int,
		default=128,help='batch size')
parser.add_argument('-dr','--dropout_rate',action='store',type=float,
		default=0.5,help='dropout rate')
parser.add_argument('-nc','--num_classes',action='store',type=int,
		default=2,help='num classes')
parser.add_argument('-tl','--train_layers',nargs='+',action='store',type=str,
		default=['fc8','fc7'],help='dropout rate')
parser.add_argument('-ds','--display_step',action='store',type=int,
		default=1,help='display_step')
parser.add_argument('-fp','--filewriter_path',action='store',type=str,
		default='../../data/filewriter',help='filewriter_path')
parser.add_argument('-cp','--checkpoint_path',action='store',type=str,
		default='../../data/checkpoint',help='checkpoint_path')
parser.add_argument('-tn','--top_N',action='store',type=int,
		default=5,help='whether the targets are in the top K predictions.')

args = parser.parse_args()
print("="*50)
print("[INFO] args:\r")
print(args)
print("="*50)

# Path to the textfiles for the trainings and validation set
train_file = args.train_file
val_file = args.val_file

# Learning params
learning_rate = args.learning_rate
num_epochs = args.num_epochs
batch_size = args.batch_size

# Network params
dropout_rate = args.dropout_rate
num_classes = args.num_classes
#train_layers = ['fc8', 'fc7']
train_layers = args.train_layers

# How often we want to write the tf.summary data to disk
display_step = args.display_step

# Path for tf.summary.FileWriter and to store model checkpoints
filewriter_path = args.filewriter_path
checkpoint_path = args.checkpoint_path

#whether the targets are in the top K predictions.
top_N = args.top_N


# argpars finished ==================================================

# Create parent path if it doesn't exist
if not os.path.isdir(checkpoint_path): os.mkdir(checkpoint_path)

# TF placeholder for graph input and output
x = tf.placeholder(tf.float32, [batch_size, 227, 227, 3])
y = tf.placeholder(tf.float32, [None, num_classes])
keep_prob = tf.placeholder(tf.float32)

# Initialize model
model = AlexNet(x, keep_prob, num_classes, train_layers)

# Link variable to model output
score = model.fc8

# List of trainable variables of the layers we want to train
var_list = [
    v for v in tf.trainable_variables() if v.name.split('/')[0] in train_layers
]  #获取参数只要需要训练的参数

# Op for calculating the loss
with tf.name_scope("cross_ent"):
    loss = tf.reduce_mean(
        tf.nn.softmax_cross_entropy_with_logits(logits=score, labels=y))

# Train op
with tf.name_scope("train"):
    # Get gradients of all trainable variables
    gradients = tf.gradients(loss, var_list)  #导数
    gradients = list(zip(gradients, var_list))

    # Create optimizer and apply gradient descent to the trainable variables
    optimizer = tf.train.GradientDescentOptimizer(learning_rate)
    train_op = optimizer.apply_gradients(grads_and_vars=gradients)

# Add gradients to summary  
for gradient, var in gradients:
    tf.summary.histogram(var.name + '/gradient', gradient)

# Add the variables we train to the summary  
for var in var_list:
    tf.summary.histogram(var.name, var)

# Add the loss to summary
tf.summary.scalar('cross_entropy', loss)

# Evaluation op: Accuracy of the model
with tf.name_scope("accuracy"):
    # top 1 accuracy
    # correct_pred = tf.equal(tf.argmax(score, 1), tf.argmax(y, 1))
    # accuracy = tf.reduce_mean(tf.cast(correct_pred, tf.float32))

    # TODO top k accuracy
    labels = tf.argmax(y, 1) # get real label
    topFiver = tf.nn.in_top_k(score, labels, top_N) # check if top N is in real label or not
    accuracy = tf.reduce_mean(tf.cast(topFiver, tf.float32))

# Add the accuracy to the summary
tf.summary.scalar('accuracy', accuracy)

# Merge all summaries together
merged_summary = tf.summary.merge_all()

# Initialize the FileWriter
writer = tf.summary.FileWriter(filewriter_path)

# Initialize an saver for store model checkpoints
saver = tf.train.Saver()

# Initalize the data generator seperately for the training and validation set
train_generator = ImageDataGenerator(
    train_file, horizontal_flip=True, shuffle=True)
val_generator = ImageDataGenerator(val_file, shuffle=False)

# Get the number of training/validation steps per epoch
train_batches_per_epoch = np.floor(train_generator.data_size /
                                   batch_size).astype(np.int16)
val_batches_per_epoch = np.floor(val_generator.data_size /
                                 batch_size).astype(np.int16)

# Start Tensorflow session
with tf.Session() as sess:

    # Initialize all variables
    sess.run(tf.global_variables_initializer())

    # Add the model graph to TensorBoard
    writer.add_graph(sess.graph)

    # Load the pretrained weights into the non-trainable layer
    model.load_initial_weights(sess)

    print("{} Start training...".format(datetime.now()))
    print("{} Open Tensorboard at --logdir {}".format(datetime.now(),
                                                      filewriter_path))

    # Loop over number of epochs
    for epoch in range(num_epochs):

        print("{} Epoch number: {}".format(datetime.now(), epoch + 1))

        step = 1

        while step < train_batches_per_epoch:

            start_time = time.time()
            # Get a batch of images and labels
            batch_xs, batch_ys = train_generator.next_batch(batch_size)

            # And run the training op
            sess.run(
                train_op,
                feed_dict={x: batch_xs,
                           y: batch_ys,
                           keep_prob: dropout_rate})
            duration = time.time() - start_time

            # Generate summary with the current batch of data and write to file
            if step % display_step == 0:
                s = sess.run(
                    merged_summary,
                    feed_dict={x: batch_xs,
                               y: batch_ys,
                               keep_prob: 1.})
                writer.add_summary(s, epoch * train_batches_per_epoch + step)
            # print
            if step % 10 == 0:
                print("[INFO] {} pics has trained. time using {}".format(step*batch_size,duration))

            step += 1

        # Validate the model on the entire validation set
        print("{} Start validation".format(datetime.now()))
        test_acc = 0.
        test_count = 0
        for _ in range(val_batches_per_epoch):
            batch_tx, batch_ty = val_generator.next_batch(batch_size)
            acc = sess.run(
                accuracy, feed_dict={x: batch_tx,
                                     y: batch_ty,
                                     keep_prob: 1.})
            test_acc += acc
            test_count += 1
        test_acc /= test_count
        print("Validation Accuracy = {} {}".format(datetime.now(), test_acc))

        # Reset the file pointer of the image data generator
        val_generator.reset_pointer()
        train_generator.reset_pointer()

        print("{} Saving checkpoint of model...".format(datetime.now()))

        #save checkpoint of the model
        checkpoint_name = os.path.join(
            checkpoint_path, 'model_epoch' + str(epoch + 1) + '.ckpt')
        save_path = saver.save(sess, checkpoint_name)

        print("{} Model checkpoint saved at {}".format(datetime.now(),
                                                       checkpoint_name))
