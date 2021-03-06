# Read tremor counts into a named tuple
# We would like to read both Wech and Idesan's tremor catalogs. 

import numpy as np 
import matplotlib.pyplot as plt 
import sys
import collections
import datetime as dt 

TremorCat = collections.namedtuple("TremorCat",['dtarray','lonarray','latarray']);


def read_wech(filename):
	dtarray=[]; lonarray=[]; latarray=[];
	start=0;

	ifile=open(filename,'r');
	for line in ifile:
		temp=line.split();
		if 'yyyy-mm-dd' in line:  # If the header is still inside. 
			start=1; continue;
		if len(temp)==5:  # If we've removed the header already. 
			start=1;
		if start==1 and len(temp)>0:
			dtarray.append(dt.datetime.strptime(temp[0]+' '+temp[1],"%Y-%m-%d %H:%M:%S"));
			lonarray.append(float(temp[3]));
			latarray.append(float(temp[2]));
		if len(latarray)==180000:
			break;
	ifile.close();

	wech_tremor = TremorCat(dtarray=np.flipud(dtarray), lonarray=np.flipud(lonarray), latarray=np.flipud(latarray));
	print("Successfully read %d tremor counts from %s " % (len(wech_tremor.dtarray),filename));
	return wech_tremor;


def read_ide(filename):
	dtarray=[]; lonarray=[]; latarray=[];
	ifile=open(filename,'r');
	for line in ifile:
		temp=line.split(',');
		if len(temp)>1:
			dtarray.append(dt.datetime.strptime(temp[0]+' '+temp[1],"%Y-%m-%d %H:%M:%S"));
			lonarray.append(float(temp[3]));
			latarray.append(float(temp[2]));
	ifile.close();	

	ide_tremor = TremorCat(dtarray=dtarray, lonarray=lonarray, latarray=latarray);
	print("Successfully read %d tremor counts from %s " % (len(ide_tremor.dtarray),filename));
	return ide_tremor;


