# Python viewing to see the Mendocino stations

# Step 1: Determine the stations in the radius. 
# Step 2: Read them in. Make a list of timeseries objects in one large dataobject. 
# Step 3: Compute: Remove outliers, earthquakes, and eventually trend from the data. 
# Step 4: Plot in order of increasing latitude, colored by how close they are to the earthquake. 

# Reference: 
# Timeseries = collections.namedtuple("Timeseries",['name','coords','dtarray','dN', 'dE','dU','Sn','Se','Su','EQtimes']);  # in mm

import numpy as np 
import matplotlib.pyplot as plt 
import matplotlib
import matplotlib.cm as cm
import collections
import datetime as dt 
import gps_io_functions
import gps_input_pipeline
import gps_ts_functions
import gps_seasonal_removals
import stations_within_radius
import offsets


def driver():
	[stations, distances, EQtime] = configure();
	[dataobj_list, offsetobj_list, eqobj_list] = inputs(stations);
	[detrended_objects, stage1_objects, stage2_objects, sorted_distances, east_slope_obj] = compute(dataobj_list, offsetobj_list, eqobj_list, distances, EQtime);
	
	output_full_ts(detrended_objects, sorted_distances, EQtime, "detrended", east_slope_obj);
	output_full_ts(stage1_objects, sorted_distances, EQtime, "noeq", east_slope_obj);
	output_full_ts(stage2_objects, sorted_distances, EQtime, "noeq_noseasons", east_slope_obj);
	return;


def configure():
	EQcoords=[-125.134, 40.829]; # The March 10, 2014 M6.8 earthquake
	EQtime  = dt.datetime.strptime("20140310", "%Y%m%d");
	radius=125;  # km. 
	stations, distances = stations_within_radius.get_stations_within_radius(EQcoords, radius);
	blacklist=["P316","P170","P158","TRND"];
	stations_new=[]; distances_new=[];
	for i in range(len(stations)):
		if stations[i] not in blacklist:
			stations_new.append(stations[i]);
			distances_new.append(distances[i]);
	return [stations_new, distances_new, EQtime];


def inputs(station_names):
	dataobj_list=[]; offsetobj_list=[]; eqobj_list=[];
	for station_name in station_names:
		[myData, offset_obj, eq_obj] = gps_input_pipeline.get_station_data(station_name, 'pbo');
		dataobj_list.append(myData);
		offsetobj_list.append(offset_obj);
		eqobj_list.append(eq_obj);	
	return [dataobj_list, offsetobj_list, eqobj_list];


def compute(dataobj_list, offsetobj_list, eqobj_list, distances, EQtime):

	latitudes_list=[i.coords[1] for i in dataobj_list];
	sorted_objects = [x for _,x in sorted(zip(latitudes_list, dataobj_list))];  # the raw, sorted data. 
	sorted_offsets = [x for _,x in sorted(zip(latitudes_list, offsetobj_list))];  # the raw, sorted data. 
	sorted_eqs = [x for _,x in sorted(zip(latitudes_list, eqobj_list))];  # the raw, sorted data. 
	sorted_distances = [x for _,x in sorted(zip(latitudes_list, distances))];  # the sorted distances.

	# Detrended objects
	detrended_objects=[];
	for i in range(len(sorted_objects)):
		newobj=gps_seasonal_removals.make_detrended_ts(sorted_objects[i], 0, 'lssq');
		detrended_objects.append(newobj);

	# Objects with no earthquakes or seasonals
	stage1_objects = [];
	stage2_objects = [];
	east_slope_obj=[];
	for i in range(len(dataobj_list)):
		# Remove the steps earthquakes
		newobj=offsets.remove_antenna_offsets(sorted_objects[i], sorted_offsets[i]);
		newobj=offsets.remove_earthquakes(newobj,sorted_eqs[i]);

		# The detrended TS without earthquakes
		stage1obj=gps_seasonal_removals.make_detrended_ts(newobj, 0, 'lssq');
		stage1_objects.append(stage1obj);

		# The detrended TS without earthquakes or seasonals
		stage2obj=gps_seasonal_removals.make_detrended_ts(newobj, 1, 'lssq');
		stage2_objects.append(stage2obj);

		# Get the pre-event and post-event velocities (earthquakes removed)
		[east_slope_before, north_slope_before, vert_slope_before, _, _, _]=gps_ts_functions.get_slope(stage2obj,endtime=EQtime);
		[east_slope_after, north_slope_after, vert_slope_after, _, _, _]=gps_ts_functions.get_slope(stage2obj,starttime=EQtime);
		east_slope_after=np.round(east_slope_after,decimals=1);
		east_slope_before=np.round(east_slope_before,decimals=1);
		east_slope_obj.append([east_slope_before, east_slope_after]);

	return [detrended_objects, stage1_objects, stage2_objects, sorted_distances, east_slope_obj];




