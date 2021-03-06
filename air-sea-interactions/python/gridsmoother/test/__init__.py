'''
Created on May 8, 2015

@author: hadmm
'''
import unittest, inspect
import numpy as np
import iris
import cf_units
iris.FUTURE.netcdf_no_unlimited = True

CUBE_SHAPE = (72, 96) #N48
SMALL_NUMBER = 1e-15
PLOT = False

def gen_2D_cube_for_testing(data_function_ll, nlat=CUBE_SHAPE[0], nlon=CUBE_SHAPE[1]):
    '''Diven a "data function" build a cube
    
    Arguments:
    
     * data_function_ll:
         function taking arguments latitude, longitude and returning a value to put into the cube
    
    Keywords:
    
     * nlat, nlon:
         shape of the cube. Defaults to CUBE_SHAPE
    
    '''
    
    #build coord points
    dlat = 180. / nlat
    dlon = 360. / nlon
    lat = np.arange(-90. + dlat / 2, 90., dlat)
    lon = np.arange(dlon / 2, 360., dlon)

    #build coords    
    lat_coord = iris.coords.DimCoord(lat, 'latitude', units='degrees')    
    lon_coord = iris.coords.DimCoord(lon, 'longitude', units='degrees')
    lon_coord.circular = True #global
    lon_coord.guess_bounds()
    lat_coord.guess_bounds()
    t_coord = iris.coords.DimCoord([15], 'time', units=cf_units.Unit('days since 1970-01-01 00:00', calendar='360_day'))
    t_coord.bounds = [0, 31]
    
    #generate data    
    if data_function_ll is not None:
        tmp_fn = np.vectorize(data_function_ll)
        data = tmp_fn(*np.meshgrid(lat, lon, indexing='ij'))
    else:
        data = np.zeros((nlat,nlon))
    
    #construct cube
    testcube = iris.cube.Cube(data,
                              dim_coords_and_dims=[(lat_coord, 0), (lon_coord, 1)],
                              aux_coords_and_dims=[(t_coord, None)]
                              )
    
    return testcube
    
def angular_separation(lat1, lon1, lat2, lon2):
    '''Return angular separation of two points in degrees
    
    Arguments:
    
     * lat1,lon1:
         latitude and longitude of first point
         
     * lat2,lon2:
         latitude and longitude of second point
         
    '''
    rlat1 = np.deg2rad(lat1)
    rlat2 = np.deg2rad(lat2)
    rdlon = np.deg2rad(lon1 - lon2)
    
    calpha = np.cos(rlat1) * np.cos(rlat2) * np.cos(rdlon) + np.sin(rlat1) * np.sin(rlat2)
    return np.rad2deg(np.arccos(calpha.clip(-1., 1.)))
    

def gen_or_load_2D(filename, data_functions, names, params={}, units='1', **kwargs):
    '''load data from filename if it exists, otherwise generate data and save it
    
    Arguments:
    
     * filename:
         name of file to load from or write to

     * data_functions:
         list of functions to use to create 2D cubes

     * names:
         list of names to give each cube
    
    
    
    '''
    import os
    if not os.path.exists(filename):
        cubes = iris.cube.CubeList()
        for data_function, name in zip(data_functions, names):
            cube = gen_2D_cube_for_testing(data_function, **kwargs)
            cube.long_name = name
            cube.units = units
            cube.attributes.update(params)
            cubes.append(cube)
        iris.save(cubes, filename)    
    else:
        cubes = iris.load_cubes(filename, names)
        for cube in cubes: 
            assert params == register_params(cube.attributes)
            #assert cube.shape == CUBE_SHAPE
        
    return cubes

def register_params(variables):
    '''when given vars() or return a dictionary of all the JET constants'''
    return dict(filter(lambda (k, v): 'GS' in k, variables.items()))

