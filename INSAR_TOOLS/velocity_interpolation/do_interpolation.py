
""" This code does a cubic 2D interpolation on the GPS velocities to 
generate an expected field of InSAR velocities (if I were to do the actual SBAS technique, what would I see?)
It uses some fun new tricks:
Scipy interpolate: cubic or linear
matplotlib.path: can replicate the matlab inpolygon() function.

Dlos = [U_n sin(phi) - U_e cos(phi)]*sin(lamda) + U_u cos(lamda)
[U_e, U_n, U_u] are the east, north, and up components of the deformation. 
phi   = azimuth of satellite heading vector, positive clockwise from north.
lamda = local incidence angle at the reflector.
from Fialko et al., 2001. 

"""

import numpy as np 
import matplotlib.pyplot as plt 
import sys
import matplotlib.path as path
import collections
from scipy import interpolate
import haversine

param_collection = collections.namedtuple("param_collection",['input_file','type_of_interp','ascending_flight_angle','descending_flight_angle','incidence_angle','xbounds','ybounds','point1', 'point2', 'reference_point']);
vel_collection = collections.namedtuple("vel_collection",['lon','lat','evel', 'nvel','vvel']);
interpolated_fields=collections.namedtuple("interp_fields",['interp_x','interp_y','interp_east','interp_north','interp_ascend','interp_descend']);


def do_interpolation():
	my_param_collection = configure();
	[vel_tuple,ca_border,or_border] = inputs(my_param_collection);
	my_interpolated_fields, asc_ref, des_ref = compute(vel_tuple, my_param_collection, ca_border, or_border);
	outputs(vel_tuple,my_param_collection, ca_border, or_border, my_interpolated_fields, asc_ref, des_ref);


# -------------- CONFIG  --------------- # 
def configure():
	reference_frame="nam08";
	input_file=reference_frame+"_vel_field.txt";
	type_of_interp="cubic"
	ascending_flight_angle=360-14;  # degrees from north (like strike)
	descending_flight_angle=180+14; # degrees from north (like strike)
	incidence_angle = 30;     # degrees from vertical (looking straight down is 0 degrees). 

	# # Oregon
	# xbounds=[-125,-122];
	# ybounds=[41.5, 46.0];
	# gradient_point1=[-123.0,43.0];
	# gradient_point2=[-123.0,42.0];
	# reference_point=[];	

	
	# Mendocino
	xbounds=[-125,-122];
	ybounds=[39.0, 42.0];
	gradient_point1=[-124.0,40.0];
	gradient_point2=[-124.0,41.0];
	reference_point=[-123.4, 39.9];

	# # Bay Area
	# xbounds=[-124,-121.3];
	# ybounds=[36.8, 39.0];
	# gradient_point1=[-122.3,37.2];
	# gradient_point2=[-121.5,37.6];
	# reference_point=[-121.5, 37.0];

	my_param_collection=param_collection(input_file=input_file,type_of_interp=type_of_interp,
		ascending_flight_angle=ascending_flight_angle,descending_flight_angle=descending_flight_angle, incidence_angle=incidence_angle,
		xbounds=xbounds, ybounds=ybounds, point1=gradient_point1, point2=gradient_point2, reference_point=reference_point);
	return my_param_collection;




# -------------- INPUTS  --------------- # 
def inputs(my_param_collection):
	ifile=open(my_param_collection.input_file,'r');
	lon=[]; lat=[]; evel=[]; nvel=[]; vvel=[];
	for line in ifile:
		temp=line.split();
		if temp[-1]=="nan":
			continue;
		else:
			lon.append(float(temp[1]))
			lat.append(float(temp[2]))
			evel.append(float(temp[3]))
			nvel.append(float(temp[4]))
			vvel.append(float(temp[5]))
	ifile.close();
	vel_tuple = vel_collection(lon=lon, lat=lat, evel=evel, nvel=nvel, vvel=vvel);
	ca_border=np.loadtxt("california_bdr");
	or_border=np.loadtxt("oregon_bdr");
	return [vel_tuple, ca_border, or_border];




