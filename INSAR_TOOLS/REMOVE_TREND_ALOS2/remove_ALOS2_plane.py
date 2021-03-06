# Little function that removes trend from unwrapped grd file (give it the order of coefficients in the plane)
# and makes KML files. Yay! 

from subprocess import call

def remove_trend2d(grdname, order):

    order=str(order)
    call(["gmt","grd2xyz",grdname,"-s",">","unwrap_mask_ll.xyz"]);  # make xyz file with no NaNs in it.  

    # Trend fitting: Get the residuals and the planar model
    call(["gmt","trend2d","unwrap_mask_ll.xyz","-Fxyr","-N"+order,"-V",">","detrended_unwrapped.xyz"])
    call(["gmt","trend2d","unwrap_mask_ll.xyz","-Fxym","-N"+order,"-V",">","planar_model_N"+order+".xyz"])

    # Convert to grd output files for plotting
    call(["gmt xyz2grd planar_model_N"+order+".xyz -Gplanar_model_N"+order+".grd `gmt grdinfo -I "+grdname+"` `gmt grdinfo -I- "+grdname+"`"],shell=True);
    call(["gmt xyz2grd detrended_unwrapped.xyz -Gdetrended_unwrapped_N"+order+".grd `gmt grdinfo -I "+grdname+"` `gmt grdinfo -I- "+grdname+"`"],shell=True);

    # kml plotting with a certain color bar. 
    call(["gmt","makecpt","-T-2.5/2.5/0.1","-Z","-Cpolar",">","mycpt.cpt"]);
    call(["grd2kml.csh","detrended_unwrapped_N"+order,"mycpt.cpt"])
    call(["grd2kml.csh","planar_model_N"+order,"mycpt.cpt"])


if __name__=="__main__":
	grdname="unwrap_mask_ll.grd"
	remove_trend2d(grdname,4);
	remove_trend2d(grdname,3);
	remove_trend2d(grdname,6);