def output_full_ts(dataobj_list, distances, EQtime, filename, east_slope_obj):

	# plt.figure(figsize=(20,15),dpi=160);
	[f,axarr]=plt.subplots(1,2,sharex=True,sharey=True,figsize=(10,8))
	label_date=dt.datetime.strptime("20181230","%Y%m%d");
	start_time_plot=dt.datetime.strptime("20050101","%Y%m%d");
	end_time_plot=dt.datetime.strptime("20181208", "%Y%m%d");

	EQ1time = dt.datetime.strptime("20050615", "%Y%m%d");  # other earthquakes added to the figure
	EQ2time = dt.datetime.strptime("20100110", "%Y%m%d");
	EQ3time = dt.datetime.strptime("20161208", "%Y%m%d");
	offset=0;
	spacing=10;
	closest_station=70;  # km from event
	farthest_station=120; # km from event
	color_boundary_object=matplotlib.colors.Normalize(vmin=closest_station,vmax=farthest_station, clip=True);
	custom_cmap = cm.ScalarMappable(norm=color_boundary_object,cmap='jet_r');

	# East
	for i in range(len(dataobj_list)):
		offset=spacing*i;
		edata=dataobj_list[i].dE;
		edata=[x + offset for x in edata];
		line_color=custom_cmap.to_rgba(distances[i]);
		l1 = axarr[0].plot_date(dataobj_list[i].dtarray,edata,marker='+',markersize=1.5,color=line_color);
		axarr[0].text(label_date,offset,dataobj_list[i].name,fontsize=9,color=line_color);
		# axarr[0].text(dt.datetime.strptime("20050301", "%Y%m%d"),offset,east_slope_obj[i][0],fontsize=9,color='k');
		# axarr[0].text(EQtime,offset,east_slope_obj[i][1],fontsize=9,color='k');
	axarr[0].set_xlim(start_time_plot,end_time_plot);
	axarr[0].set_ylim([-10,offset+10])
	bottom,top=axarr[0].get_ylim();
	axarr[0].plot_date([EQtime, EQtime], [bottom, top], '--k');	
	axarr[0].plot_date([EQ1time, EQ1time], [bottom, top], '--k');
	axarr[0].plot_date([EQ2time, EQ2time], [bottom, top], '--k');
	axarr[0].plot_date([EQ3time, EQ3time], [bottom, top], '--k');
	axarr[0].set_ylabel("East (mm)");
	axarr[0].set_title("East GPS Time Series")
	axarr[0].grid(True)

	# North
	for i in range(len(dataobj_list)):
		offset=spacing*i;
		ndata=dataobj_list[i].dN;
		ndata=[x + offset for x in ndata];
		line_color=custom_cmap.to_rgba(distances[i]);
		l1 = axarr[1].plot_date(dataobj_list[i].dtarray,ndata,marker='+',markersize=1.5, color=line_color);
	axarr[1].set_xlim(start_time_plot,end_time_plot);
	axarr[1].set_ylim([-10,offset+10])
	bottom,top=axarr[1].get_ylim();
	axarr[1].plot_date([EQtime, EQtime], [bottom, top], '--k');	
	axarr[1].plot_date([EQ1time, EQ1time], [bottom, top], '--k');
	axarr[1].plot_date([EQ2time, EQ2time], [bottom, top], '--k');
	axarr[1].plot_date([EQ3time, EQ3time], [bottom, top], '--k');
	axarr[1].set_ylabel("North (mm)");
	axarr[1].set_title("North GPS Time Series")
	axarr[1].grid(True)
	custom_cmap.set_array(range(closest_station,farthest_station))
	cb = plt.colorbar(custom_cmap);
	cb.set_label('Kilometers from 2014 Earthquake');
	plt.savefig('Mend_Collective_TS_'+filename+'.jpg')	
	plt.close();


	return;




