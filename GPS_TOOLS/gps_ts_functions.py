# May/June 2018
# This is a toolbox that operates on Timeseries objects. 
# Contains functions to map, filter, and reduce generic GPS time series


import numpy as np 
import subprocess, sys, collections
import datetime as dt 
from scipy import signal
import gps_io_functions

# A line for referencing the namedtuple definition. 
Timeseries = collections.namedtuple("Timeseries",['name','coords','dtarray','dN', 'dE','dU','Sn','Se','Su','EQtimes']);  # in mm


# -------------------------------------------- # 
# FUNCTIONS THAT TAKE TIME SERIES OBJECTS # 
# AND RETURN OTHER TIME SERIES OBJECTS # 
# -------------------------------------------- # 


def remove_outliers(Data0, outliers_def):
	medfilt_e=signal.medfilt(Data0.dE, 35);
	medfilt_n=signal.medfilt(Data0.dN, 35);
	medfilt_u=signal.medfilt(Data0.dU, 35);

	newdtarray=[]; newdN=[]; newdE=[]; newdU=[];
	for i in range(len(medfilt_e)):
		if abs(Data0.dE[i]-medfilt_e[i])<outliers_def and abs(Data0.dN[i]-medfilt_n[i])<outliers_def and abs(Data0.dU[i]-medfilt_u[i])<outliers_def*2:
			newdtarray.append(Data0.dtarray[i]);
			newdE.append(Data0.dE[i]);
			newdN.append(Data0.dN[i]);
			newdU.append(Data0.dU[i]);
		else:
			newdtarray.append(Data0.dtarray[i]);
			newdE.append(np.nan);
			newdN.append(np.nan);
			newdU.append(np.nan);
	
	newData=Timeseries(name=Data0.name, coords=Data0.coords, dtarray=newdtarray, dN=newdN, dE=newdE, dU=newdU, Sn=Data0.Sn, Se=Data0.Se, Su=Data0.Su, EQtimes=Data0.EQtimes);
	return newData;


def impose_time_limits(Data0, starttime, endtime):
	# Starttime and endtime are datetime objects
	newdtarray=[]; newdN=[]; newdE=[]; newdU=[]; newSn=[]; newSe=[]; newSu=[];
	for i in range(len(Data0.dN)):
		if Data0.dtarray[i]>=starttime and Data0.dtarray[i]<=endtime:
			newdtarray.append(Data0.dtarray[i]);
			newdE.append(Data0.dE[i]);
			newdN.append(Data0.dN[i]);
			newdU.append(Data0.dU[i]);
			newSe.append(Data0.Se[i]);
			newSn.append(Data0.Sn[i]);
			newSu.append(Data0.Su[i]);
	
	newData=Timeseries(name=Data0.name, coords=Data0.coords, dtarray=newdtarray, dN=newdN, dE=newdE, dU=newdU, Sn=newSn, Se=newSe, Su=newSu, EQtimes=Data0.EQtimes);
	return newData;


def remove_nans(Data0):
	idxE=np.isnan(Data0.dE);
	idxN=np.isnan(Data0.dN);
	idxU=np.isnan(Data0.dU);
	temp_dates=[];
	temp_east=[];
	temp_north=[];
	temp_vert=[];
	temp_Sn=[];
	temp_Se=[];
	temp_Su=[];
	for i in range(len(Data0.dtarray)):
		if idxE[i]==0 and idxN[i]==0 and idxU[i]==0:
			temp_dates.append(Data0.dtarray[i]);
			temp_east.append(Data0.dE[i]);
			temp_north.append(Data0.dN[i]);
			temp_vert.append(Data0.dU[i]);
			temp_Se.append(Data0.Se[i]);
			temp_Sn.append(Data0.Sn[i]);
			temp_Su.append(Data0.Su[i]);
	newData=Timeseries(name=Data0.name, coords=Data0.coords, dtarray=temp_dates, dN=temp_north, dE=temp_east, dU=temp_vert, Sn=temp_Sn, Se=temp_Se, Su=temp_Su, EQtimes=Data0.EQtimes);
	return newData;


