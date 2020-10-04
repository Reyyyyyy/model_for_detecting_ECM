import tensorflow as tf
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import os

#加载VGG16
vgg16 = (np.load('vgg16.npy',allow_pickle=True,encoding='bytes')).tolist()

#超参数
batch_size = 96
epochs = 6
lr = 0.001

def get_data():
    x_train = np.load(r'D:\核聚变课题组数据\干净数据\train_batches.npy')/255
    y_train = np.load(r'D:\核聚变课题组数据\干净数据\train_labels.npy')
    x_test = np.load(r'D:\核聚变课题组数据\干净数据\test_batches.npy')/255
    y_test = np.load(r'D:\核聚变课题组数据\干净数据\test_labels.npy')

    return (x_train,y_train),(x_test,y_test)

def conv2d(x,w,b,strides=1):
    x = tf.nn.conv2d(x,w,strides=[1,strides,strides,1],padding='SAME')
    x = tf.nn.bias_add(x,b)
    return tf.nn.relu(x)

def maxpool2d(x,strides=2):
    return tf.nn.max_pool(x,ksize=[1,2,2,1],strides=[1,strides,strides,1],padding='SAME')

def global_average_pooling(x):
    return tf.reduce_mean(x,[1,2])

class MOdel():
    
    def __init__(self):
        self.name='VGG16_GAP'
        self.weights = dict(w = tf.Variable(tf.random.truncated_normal(shape=(3,3,512,2),stddev=0.09),dtype=tf.float32))
        self.biases  = dict(b = tf.Variable(tf.zeros(2)))
        
    def VGG16(self,x):
        
        conv1_1 = conv2d(x,vgg16[b'conv1_1'][0],vgg16[b'conv1_1'][1])
        conv1_2 = conv2d(conv1_1,vgg16[b'conv1_2'][0],vgg16[b'conv1_2'][1])
        mp1 = maxpool2d(conv1_2)
        conv2_1 = conv2d(mp1,vgg16[b'conv2_1'][0],vgg16[b'conv2_1'][1])
        conv2_2 = conv2d(conv2_1,vgg16[b'conv2_2'][0],vgg16[b'conv2_2'][1])
        mp2 = maxpool2d(conv2_2)
        conv3_1 = conv2d(mp2,vgg16[b'conv3_1'][0],vgg16[b'conv3_1'][1])
        conv3_2 = conv2d(conv3_1,vgg16[b'conv3_2'][0],vgg16[b'conv3_2'][1])
        conv3_3 = conv2d(conv3_2,vgg16[b'conv3_3'][0],vgg16[b'conv3_3'][1])
        mp3 = maxpool2d(conv3_3)
        conv4_1 = conv2d(mp3,vgg16[b'conv4_1'][0],vgg16[b'conv4_1'][1])
        conv4_2 = conv2d(conv4_1,vgg16[b'conv4_2'][0],vgg16[b'conv4_2'][1])
        conv4_3 = conv2d(conv4_2,vgg16[b'conv4_3'][0],vgg16[b'conv4_3'][1])
        mp4 = maxpool2d(conv4_3)
        conv5_1 = conv2d(mp4,vgg16[b'conv5_1'][0],vgg16[b'conv5_1'][1])
        conv5_2 = conv2d(conv5_1,vgg16[b'conv5_2'][0],vgg16[b'conv5_2'][1])
        conv5_3 = conv2d(conv5_2,vgg16[b'conv5_3'][0],vgg16[b'conv5_3'][1])    
        mp5 = maxpool2d(conv5_3)
        
        return mp5
        
    def predict(self,x):

        x = self.VGG16(x)
        conv = conv2d(x,self.weights['w'],self.biases['b'])

        return global_average_pooling(conv)
        
x = tf.placeholder(tf.float32,[None,224,224,3])
y = tf.placeholder(tf.float32,[None,2])

#初始化模型
model = MOdel()

#可视化模型
tf.summary.histogram('Weights',model.weights['w'])
tf.summary.histogram('Biases',model.biases['b'])

pred = model.predict(x)
cost = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits=pred,labels=y))
optimizer = tf.train.AdamOptimizer(lr).minimize(cost)
estimator = tf.reduce_mean(tf.cast(tf.equal(tf.argmax(pred,axis=1),tf.argmax(y,axis=1)),dtype=tf.float32))
init = tf.global_variables_initializer()
saver = tf.train.Saver(model.weights.update(model.biases))

tf.summary.scalar('cross-entropy-error',cost)
merged_summary_op = tf.summary.merge_all()

#载入数据
(train_x,train_y),(test_x,test_y) = get_data()

with tf.Session() as sess:
    
    sess.run(init)
    summary_writer = tf.summary.FileWriter('graphs',sess.graph)
    num_data = train_x.shape[0]
    
    #训练模型
    for step in range(int(epochs*num_data/batch_size)):
        pointer = step*batch_size%num_data
        x_batch = train_x[pointer:pointer+batch_size]
        y_batch = train_y[pointer:pointer+batch_size]

        if x_batch.shape[0] ==0:
            continue
        
        sess.run(optimizer,feed_dict={x:x_batch,y:y_batch})
        loss = sess.run(cost,feed_dict={x:x_batch,y:y_batch})
        acc  = sess.run(estimator,feed_dict={x:x_batch,y:y_batch})
        print('Loss:',loss)
        print('Accuracy:',acc)
        print('\n')
        #记录训练过程
        summary_str = sess.run(merged_summary_op,feed_dict={x:x_batch,y:y_batch})
        summary_writer.add_summary(summary_str,step)

    summary_writer.close()    
    #评估模型
    test_batch = 9
    TP = 0
    FP = 0
    TN = 0
    FN = 0
    for i in range(int(test_x.shape[0]/test_batch)):
        y_pred = sess.run(tf.argmax(pred,axis=1),feed_dict={x:test_x[i*test_batch:(i+1)*test_batch]})
        y_true = np.argmax(test_y[i*test_batch:(i+1)*test_batch],axis=1)

        TP += np.sum(np.logical_and(np.equal(y_pred,0),np.equal(y_true,0)))
        FP += np.sum(np.logical_and(np.equal(y_pred,0),np.equal(y_true,1)))
        TN += np.sum(np.logical_and(np.equal(y_pred,1),np.equal(y_true,1)))
        FN += np.sum(np.logical_and(np.equal(y_pred,1),np.equal(y_true,0)))

    accuracy = (TP+TN)/(TP+TN+FP+FN)
    precision = TP/(TP+FP)
    recall = TP/(TP+FN)
    N_score = TN/(TN+FP)
    F_score = (2*precision*recall)/(precision+recall)
    
    print('\n---Done!---\n')
    print('Accuracy:',accuracy)
    print('Precison:',precision)
    print('Recall:',recall)
    print('F-Score:',F_score)
    print('N-Score:',N_score)
    #保存模型
    saver.save(sess,'./my_model.ckpt')










        
