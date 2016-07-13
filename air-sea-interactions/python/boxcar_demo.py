'''
Created on Jul 15, 2015

@author: Matthew Mizielinski
'''
import iris, os
import iris.quickplot as qplt
import matplotlib.pyplot as plt
plt.rcParams['image.cmap']='RdBu_r'
import gridsmoother
import numpy as np 

lat_width = 6.
lon_width = 18.
    
if __name__ == '__main__':
    N216data = "gridsmoother/data/sst_masked.nc"
    sst_field = iris.load_cube(N216data, 'surface_temperature')

    print "box car parameters: lat_width %s, lon_width %s" % (lat_width, lon_width)
    
    gs = gridsmoother.GridSmoother()
    filename= "boxcar_%s_x_%s.json.gz" % (lon_width,lat_width)
    if os.path.exists(filename):
        print 'read existing file ',filename
        gs.load(filename)
    else:
        gs.build_boxcar_lat_lon(sst_field[0], lat_width, lon_width)
        gs.save(filename)
    
    smoothed_cube_masked = gs.smooth_3d_cube(sst_field, masked = True)
    anomaly_cube_masked = sst_field - smoothed_cube_masked

    if not os.path.exists('data_out'): os.makedirs('data_out')
    iris.save(anomaly_cube_masked ,'data_out/anomaly_masked.nc')

    reference_anomaly = iris.load_cube('gridsmoother/data_ref/anomaly_masked.nc')
    difference_from_ref = reference_anomaly - anomaly_cube_masked
    iris.save(difference_from_ref, './data_out/difference_from_ref.nc')


    fig = plt.figure()
    
    for i,cube in enumerate([sst_field[0], smoothed_cube_masked, anomaly_cube_masked[0]]):   
        print 'cube ',cube
        vmax = cube.data.max()
        vmin = cube.data.min()
        subpl = fig.add_subplot(221+i)
        qplt.pcolormesh(cube, vmin=vmin, vmax = vmax)
        plt.gca().coastlines()
    
    plt.show()