def look_up_seasonal_coefs(name,table_file):
	[E, N, U, Ea1, Na1, Ua1, Ea2, Na2, Ua2, Es1, Ns1, Us1, Es2, Ns2, Us2]=gps_io_functions.read_noel_file_station(table_file,name);
	east_params=[E, Ea2, Ea1, Es2, Es1];
	north_params=[N, Na2, Na1, Ns2, Na2];
	up_params=[U, Ua2, Ua1, Us2, Us1];
	return [east_params, north_params, up_params];


def detrend_data_by_value(Data0,east_params,north_params,vert_params):
	east_detrended=[]; north_detrended=[]; vert_detrended=[];
	idx=np.isnan(Data0.dE);
	if(sum(idx))>0:  # if there are nans, please pull them out. 
		Data0=remove_nans(Data0);
	decyear=get_float_times(Data0.dtarray);
	
	east_model=linear_annual_semiannual_function(decyear,east_params);
	north_model=linear_annual_semiannual_function(decyear,north_params);
	vert_model=linear_annual_semiannual_function(decyear,vert_params);

	for i in range(len(decyear)):
		east_detrended.append(Data0.dE[i]-(east_model[i]) );
		north_detrended.append(Data0.dN[i]-(north_model[i]) );
		vert_detrended.append(Data0.dU[i]-(vert_model[i]) );
	east_detrended=east_detrended-east_detrended[0];
	north_detrended=north_detrended-north_detrended[0];
	vert_detrended=vert_detrended-vert_detrended[0];
	newData=Timeseries(name=Data0.name, coords=Data0.coords, dtarray=Data0.dtarray, dN=north_detrended, dE=east_detrended, dU=vert_detrended, Sn=Data0.Sn, Se=Data0.Se, Su=Data0.Su, EQtimes=Data0.EQtimes);
	return newData;



# FUTURE FEATURES: 
def rotate_data():
	return;





# -------------------------------------------- # 
# FUNCTIONS THAT TAKE TIME SERIES OBJECTS #
# AND RETURN SCALARS OR VALUES # 
# -------------------------------------------- # 

def get_slope(Data0, starttime=[], endtime=[]):
	# Model the data with a best-fit y = mx + b. 
	if starttime==[]:
		starttime=Data0.dtarray[0];
	if endtime==[]:
		endtime=Data0.dtarray[-1];

	# Defensive programming
	if starttime<Data0.dtarray[0]:
		starttime=Data0.dtarray[0];
	if endtime>Data0.dtarray[-1]:
		endttime=Data0.dtarray[-1];
	if endtime<Data0.dtarray[0]:
		print("Error: end time before start of array for station %s. Returning Nan" % Data0.name);
		return [np.nan,np.nan,np.nan,np.nan,np.nan,np.nan];
	if starttime>Data0.dtarray[-1]:
		print("Error: start time after end of array for station %s. Returning Nan" % Data0.name);
		return [np.nan,np.nan,np.nan,np.nan,np.nan,np.nan];

	# Cut to desired window, and remove nans
	mydtarray=[]; myeast=[]; mynorth=[]; myup=[];
	for i in range(len(Data0.dtarray)):
		if Data0.dtarray[i]>=starttime and Data0.dtarray[i]<=endtime and ~np.isnan(Data0.dE[i]):
			mydtarray.append(Data0.dtarray[i]);
			myeast.append(Data0.dE[i]);
			mynorth.append(Data0.dN[i]);
			myup.append(Data0.dU[i]);

	if len(mydtarray)==0:
		print("Error: no time array for station %s. Returning Nan" % Data0.name);
		return [np.nan,np.nan,np.nan,np.nan,np.nan,np.nan];		
	time_duration=mydtarray[-1]-mydtarray[0];	
	if time_duration.days<365:
		print("Error: using less than one year of data to estimate parameters for station %s. Returning Nan" % Data0.name);
		return [np.nan,np.nan,np.nan,np.nan,np.nan,np.nan];

	# doing the inversion here, since it's only one line.
	decyear=get_float_times(mydtarray);
	east_coef=np.polyfit(decyear,myeast,1);
	north_coef=np.polyfit(decyear,mynorth,1);
	vert_coef=np.polyfit(decyear,myup,1);
	east_slope=east_coef[0];
	north_slope=north_coef[0];
	vert_slope=vert_coef[0];


	# How bad is the fit to the line? 
	east_trend=[east_coef[0]*x + east_coef[1] for x in decyear];
	east_detrended=[myeast[i]-east_trend[i] for i in range(len(myeast))];
	east_std = np.std(east_detrended);
	north_trend=[north_coef[0]*x + north_coef[1] for x in decyear];
	north_detrended=[mynorth[i]-north_trend[i] for i in range(len(mynorth))];
	north_std = np.std(north_detrended);
	vert_trend=[vert_coef[0]*x + vert_coef[1] for x in decyear];
	vert_detrended=[myup[i]-vert_trend[i] for i in range(len(myup))];
	vert_std = np.std(vert_detrended);	

	return [east_slope, north_slope, vert_slope, east_std, north_std, vert_std];




