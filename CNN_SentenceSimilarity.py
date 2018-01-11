#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2017/11/30 11:19
# @Author  : Junru_Lu
# @Site    : 
# @File    : CNN_SentenceSimilarity.py
# @Software: PyCharm


import jieba
import tensorflow as tf
import numpy as np
import math
from sklearn.cross_validation import train_test_split
from gensim.models import keyedvectors
import sys
reload(sys)
sys.setdefaultencoding('utf-8')


stopwords = set(list(open('ChineseSTS-master/stopwords.txt', 'r').read().strip().split('\n')))  # 停用词表
word_vectors = keyedvectors.KeyedVectors.load('Word Embedding/Word60.model')  # 加载预先训练好的词向量
MAX_LENTH = 40
CLASS_TYPE = 2
GRAM = 4


def sen_vector_gen(title_words):  # 生成句子的词向量
    sen_vector = np.zeros(60, dtype=float)
    for word in title_words:
        try:
            sen_vector += word_vectors[word]
        except:
            pass
    sen_vector = sen_vector / len(title_words)  # 用词的词向量的平均值来表示句子向量
    return [sen_vector]


def get_vec_cosine(vec1, vec2):
    tmp = np.vdot(vec1, vec1) * np.vdot(vec2, vec2)
    if tmp == 0.0:
        return 0.0
    return np.vdot(vec1, vec2) / math.sqrt(tmp)


def cut_sentence_trigram(s):
    gram = GRAM
    s_trigram = []
    i = 0
    while i < len(s)-3 * (gram - 1):
        s_trigram.append(s[i:i+gram * 3])
        i += gram
    return s_trigram


def s1_s2_simipics(s1, s2, max_lenth):
    s1_trigram = cut_sentence_trigram(s1)
    s2_trigram = cut_sentence_trigram(s2)
    k = 0
    simi = []
    while k < max_lenth:
        j = 0
        while j < max_lenth:
            try:
                simi_pic = get_vec_cosine(sen_vector_gen([e for e in jieba.lcut(s1_trigram[k]) if e not in stopwords]),
                                          sen_vector_gen([e for e in jieba.lcut(s2_trigram[k]) if e not in stopwords]))
            except:
                simi_pic = 0.0
            simi.append(simi_pic)
            j += 1
        k += 1
    return simi


def weight_variable(shape):  # 定义初始权重
    # 形状为shape的随机变量
    initial = tf.truncated_normal(shape, stddev=0.1)
    return tf.Variable(initial)


def bias_variable(shape):
    initial = tf.constant(0.1, shape=shape)
    return tf.Variable(initial)


def conv2d(x, W):
    # stride[1,x_movement,y_movement,1]
    # padding=same:不够的地方补0；padding=valid:会缩小
    # 2维卷积层,卷积步长为(x=1,y=1)
    return tf.nn.conv2d(x, W, strides=[1, 1, 1, 1], padding='SAME')


def max_pool_2x2(x):
    # maxpooling
    # ksize表示核函数大小
    return tf.nn.max_pool(x, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='SAME')


def compute_accuracy(v_xs, v_ys):
    global prediction
    y_pre = sess.run(prediction, feed_dict={xs: v_xs, keep_prob: 1})
    # 预测的向量中1的位置和标签中1的位置是否一致
    correct_prediction = tf.equal(tf.argmax(y_pre, 1), tf.argmax(v_ys, 1))
    accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))
    result = sess.run(accuracy, feed_dict={xs: v_xs, ys: v_ys, keep_prob: 1})
    return result

# 放置在'Inputs'层中
with tf.name_scope('inputs'):
    keep_prob = tf.placeholder(tf.float32)
    # None表示无论多少行例子都可以;16 = 4 * 4
    xs = tf.placeholder(tf.float32, [None, MAX_LENTH**2], name='x_input')
    ys = tf.placeholder(tf.float32, [None, CLASS_TYPE], name='y_input')
    # -1表示图片个数,1表示Channel个数
    x_image = tf.reshape(xs, [-1, MAX_LENTH, MAX_LENTH, 1])