# ---------- COMPUTE --------------- # 
def compute(vel_tuple,my_param_collection, ca_border, or_border):
	# Scipy returns a function that you can use on a new set of x,y pairs. 
	f_east = interpolate.interp2d(vel_tuple.lon, vel_tuple.lat, vel_tuple.evel, kind=my_param_collection.type_of_interp);
	f_north = interpolate.interp2d(vel_tuple.lon, vel_tuple.lat, vel_tuple.nvel, kind=my_param_collection.type_of_interp);

	CA_path=path.Path(ca_border);
	OR_path=path.Path(or_border);

	# The new interpolation grid: a new set of points with some chosen spacing
	xarray=np.arange(my_param_collection.xbounds[0],my_param_collection.xbounds[1],0.08);
	yarray=np.arange(my_param_collection.ybounds[0],my_param_collection.ybounds[1],0.08);
	[X,Y]=np.meshgrid(xarray,yarray);

	new_x_in_CA=[]; new_y_in_CA=[]; new_east=[]; new_north=[]; new_vertical=[];
	for i in range(np.shape(X)[0]):
		for j in range(np.shape(X)[1]):
			if CA_path.contains_point([X[i,j],Y[i,j]])==1 or OR_path.contains_point([X[i,j],Y[i,j]])==1:   # if the point is in CA or OR
				new_x_in_CA.append(X[i,j]);
				new_y_in_CA.append(Y[i,j]);

	# Evaluate the linear or cubic interpolation function at new points
	for i in range(len(new_x_in_CA)):
		new_east.append(f_east(new_x_in_CA[i],new_y_in_CA[i]))  # only want to give the functions one point at a time. 
		new_north.append(f_north(new_x_in_CA[i],new_y_in_CA[i]));
		new_vertical.append(0.0);  # there's no vertical deformation in this field by construction. 
	
	# Transform each field into the LOS fields 
	ascending_LOS_array=project_to_LOS(new_east,new_north,new_vertical,my_param_collection.ascending_flight_angle,my_param_collection.incidence_angle);
	descending_LOS_array=project_to_LOS(new_east,new_north,new_vertical,my_param_collection.descending_flight_angle,my_param_collection.incidence_angle);
	my_interpolated_fields=interpolated_fields(interp_x=new_x_in_CA,interp_y=new_y_in_CA,interp_east=new_east,interp_north=new_north,interp_ascend=ascending_LOS_array,interp_descend=descending_LOS_array);

	# Take the reference point and transform its velocity into LOS. 
	velref_e=f_east(my_param_collection.reference_point[0],my_param_collection.reference_point[1]);
	velref_n=f_north(my_param_collection.reference_point[0],my_param_collection.reference_point[1]);
	ascending_LOS_reference=project_to_LOS(velref_e,velref_n,0,my_param_collection.ascending_flight_angle,my_param_collection.incidence_angle)[0];
	descending_LOS_reference=project_to_LOS(velref_e,velref_n,0,my_param_collection.descending_flight_angle,my_param_collection.incidence_angle)[0];

	# Here I want to evaluate gradients at two hard-coded points. 
	e_def1=f_east(my_param_collection.point1[0],my_param_collection.point1[1]);
	n_def1=f_north(my_param_collection.point1[0],my_param_collection.point1[1]);
	e_def2=f_east(my_param_collection.point2[0],my_param_collection.point2[1]);
	n_def2=f_north(my_param_collection.point2[0],my_param_collection.point2[1]);	
	ascending1=project_to_LOS(e_def1,n_def1,0.0,my_param_collection.ascending_flight_angle,my_param_collection.incidence_angle);
	ascending2=project_to_LOS(e_def2,n_def2,0.0,my_param_collection.ascending_flight_angle,my_param_collection.incidence_angle);
	descending1=project_to_LOS(e_def1,n_def1,0.0,my_param_collection.descending_flight_angle,my_param_collection.incidence_angle);
	descending2=project_to_LOS(e_def2,n_def2,0.0,my_param_collection.descending_flight_angle,my_param_collection.incidence_angle);
	evaluate_gradients(my_param_collection.point1, my_param_collection.point2, ascending1, ascending2, descending1, descending2);

	return my_interpolated_fields, ascending_LOS_reference, descending_LOS_reference;



def evaluate_gradients(point1, point2, ascending1, ascending2, descending1, descending2):
	mydistance = haversine.distance([point1[1],point1[0]],[point2[1],point2[0]]); 
	print("Gradient in ASCENDING track from point1 to point2: %f mm/yr in %f km " % (np.abs(ascending1-ascending2), mydistance) );
	print("Equal to: %f mm/yr per 100 km \n" % (100*np.abs(ascending1-ascending2)/mydistance) );
	print("Gradient in DESCENDING track from point1 to point2: %f mm/yr in %f km " % (np.abs(descending1-descending2), mydistance) );
	print("Equal to: %f mm/yr per 100 km \n" % (100*np.abs(descending1-descending2)/mydistance) );
	return;