def test_single_point(target_point, tmpfile, source_data_function, num_expected_distinct_values=2):
    '''Smooth a single point'''
    
    import iris.quickplot as qplt, matplotlib.pyplot as plt
    from gridsmoother import GridSmoother
    
    import os

    #lat,lon = target_point

    dlat = 180. / CUBE_SHAPE[0]
    dlon = 360. / CUBE_SHAPE[1]

    print "point lat = %s, lon = %s" % target_point

    assert int(target_point[0] / dlat) - target_point[0] / dlat < SMALL_NUMBER
    assert int(target_point[1] / dlon) - target_point[1] / dlon < SMALL_NUMBER
    
    print "dlat = %s, dlon = %s" % (dlat, dlon)
    
    #centre = (lat,lon)#(dlat / 2., dlon / 2.)
    source_cube = gen_or_load_2D(tmpfile , [source_data_function], ["unsmoothed data"], {"GS_centre_lat":target_point[0], 'GS_centre_lon':target_point[1]})[0]
    
    for smoothing_width in np.arange(2.0, 5, 0.5) * dlat:
        print "smoothing_width: ", smoothing_width
        
        gs = GridSmoother()
        filename = 'smoothing_%s.json.gz' % smoothing_width
        
        smoothing_function = lambda s: (s <= smoothing_width) * 1.0
        if os.path.exists(filename):
            gs.load(filename)
        else:
            gs.build(source_cube, smoothing_function)
            gs.save('smoothing_%s.json.gz' % smoothing_width)

        smoothed_cube = gs.smooth_2d_cube(source_cube)
        
        assert np.isclose(smoothed_cube.data.sum(), source_cube.data.sum(), atol=SMALL_NUMBER)

        #will fail for smoothing functions other than a hard cut off:
        if num_expected_distinct_values is not None:
            assert len(set(smoothed_cube.data.ravel().tolist())) == num_expected_distinct_values
        
        for i, j in zip(*np.where(smoothed_cube.data > 0.0)):
            assert smoothing_function(angular_separation(source_cube.coord('latitude').points[i],
                                                         source_cube.coord('longitude').points[j],
                                                         *target_point)
                                      ) > 0.
        
        for i, j in zip(*np.where(smoothed_cube.data == 0.0)):
            assert smoothing_function(angular_separation(source_cube.coord('latitude').points[i],
                                                         source_cube.coord('longitude').points[j],
                                                         *target_point)
                                      ) == 0.
        
        if PLOT:
            import cartopy.crs as ccrs
            fig = plt.figure()
            subpl = fig.add_subplot(111, projection=ccrs.PlateCarree())
        
            qplt.pcolormesh(smoothed_cube, cmap='Reds')
            qplt.outline(smoothed_cube)
            subpl.add_artist(plt.Circle(target_point, smoothing_width, edgecolor='blue', facecolor='none', transform=ccrs.PlateCarree()))
            
            for i, lat in enumerate(smoothed_cube.coord('latitude').points):
                for j, lon in enumerate(smoothed_cube.coord('longitude').points):
                    if smoothed_cube.data[i, j] > 0:
                        plt.text(lon, lat, smoothed_cube.data[i, j] ** -1, transform=ccrs.PlateCarree(), ha='center', va='center')
            
            qplt.plt.gca().coastlines()
            qplt.show()


def test_area(tmpfile, source_data_function):
    '''Smooth a single point'''
    
    import iris.quickplot as qplt, matplotlib.pyplot as plt
    from gridsmoother import GridSmoother
    import itertools
    import os

    #lat,lon = target_point
    
    dlat = 180. / CUBE_SHAPE[0]
    dlon = 360. / CUBE_SHAPE[1]
    lats = np.arange(-90. + dlat/2, 90., dlat)
    lons = np.arange(dlon/2,       360., dlon)
    
    source_points = []
    for lat,lon in itertools.product(lats, lons):
        if source_data_function(lat,lon) > 0:
            source_points.append((lat,lon))
    
    source_cubes = iris.cube.CubeList()
    for target_point in source_points:
        source_cube = gen_2D_cube_for_testing(None, CUBE_SHAPE[0], CUBE_SHAPE[1])
        target_index = (np.where(target_point[0] == lats)[0][0],
                        np.where(target_point[1] == lons)[0][0])
        source_cube.data[target_index] = 1.0
        source_cubes.append(source_cube)
    
    sum_cube = gen_2D_cube_for_testing(source_data_function, CUBE_SHAPE[0], CUBE_SHAPE[1]) 
    
    for smoothing_width in np.arange(2.0, 5, 0.5) * dlat:
        print "smoothing_width: ", smoothing_width
        
        gs = GridSmoother()
        filename = 'smoothing_%s.json.gz' % smoothing_width
        
        smoothing_function = lambda s: (s <= smoothing_width) * 1.0
        if os.path.exists(filename):
            gs.load(filename)
        else:
            gs.build(source_cube, smoothing_function)
            gs.save('smoothing_%s.json.gz' % smoothing_width)

        smoothed_sum_cube = gs.smooth_2d_cube(sum_cube)
        
        smoothed_cubes = iris.cube.CubeList([gs.smooth_2d_cube(s) for s in source_cubes])
        
        assert (smoothed_sum_cube.data - sum(smoothed_cubes).data).max() < SMALL_NUMBER
        