def get_linear_annual_semiannual(Data0, starttime=[], endtime=[]):
	# Model the data with a best-fit GPS = Acos(wt) + Bsin(wt) + Ccos(2wt) + Dsin(2wt) + E*t + F; 
	if starttime==[]:
		starttime=Data0.dtarray[0];
	if endtime==[]:
		endtime=Data0.dtarray[-1];

	# Defensive programming
	if starttime<Data0.dtarray[0]:
		starttime=Data0.dtarray[0];
	if endtime>Data0.dtarray[-1]:
		endttime=Data0.dtarray[-1];
	if endtime<Data0.dtarray[0]:
		print("Error: end time before start of array for station %s. Returning Nan" % Data0.name);
		east_params=[np.nan,0,0,0,0];  north_params=[np.nan,0,0,0,0]; up_params=[np.nan,0,0,0,0];
	if starttime>Data0.dtarray[-1]:
		print("Error: start time after end of array for station %s. Returning Nan" % Data0.name);
		east_params=[np.nan,0,0,0,0];  north_params=[np.nan,0,0,0,0]; up_params=[np.nan,0,0,0,0];

	# Cut to desired time window, and remove nans.
	mydtarray=[]; myeast=[]; mynorth=[]; myup=[];
	for i in range(len(Data0.dtarray)):
		if Data0.dtarray[i]>=starttime and Data0.dtarray[i]<=endtime and ~np.isnan(Data0.dE[i]):
			mydtarray.append(Data0.dtarray[i]);
			myeast.append(Data0.dE[i]);
			mynorth.append(Data0.dN[i]);
			myup.append(Data0.dU[i]);

	if len(mydtarray)<365:
		print("Error: using less than one year of data to estimate parameters for station %s. Returning Nan" % Data0.name);
		east_params=[np.nan,0,0,0,0];  north_params=[np.nan,0,0,0,0]; up_params=[np.nan,0,0,0,0];
		return [east_params, north_params, up_params];

	decyear=get_float_times(mydtarray);	
	east_params_unordered=invert_linear_annual_semiannual(decyear,myeast);
	north_params_unordered=invert_linear_annual_semiannual(decyear, mynorth);
	vert_params_unordered=invert_linear_annual_semiannual(decyear, myup);

	# The definition for returning parameters, consistent with Noel's reporting:
	# slope, a2(cos), a1(sin), s2, s1. 
	east_params=[east_params_unordered[4], east_params_unordered[0], east_params_unordered[1], east_params_unordered[2], east_params_unordered[3]];
	north_params=[north_params_unordered[4], north_params_unordered[0], north_params_unordered[1], north_params_unordered[2], north_params_unordered[3]];
	vert_params=[vert_params_unordered[4], vert_params_unordered[0], vert_params_unordered[1], vert_params_unordered[2], vert_params_unordered[3]];

	return [east_params, north_params, vert_params];