# ---------- PLOTTING OUTPUTS --------------- # 
def outputs(vel_tuple, my_param_collection, ca_border, or_border, my_interpolated_fields, asc_ref, des_ref):

	# Making the plotting variables
	narray_x=np.array(my_interpolated_fields.interp_x);
	narray_y=np.array(my_interpolated_fields.interp_y);
	narray_north=np.array(my_interpolated_fields.interp_north)[:,0];
	narray_east=np.array(my_interpolated_fields.interp_east)[:,0];
	narray_ascend=np.array(my_interpolated_fields.interp_ascend)[:,0];
	narray_descend=np.array(my_interpolated_fields.interp_descend)[:,0];

	# Looking for the max los deformation values, to use for color bars. 
	asc_dataset=narray_ascend-asc_ref;
	des_dataset=narray_descend-des_ref;
	max_ascending_los = np.max(asc_dataset);
	min_ascending_los = np.min(asc_dataset);
	max_descending_los = np.max(des_dataset);
	min_descending_los = np.min(des_dataset);
	max_los_value = np.max([max_descending_los, max_ascending_los]);
	min_los_value = np.min([min_descending_los, min_ascending_los]);


	# Figure of interpolated velocities
	f1=plt.figure();
	ax=f1.add_subplot(1,1,1)
	ax.plot(my_interpolated_fields.interp_x,my_interpolated_fields.interp_y,'.g');
	ax.quiver(my_interpolated_fields.interp_x, my_interpolated_fields.interp_y, my_interpolated_fields.interp_east, my_interpolated_fields.interp_north, color='red',scale=500.0);
	f1 = my_plot_formatting(ax,my_param_collection,ca_border,or_border,"Interpolated GPS Velocity Field",vel_tuple);
	plt.savefig("Interpolated_field.png");
	plt.close();

	# Northward and Eastward velocities in a subplot
	f,axarr=plt.subplots(1,2,figsize=(12,6));
	h1=axarr[0].scatter(narray_x,narray_y,s=75,marker='s',c=narray_north,cmap='jet',edgecolors='face',vmin=-30,vmax=30);
	axarr[0].quiver(narray_x, narray_y, narray_east, narray_north, color='white',scale=500.0);
	my_plot_formatting(axarr[0],my_param_collection,ca_border,or_border,"North Velocity Interpolated from GPS",vel_tuple);
	h2=axarr[1].scatter(narray_x,narray_y,s=75,marker='s',c=narray_east,cmap='jet',edgecolors='face',vmin=-30,vmax=30);
	cbar=plt.colorbar(h1,ax=axarr[1]); cbar.set_label('mm/yr');
	axarr[1].quiver(narray_x, narray_y, narray_east, narray_north, color='white',scale=500.0);
	my_plot_formatting(axarr[1],my_param_collection,ca_border,or_border,"East Velocity Interpolated from GPS",vel_tuple);
	plt.savefig("East_North.png");
	plt.close();

	# ASCENDING AND DESCENDING VIEWING GEOMETRY
	f,axarr=plt.subplots(1,2,figsize=(12,6));
	axarr[0].scatter(narray_x,narray_y,s=75,marker='s',c=asc_dataset,cmap='jet',edgecolors='face',vmin=min_los_value, vmax=max_los_value);
	axarr[0].quiver(narray_x, narray_y, narray_east, narray_north, color='white',scale=500.0);
	quiver_point=[min(my_param_collection.xbounds)+0.4, max(my_param_collection.ybounds)-0.4]
	axarr[0].quiver(quiver_point[0], quiver_point[1],np.cos(np.deg2rad(90-my_param_collection.ascending_flight_angle)),np.sin(np.deg2rad(90-my_param_collection.ascending_flight_angle)),scale=10);
	axarr[0].quiver(quiver_point[0], quiver_point[1],np.sin(np.deg2rad(90-my_param_collection.ascending_flight_angle)),-np.cos(np.deg2rad(90-my_param_collection.ascending_flight_angle)),scale=10,color='red');
	axarr[0].text(quiver_point[0]+0.05,quiver_point[1],"LOS",color='red',ha='right',va='top');
	axarr[0].plot(my_param_collection.point1[0],my_param_collection.point1[1],marker='s',color='black',markersize=5);
	axarr[0].plot(my_param_collection.point2[0],my_param_collection.point2[1],marker='s',color='black',markersize=5);
	axarr[0].plot(my_param_collection.reference_point[0],my_param_collection.reference_point[1],marker='s',color='black',markersize=5);
	my_plot_formatting(axarr[0],my_param_collection,ca_border,or_border,"Ascending GPS LOS Velocity",vel_tuple);
	
	h1=axarr[1].scatter(narray_x,narray_y,s=75,marker='s',c=des_dataset,cmap='jet',edgecolors='face',vmin=min_los_value,vmax=max_los_value);
	cbar=plt.colorbar(h1,ax=axarr[1]); cbar.set_label('mm/yr');
	quiver_point=[min(my_param_collection.xbounds)+0.4, max(my_param_collection.ybounds)-0.4]
	axarr[1].quiver(quiver_point[0], quiver_point[1],np.cos(np.deg2rad(90-my_param_collection.descending_flight_angle)),np.sin(np.deg2rad(90-my_param_collection.descending_flight_angle)),scale=10);
	axarr[1].quiver(quiver_point[0], quiver_point[1],np.sin(np.deg2rad(90-my_param_collection.descending_flight_angle)),-np.cos(np.deg2rad(90-my_param_collection.descending_flight_angle)),scale=10,color='red');
	axarr[1].text(quiver_point[0]+0.05,quiver_point[1],"LOS",color='red',ha='left',va='bottom');
	axarr[1].quiver(narray_x, narray_y, narray_east, narray_north, color='white',scale=500.0);
	axarr[1].plot(my_param_collection.point1[0],my_param_collection.point1[1],marker='s',color='black',markersize=5);
	axarr[1].plot(my_param_collection.point2[0],my_param_collection.point2[1],marker='s',color='black',markersize=5);
	axarr[1].plot(my_param_collection.reference_point[0],my_param_collection.reference_point[1],marker='s',color='black',markersize=5);
	my_plot_formatting(axarr[1],my_param_collection,ca_border,or_border,"Descending LOS Velocity Interpolated from GPS",vel_tuple);

	# The sentinel descending scene. 
	xboxes=[-123.260666, -124.37, -123.98, -122.816429, -123.260666];
	yboxes=[39.701538, 39.86, 41.6, 41.437393, 39.701538];
	axarr[1].plot(xboxes, yboxes,'k');
	plt.savefig("LOS.png");

	return;