def test_boxcar_area(tmpfile, source_data_function):
    '''Smooth a single point'''
    
    import iris.quickplot as qplt, matplotlib.pyplot as plt
    from gridsmoother import GridSmoother
    import itertools
    import os

    #lat,lon = target_point
    
    dlat = 180. / CUBE_SHAPE[0]
    dlon = 360. / CUBE_SHAPE[1]
    lats = np.arange(-90. + dlat/2, 90., dlat)
    lons = np.arange(dlon/2,       360., dlon)
    
    source_points = []
    for lat,lon in itertools.product(lats, lons):
        if source_data_function(lat,lon) > 0:
            source_points.append((lat,lon))
    
    source_cubes = iris.cube.CubeList()
    for target_point in source_points:
        source_cube = gen_2D_cube_for_testing(None, CUBE_SHAPE[0], CUBE_SHAPE[1])
        target_index = (np.where(target_point[0] == lats)[0][0],
                        np.where(target_point[1] == lons)[0][0])
        source_cube.data[target_index] = 1.0
        source_cubes.append(source_cube)
    
    sum_cube = gen_2D_cube_for_testing(source_data_function, CUBE_SHAPE[0], CUBE_SHAPE[1]) 
    
    for smoothing_width in np.arange(5, 25,5,):
        print "smoothing_width: ", smoothing_width
        
        gs = GridSmoother()
        filename = 'boxcar_%s.json.gz' % smoothing_width
        
        if os.path.exists(filename):
            gs.load(filename)
        else:
            gs.build_boxcar_lat_lon(sum_cube,smoothing_width*2, smoothing_width)#(source_cube, smoothing_function)
            gs.save('boxcar_%s.json.gz' % smoothing_width)

        smoothed_sum_cube = gs.smooth_2d_cube(sum_cube)
        
        smoothed_cubes = iris.cube.CubeList([gs.smooth_2d_cube(s) for s in source_cubes])
        
        assert (smoothed_sum_cube.data - sum(smoothed_cubes).data).max() < SMALL_NUMBER

        
def test_single_boxcar(target_point, tmpfile, source_data_function):
    '''Smooth a single point'''
    
    import iris.quickplot as qplt, matplotlib.pyplot as plt
    from gridsmoother import GridSmoother
    
    import os

    #lat,lon = target_point

    dlat = 180. / 1#CUBE_SHAPE[0]
    dlon = 360. / 1#CUBE_SHAPE[1]

    print "point lat = %s, lon = %s" % target_point

    assert int(target_point[0] / dlat) - target_point[0] / dlat < SMALL_NUMBER
    assert int(target_point[1] / dlon) - target_point[1] / dlon < SMALL_NUMBER
    
    print "dlat = %s, dlon = %s" % (dlat, dlon)
    
    #centre = (lat,lon)#(dlat / 2., dlon / 2.)
    source_cube = gen_or_load_2D(tmpfile , [source_data_function], ["unsmoothed data"], {"GS_centre_lat":target_point[0], 'GS_centre_lon':target_point[1]},nlat=180, nlon=360)[0]
    
    lat_width = 6.
    lon_width = 18.
    
    print "box car parameters: lat_width %s, lon_width %s" % (lat_width, lon_width)
    
    gs = GridSmoother()
    filename= "boxcar_%s_x_%s.json.gz" % (lon_width,lat_width)
    if os.path.exists(filename):
        gs.load(filename)
    else:
        gs.build_boxcar_lat_lon(source_cube, lat_width, lon_width)
        gs.save(filename)
    
    smoothed_cube = gs.smooth_2d_cube(source_cube)
               
    if PLOT:
        import cartopy.crs as ccrs
        fig = plt.figure()
        subpl = fig.add_subplot(111, projection=ccrs.PlateCarree())
    
        qplt.pcolormesh(smoothed_cube, cmap='Reds')
        qplt.outline(smoothed_cube)