def invert_linear_annual_semiannual(decyear,data):
	"""
	Take a time series and fit a best-fitting linear least squares equation: 
	GPS = Acos(wt) + Bsin(wt) + Ccos(2wt) + Dsin(2wt) + E*t + F; 
	Here we also solve for a linear trend as well. 
	"""
	design_matrix=[];
	w = 2*np.pi / 1.0;  
	for t in decyear:
		design_matrix.append([np.cos(w*t), np.sin(w*t), np.cos(2*w*t), np.sin(2*w*t), t, 1]);
	design_matrix= np.array(design_matrix);
	params = np.dot(np.linalg.inv(np.dot(design_matrix.T, design_matrix)), np.dot(design_matrix.T, data));
	return params;


def get_float_times(datetimes):
	floats=[];
	for item in datetimes:
		temp=item.strftime("%Y %j");
		temp=temp.split();
		floats.append(float(temp[0])+float(temp[1])/365.24);
	return floats;

def get_float_time(datetime_item):
	temp=datetime_item.strftime("%Y %j");
	temp=temp.split();
	floats = (float(temp[0])+float(temp[1])/365.24);
	return floats;


def float_to_dt(float_time):
	# Example: 2014.194 --> datetime object
	fractional_year=str(1+int(365.24*(float_time-np.floor(float_time))));  # something like 004, 204, 321, etc. 
	if len(fractional_year)==1:
		fractional_year='00'+fractional_year;
	elif len(fractional_year)==2:
		fractional_year='0'+fractional_year;
	if fractional_year=='367' or fractional_year=='366':
		fractional_year='365';
	myyear = str(int(np.floor(float_time)));  # something like 2014
	my_date = dt.datetime.strptime(myyear+fractional_year,"%Y%j");
	return my_date;








# -------------------------------------------- # 
# FUNCTIONS THAT TAKE PARAMETERS
# AND RETURN Y=F(X) ARRAYS
# -------------------------------------------- # 


def linear_annual_semiannual_function(decyear, fit_params):
	"""
	Given curve parameters and a set of observation times, build the function y = f(x). 
	Model consists of GPS_V = E*t + Acos(wt) + Bsin(wt) + Ccos(2wt) + Dsin(2wt);
	"""
	model_def = [];
	w = 2*np.pi / 1.0; 
	for t in decyear:
		model_def.append( fit_params[0]*t + (fit_params[1]*np.cos(w*t)) + (fit_params[2]*np.sin(w*t)) + (fit_params[3]*np.cos(2*w*t)) + (fit_params[4]*np.sin(2*w*t)) );
	return model_def;


def annual_semiannual_only_function(decyear, fit_params):
	"""
	Given curve parameters and a set of observation times, build the function y = f(x). 
	Model consists of GPS_V = Acos(wt) + Bsin(wt) + Ccos(2wt) + Dsin(2wt);
	"""
	model_def = [];
	w = 2*np.pi / 1.0; 
	for t in decyear:
		model_def.append( (fit_params[0]*np.cos(w*t)) + (fit_params[1]*np.sin(w*t)) + (fit_params[2]*np.cos(2*w*t)) + (fit_params[3]*np.sin(2*w*t)) );
	return model_def;


def annual_only_function(decyear, fit_params):
	"""
	Given curve parameters and a set of observation times, build the function y = f(x). 
	Model consists of GPS_V = Acos(wt) + Bsin(wt); 
	"""
	model_def = [];
	w = 2*np.pi / 1.0; 
	for t in decyear:
		model_def.append( (fit_params[0]*np.cos(w*t)) + (fit_params[1]*np.sin(w*t)) );
	return model_def;






