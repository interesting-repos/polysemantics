import tensorflow.python.platform

import numpy as np
import tensorflow as tf

# Global variables.
NUM_LABELS = 2    # The number of labels.
BATCH_SIZE = 1  # The number of training examples to use per training step.

tf.app.flags.DEFINE_string('name', None, 'Name of test to run')
tf.app.flags.DEFINE_integer('length', None, 'Length of sequences')
tf.app.flags.DEFINE_integer('num_epochs', 1,
                            'Number of passes over the training data.')
tf.app.flags.DEFINE_integer('num_hidden', 1,
                            'Number of nodes in the hidden layer.')
FLAGS = tf.app.flags.FLAGS

# Extract numpy representations of the labels and features given rows consisting of:
#   label, feat_0, feat_1, ..., feat_n
def extract_data(filename):

    # Arrays to hold the labels and feature vectors.
    labels = []
    fvecs = []

    # Iterate over the rows, splitting the label from the features. Convert labels
    # to integers and features to floats.
    for line in file(filename):
        row = line.strip('\n').split(",")
        labels.append(int(row[0]))
        fvecs.append([float(x) for x in row[1:]])
        print "Vector length " + str(len([float(x) for x in row[1:]]))

    # Convert the array of float arrays into a numpy float matrix.
    fvecs_np = np.matrix(fvecs).astype(np.float32)

    # Convert the array of int labels into a numpy array.
    labels_np = np.array(labels).astype(dtype=np.uint8)

    # Convert the int numpy array into a one-hot matrix.
    labels_onehot = (np.arange(NUM_LABELS) == labels_np[:, None]).astype(np.float32)

    # Return a pair of the feature matrix and the one-hot label matrix.
    return fvecs_np,labels_onehot

# Init weights method. (Lifted from Delip Rao: http://deliprao.com/archives/100)
def init_weights(shape, init_method='xavier', xavier_params = (None, None)):
    if init_method == 'zeros':
        return tf.Variable(tf.zeros(shape, dtype=tf.float32))
    elif init_method == 'uniform':
        return tf.Variable(tf.random_normal(shape, stddev=0.01, dtype=tf.float32))
    else: #xavier
        (fan_in, fan_out) = xavier_params
        low = -4*np.sqrt(6.0/(fan_in + fan_out)) # {sigmoid:4, tanh:1} 
        high = 4*np.sqrt(6.0/(fan_in + fan_out))
        return tf.Variable(tf.random_uniform(shape, minval=low, maxval=high, dtype=tf.float32))
    
def main(argv=None):    
    # For tensorboard
    sess = tf.InteractiveSession()
    
    # Get the data.
    train_data_filename = "data/outfile-length" + str(FLAGS.length) + "-train-" + FLAGS.name + ".csv"
    test_data_filename = "data/outfile-length" + str(FLAGS.length) + "-eval-" + FLAGS.name + ".csv"

    # Extract it into numpy arrays.
    train_data,train_labels = extract_data(train_data_filename)
    test_data, test_labels = extract_data(test_data_filename)

    # Get the shape of the training data.
    train_size,num_features = train_data.shape

    # Get the number of epochs for training.
    num_epochs = FLAGS.num_epochs

    # Get the size of layer one.
    num_hidden = FLAGS.num_hidden
 
    # This is where training samples and labels are fed to the graph.
    # These placeholder nodes will be fed a batch of training data at each
    # training step using the {feed_dict} argument to the Run() call below.
    x = tf.placeholder("float", shape=[None, num_features])
    y_ = tf.placeholder("float", shape=[None, NUM_LABELS])
        
    # For the test data, hold the entire dataset in one constant node.
    test_data_node = tf.constant(test_data)

    # Define and initialize the network.

    # Initialize the hidden weights and biases.
    w_hidden = init_weights(
        [num_features, num_hidden],
        'xavier',
        xavier_params=(num_features, num_hidden))

    b_hidden = init_weights([1,num_hidden],'zeros')

    # The hidden layer.
    hidden = tf.nn.tanh(tf.matmul(x,w_hidden) + b_hidden)
    # subst tf.nn.relu here for rectified linear units, the original is tanh
    # if you use relu, you should probably switch out `xavier` below for `uniform`

    # Initialize the output weights and biases.
    w_out = init_weights(
        [num_hidden, NUM_LABELS],
        'xavier',
        xavier_params=(num_hidden, NUM_LABELS))
    
    b_out = init_weights([1,NUM_LABELS],'zeros')

    # The output layer.
    y = tf.nn.softmax(tf.matmul(hidden, w_out) + b_out)
    
    # Stuff for tensorboard
    w_hist = tf.histogram_summary("weights", w_hidden)
    b_hist = tf.histogram_summary("biases", b_hidden)
    y_hist = tf.histogram_summary("y", y)
    
    # Optimization.
    cross_entropy = -tf.reduce_sum(y_*tf.log(y))
    train_step = tf.train.GradientDescentOptimizer(0.01).minimize(cross_entropy)
    
    # Evaluation.
    correct_prediction = tf.equal(tf.argmax(y,1), tf.argmax(y_,1))
    accuracy = tf.reduce_mean(tf.cast(correct_prediction, "float"))

    accuracy_summary = tf.scalar_summary("accuracy", accuracy)
	
    # More tensorboard stuff: merge all the summaries and write them out
    merged = tf.merge_all_summaries()
    summary_filename = "/home/ubuntu/polysemantics/logs/" + FLAGS.name + "-length" + str(FLAGS.length)
    writer = tf.train.SummaryWriter(summary_filename, sess.graph_def)
    
    # Run all the initializers to prepare the trainable parameters.
    tf.initialize_all_variables().run()
    	
    print 'Initialized!'
    print
    print 'Training.'
    	
    # Iterate and train.
    for step in xrange(num_epochs * train_size // BATCH_SIZE):
        if step % 10 == 0: # just test, no learning
            feed = {x: test_data, y_: test_labels}
            result=sess.run([merged,accuracy],feed_dict=feed)
            summary_str = result[0]
            acc = result[1]
            writer.add_summary(summary_str, step)
            print("Accuracy at step %s: %s" % (step, acc))
        else: # actually do learning
            offset = (step * BATCH_SIZE) % train_size
            batch_data = train_data[offset:(offset + BATCH_SIZE), :]
            batch_labels = train_labels[offset:(offset + BATCH_SIZE)]
            feed={x: batch_data, y_: batch_labels}
    	    sess.run(train_step, feed_dict=feed)
    
    print(accuracy.eval({x: test_data, y_: test_labels}))
            
if __name__ == '__main__':
    tf.app.run()