#        subpl.add_artist(plt.Circle(target_point, smoothing_width, edgecolor='blue', facecolor='none', transform=ccrs.PlateCarree()))
        
        for i, lat in enumerate(smoothed_cube.coord('latitude').points):
            for j, lon in enumerate(smoothed_cube.coord('longitude').points):
                if smoothed_cube.data[i, j] > 0:
                    plt.text(lon, lat, smoothed_cube.data[i, j] ** -1, transform=ccrs.PlateCarree(), ha='center', va='center')
        
        qplt.plt.gca().coastlines()
        qplt.show()


class Test(unittest.TestCase):

    def testpoint_equator(self):
        dlat = 180. / CUBE_SHAPE[0]
        dlon = 360. / CUBE_SHAPE[1]
        
        target_point = (dlat/2, dlon/2)
        
        def _source_data_function(lat, lon):
            if abs(lat - target_point[0]) < dlat/2 and abs(lon - target_point[1]) < dlon/2:
                return 1.0
            return 0.0
    
        tmpfile = inspect.currentframe().f_code.co_name + ".nc"
        test_single_point(target_point, tmpfile, _source_data_function)
    
    def testarea_equator(self):
        dlat = 180. / CUBE_SHAPE[0]
        dlon = 360. / CUBE_SHAPE[1]
        
        target_point = (dlat/2, dlon/2)
        
        def _source_data_function(lat, lon):
            if abs(lat - target_point[0]) < 3*dlat/2 and abs(lon - target_point[1]) < 3*dlon/2:
                return 1.0
            return 0.0
    
        tmpfile = inspect.currentframe().f_code.co_name + ".nc"
        test_area(tmpfile, _source_data_function)
        
    def testarea_pole(self):
        dlat = 180. / CUBE_SHAPE[0]
        dlon = 360. / CUBE_SHAPE[1]
        
        target_point = (90-dlat/2, dlon/2)
        
        def _source_data_function(lat, lon):
            if abs(lat - target_point[0]) < 8*dlat/2 and abs(lon - target_point[1]) < 8*dlon/2:
                return 1.0
            return 0.0
    
        tmpfile = inspect.currentframe().f_code.co_name + ".nc"
        test_area(tmpfile, _source_data_function)
    
    
    def testpoint_equator_boxcar(self):
        dlat = 180. / 180#CUBE_SHAPE[0]
        dlon = 360. / 360#CUBE_SHAPE[1]
        
        target_point = (dlat/2, dlon/2)
        
        def _source_data_function(lat, lon):
            if abs(lat - target_point[0]) < dlat/2 and abs(lon - target_point[1]) < dlon/2:
                return 1.0
            return 0.0
        
        tmpfile = inspect.currentframe().f_code.co_name + ".nc"
        test_single_boxcar(target_point, tmpfile, _source_data_function)
        
    def testarea_equator_boxcar(self):
        dlat = 180. / 180#CUBE_SHAPE[0]
        dlon = 360. / 360#CUBE_SHAPE[1]
        
        target_point = (dlat/2, dlon/2)
        
        def _source_data_function(lat, lon):
            if abs(lat - target_point[0]) < 8*dlat/2 and abs(lon - target_point[1]) < 8* dlon/2:
                return 1.0
            return 0.0
        
        tmpfile = inspect.currentframe().f_code.co_name + ".nc"
        test_boxcar_area(tmpfile, _source_data_function)
    
    def testpoint_pole(self):
        dlat = 180. / CUBE_SHAPE[0]
        dlon = 360. / CUBE_SHAPE[1]
            
        target_point = (90.-dlat/2, dlon/2)
        
        def _source_data_function(lat, lon):
            if abs(lat - target_point[0]) < dlat/2 and abs(lon - target_point[1]) < dlon/2:
                return 1.0
            return 0.0
    
        tmpfile = inspect.currentframe().f_code.co_name + ".nc"
        test_single_point(target_point, tmpfile, _source_data_function)
        
    def testpoint_pole_boxcar(self):
        dlat = 180. / 180#CUBE_SHAPE[0]
        dlon = 360. / 360#CUBE_SHAPE[1]
        
        target_point = (90.-dlat/2, dlon/2)
        
        def _source_data_function(lat, lon):
            if abs(lat - target_point[0]) < dlat/2 and abs(lon - target_point[1]) < dlon/2:
                return 1.0
            return 0.0
        
        tmpfile = inspect.currentframe().f_code.co_name + ".nc"
        test_single_boxcar(target_point, tmpfile, _source_data_function)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
