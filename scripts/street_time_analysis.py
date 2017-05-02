import pandas as pd
import numpy as np
import sys
from haversine import haversine # pip install haversine

# read in data
f = open('../data/street_length_data.csv')
names = ["user_id", "street_edge_id", "start_time", "end_time", "lng1", "lat1", "lng2", "lat2"]
data = np.genfromtxt(f, delimiter=',', names=names, case_sensitive=True, dtype=None)
f.close()

# convert to pandas dataframe
street_data = pd.DataFrame(data, columns=data.dtype.names)

# correctly format start and end time from strings, and fill a time duration column w/ dummy vals
street_data['start_time'] = pd.to_datetime(street_data['start_time'], format='%Y-%m-%d %H:%M:%S')
street_data['end_time'] = pd.to_datetime(street_data['end_time'], format='%Y-%m-%d %H:%M:%S')
street_data['duration'] = pd.Timedelta(0)

# function that calculates the time spent on each street, where each entry in a data frame, df, are
# entries from the same user_id with the same start_time.
def calculateDuration(df):
	# sort the entries by ending time
	df = df.sort_values('end_time')
	# all entries except first have duration end_time[i]-end_time[i-1]
	if len(df) > 1:
		df['duration'] = (df['end_time'] - df['end_time'].shift()).fillna(0)
	# the first entry has a duration of end_time-start_time
	df.iloc[0]['duration'] = df.iloc[0]['end_time'] - df.iloc[0]['start_time']
	return df

# group by user ID and start time, then calculate duration for first in each group as
# end_time-start_time, and calculate duration for all remaining as end_time[i]-end_time[i-1]
# TODO group by IP address if anon user (97760883-8ef0-4309-9a5e-0c086ef27573)
street_data = street_data.groupby(['user_id', 'start_time']).apply(calculateDuration)

# calculate  distance between endpoints of street, minutes per km, and speed
street_data['dist'] = street_data.apply(lambda x: haversine((x.lat1,x.lng1),(x.lat2,x.lng2)), axis=1)
street_data['mins'] = street_data.apply(lambda x: x.duration / pd.Timedelta('1 minute'), axis=1)
street_data['mins_per_km'] = street_data['mins'] / street_data['dist']
street_data['mps'] = 1000.0 * street_data['dist'] / (60 * street_data['mins'])

# throw out the data with unreasonably long time to completion (threw out those
# over 3 hours, but there were a lot that were on the order of a year because of
# a bug manifesting itself in the earlier data) and unreasonably high speeds;
# anything above 7.5m/s (17mph) right now.
street_data = street_data.drop(street_data[street_data.mins > 180].index)
street_data = street_data.drop(street_data[street_data.mps > 7.5].index)

# print average m/s
# TODO figure out why the answer is slightly different than answer from R script
print str((sum(street_data['dist'])*1000.0)/(60*sum(street_data['mins']))) # m/s

sys.exit()