# 第一层卷积+pooling
# 核函数大小patch=2*2;通道数，即特征数为1所以in_size=1;新特征的厚度为out_size=4
W_conv1 = weight_variable([5, 5, 1, MAX_LENTH/4])
b_conv1 = bias_variable([MAX_LENTH/4])
h_conv1 = tf.nn.relu(conv2d(x_image, W_conv1) + b_conv1)
h_pool1 = max_pool_2x2(h_conv1)

# 第二层卷积+pooling
# 核函数大小patch=2*2;in_size=4;新特征的厚度为out_size=8
W_conv2 = weight_variable([5, 5, MAX_LENTH/4, MAX_LENTH/2])
b_conv2 = bias_variable([MAX_LENTH/2])
h_conv2 = tf.nn.relu(conv2d(h_pool1, W_conv2)+b_conv2)
h_pool2 = max_pool_2x2(h_conv2)

# 第一层全连接层func1 layer
W_fc1 = weight_variable([(MAX_LENTH/4)*(MAX_LENTH/4)*(MAX_LENTH/2), MAX_LENTH])
b_fc1 = bias_variable([MAX_LENTH])
h_pool2_flat = tf.reshape(h_pool2, [-1, (MAX_LENTH/4)*(MAX_LENTH/4)*(MAX_LENTH/2)])
h_fc1 = tf.nn.relu(tf.matmul(h_pool2_flat, W_fc1)+b_fc1)
h_fc1_drop = tf.nn.dropout(h_fc1, keep_prob)

# 第二层全连接层func2 layer
W_fc2 = weight_variable([MAX_LENTH, CLASS_TYPE])
b_fc2 = bias_variable([CLASS_TYPE])
prediction = tf.nn.softmax(tf.matmul(h_fc1_drop, W_fc2)+b_fc2)

with tf.name_scope('loss'):
    # 交叉熵损失函数
    loss = tf.reduce_mean(-tf.reduce_sum(ys*tf.log(prediction), reduction_indices=[1]))
    tf.summary.scalar('loss', loss)
with tf.name_scope('train'):
    # 训练目标
    train_step = tf.train.AdamOptimizer(1e-4).minimize(loss)

init = tf.global_variables_initializer()
with tf.Session() as sess:
    merged = tf.summary.merge_all()
    # python3则为tf.train.SummaryWriter
    writer = tf.summary.FileWriter('logs/', sess.graph)
    '''
    运行前删去logs下所有现存日志
    运行后，在终端输入：tensorboard --logdir='/Users/admin1/PycharmProjects/Tensorflow-Learning/logs/'
    'Starting TensorBoard 41 on port 6006'这句话出现后，将显示的网址复制到浏览器地址栏
    *如果没有出现网址，在地址栏输入'localhost:6006'即可
    '''
    sess.run(init)

    s = np.zeros(MAX_LENTH**2 + 2, float)
    for line in open('ChineseSTS-master/train1.txt', 'r'):
        line_seg = line.strip().split('\t')
        w1 = line_seg[1]
        w2 = line_seg[3]
        label1 = line_seg[4]
        label2 = line_seg[5]
        line_simi = s1_s2_simipics(w1, w2, MAX_LENTH) + [float(label1)] + [float(label2)]
        s = np.vstack((s, line_simi))
    S = s[1:, :]
    X_train, X_test, Y_train, Y_test = train_test_split(S[:, :-2], S[:, -2:], train_size=0.9)

    for i in range(1000):
        batch_xs, batch_xy = X_train[5*i:5*i+400, :], Y_train[5*i:5*i+400, :]
        sess.run(train_step, feed_dict={xs: batch_xs, ys: batch_xy, keep_prob: 0.8})
        if i % 10 == 0:
            result = sess.run(merged, feed_dict={xs: batch_xs, ys: batch_xy, keep_prob: 1})
            writer.add_summary(result, i)
            print compute_accuracy(X_test, Y_test)