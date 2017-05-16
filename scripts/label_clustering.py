import pandas as pd
import numpy as np
from haversine import haversine # pip install haversine
import sys
from scipy.cluster.hierarchy import linkage, cut_tree, dendrogram
from collections import Counter

GROUND_TRUTH = 1
TURKER = 2
TEST = 3

if len(sys.argv) < 2:
	print 'Argument needed to specify whether ground truth or turker labels are to be clustered.'
	exit()
else:
	if sys.argv[1] in ['gt', 'GT', 'ground_truth', 'groundTruth', 'groundtruth', 'g']:
		data = GROUND_TRUTH
		MAJORITY_THRESHOLD = 2
	elif sys.argv[1] in ['turker', 'turk', 't']:
		data = TURKER
		MAJORITY_THRESHOLD = 3
	elif sys.argv[1] == 'test':
		data = TEST
		MAJORITY_THRESHOLD = 3
	else:
		print 'Try passing \'gt\' for ground truth labels, \'t\' for turker labels, or \'test\' for a sample of test labels.'
		exit()

# read in data
names = ['lng', 'lat', 'label_type', 'user_id']
#names = ['lng', 'lat', 'label_type', 'user_id', 'asmt_id', 'turker_id', 'route_id']
if data == GROUND_TRUTH:
	label_data = pd.read_csv('../data/labels-ground_truth.csv', names=names)
elif data == TURKER:
	label_data = pd.read_csv('../data/labels-turker.csv', names=names)
elif data == TEST:
	label_data = pd.read_csv('../data/labels-test.csv', names=names)

# remove other, occlusion, and no sidewalk label types to make analysis for the class project easier
included_types = ['CurbRamp', 'SurfaceProblem', 'Obstacle', 'NoCurbRamp']
label_data = label_data[label_data.label_type.isin(included_types)]

# remove weird entries with longitude values (on the order of 10^14)
if sum(label_data.lng > 360) > 0:
	print 'There are %d invalid longitude values, removing those entries.' % sum(label_data.lng > 360)
	label_data = label_data.drop(label_data[label_data.lng > 360].index)

# put lat-lng in a tuple so it plays nice w/ haversine function
label_data['coords'] = label_data.apply(lambda x: (x.lat, x.lng), axis = 1)
label_data['id'] =  label_data.index.values

# sample data the test data so that distance matrix isn't too large to fit in memory
if data == TEST:
	label_data = label_data.sample(1000)

# create distance matrix between all pairs of labels
haver_vec = np.vectorize(haversine, otypes=[np.float64])
dist_matrix = label_data.groupby('id').apply(lambda x: pd.Series(haver_vec(label_data.coords, x.coords)))

# cluster based on distance and maybe label_type
label_link = linkage(dist_matrix, method='complete')

# cuts tree so that only labels less than 0.5m apart are clustered, adds a col
# to dataframe with label for the cluster they are in
label_data['cluster'] = cut_tree(label_link, height = 1.0)

# Majority vote to decide what is included. If a cluster has at least 3 people agreeing on the type
# of the label, that is included. Any less, and we add it to the list of problem_clusters, so that
# we can look at them by hand through the admin interface to decide.
included_labels = [] # list of tuples (label_type, lat, lng)
problem_clusters = {} # key: cluster_number, value: indices or labels in the cluster
clusters = label_data.groupby('cluster')
for clust_num, clust in clusters:
	# only include one label type per user per cluster
	no_dups = clust.drop_duplicates(subset=['label_type', 'user_id'])
	# count up the number of each label type in cluster, any with a majority are included
	for label_type in included_types:
		single_type_clust = no_dups.drop(no_dups[no_dups.label_type != label_type].index)
		if len(single_type_clust) > MAJORITY_THRESHOLD:
			ave = np.mean(single_type_clust['coords'].tolist(), axis=0) # use ave pos of clusters
			included_labels.append((label_type, ave[0], ave[1]))
	else:
		problem_clusters[clust_num] = clust.index

# output the labels from majority vote as a csv
included = pd.DataFrame(included_labels, columns=['type', 'lat', 'lng'])
if data == GROUND_TRUTH:
	included.to_csv('../data/ground_truth-part1.csv', index=False)
elif data == TURKER:
	included.to_csv('../data/turker-final.csv', index=False)
elif data == TEST:
	included.to_csv('../data/test-final.csv', index=False)

if data == GROUND_TRUTH:
	# order GT labels that we are unsure about by cluster, so they are easier to manually look through.
	problem_labels = label_data[label_data.cluster.isin(problem_clusters.keys())]

	# output GT labels that we are NOT sure about to another CSV so we can look through them.
	problem_labels.to_csv('../data/ground_truth-problem_labels.csv', index=False)

sys.exit()