def my_plot_formatting(ax,my_param_collection,ca_border,or_border,titlestring,vel_tuple):
	ax.set_xlim(my_param_collection.xbounds);
	ax.set_ylim(my_param_collection.ybounds);
	ax.quiver(vel_tuple.lon, vel_tuple.lat, vel_tuple.evel, vel_tuple.nvel,scale=500.0);
	ax.plot(ca_border[:,0],ca_border[:,1],'k');
	ax.plot(or_border[:,0],or_border[:,1],'k');
	ax.plot(vel_tuple.lon, vel_tuple.lat,'.');
	ax.set_title(titlestring);
	return ax;


def project_to_LOS(U_e,U_n,U_u,flight_angle,incidence_angle):
	# Dlos = [U_n sin(phi) - U_e cos(phi)]*sin(lamda) + U_u cos(lamda)
	# [U_e, U_n, U_u] are the east, north, and up components of the deformation. 
	# phi   = azimuth of satellite heading vector, positive clockwise from north.
	# lamda = local incidence angle at the reflector.
	
	phi=np.deg2rad(flight_angle); 
	lamda=np.deg2rad(incidence_angle);

	if np.size(U_e)>1:  # processing a 1D array of values
		d_los = [0*i for i in U_e];
		for i in range(len(U_e)):
			d_los[i] = ( (U_n[i]*np.sin(phi) - U_e[i]*np.cos(phi) )*np.sin(lamda)  + U_u[i]*np.cos(lamda) );
	else:               # processing a single value
		d_los = (U_n*np.sin(phi) - U_e*np.cos(phi) )*np.sin(lamda)  + U_u*np.cos(lamda) ;

	# Flipping by negative one, because the convention is positive when moving away from the satellite. 
	d_los=np.array(d_los)*-1;

	return d_los


