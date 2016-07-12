import sys
sys.path.append('/home/h03/hadmm/workspace')

import numpy as np
import iris
from gridsmoother import GridSmoother
import cartopy.crs as ccrs
import iris.analysis.cartography as iac
import matplotlib.pyplot as plt
import iris.quickplot as qplt



    
def main():
    import os#, sys

    #smoothing_width = float(sys.argv[1])
    #resolution = int(sys.argv[2])

    smoothing_width = 10.
    resolution = 48


    dlat = 180. / int(resolution*1.5)
    lat_p = np.arange(-90.+dlat/2, 90., dlat)

    dlon = 360. / int(resolution*2)
    lon_p = np.arange(dlon/2, 360.,dlon)

    lat = iris.coords.DimCoord(lat_p, 'latitude',  units = 'degrees')
    lon = iris.coords.DimCoord(lon_p, 'longitude', units = 'degrees')
    data = np.empty((len(lat_p),len(lon_p)))

    source_cube = iris.cube.Cube(data, dim_coords_and_dims = [(lat,0),(lon,1)])

#    smoothing_width = 2.
#    fn = lambda x: np.exp(-x**2 / (2. *smoothing_width**2))

    fn = lambda x: (x <= smoothing_width) * 1.0
    gs = GridSmoother()
    
    filename = "simple_%s_grid_smoother_%s_%s.json.gz" %(smoothing_width,dlat,dlon)

    if os.path.exists(filename):
        print "loading ", filename
        gs.load(filename)
    else:
        print "generating smoother for %sx%s (lat x lon) degree source grid" %(dlat,dlon)
        gs.build(source_cube, fn, quiet=False, metadata={'source_grid':"N48","smoothing radius":smoothing_width})
        print "saving to ", filename
        gs.save(filename)

    print "filling test cube with data"
    source_cube.data.fill(0)
    source_cube.long_name = "Source data"
    for i,ilat in enumerate(lat_p):
        for j,jlon in enumerate(lon_p):
            R = np.sqrt((ilat-0)**2 + (jlon-60.)**2)
            if R > 20 and R < 25:
                source_cube.data[i,j] = 10
    
    tmpcube, extent = iac.project(source_cube, ccrs.RotatedPole(90, 20))
    source_cube.data = tmpcube.data + tmpcube.data[:, ::-1]
    
    for i,ilat in enumerate(lat_p):
        for j,jlon in enumerate(lon_p):
            if 17.5 <= ilat <= 22.5 and (jlon < 60 or jlon > 300):
                source_cube.data[i,j] = 10

    print "smoothing test cube"
    result_cube = gs.smooth_2d_cube(source_cube)
    result_cube.long_name = "Smoothed data"
    print "plotting"
    
    
    proj = ccrs.Orthographic(0,65)
    #proj = ccrs.PlateCarree()
    fig = plt.figure()
    s = fig.add_subplot(121, projection=proj)
    qplt.pcolormesh(source_cube, cmap='Greens')
    s.set_global()
    s.gridlines()
    plt.gca().coastlines()
    r = fig.add_subplot(122, projection= proj)
    qplt.pcolormesh(result_cube,cmap='Blues')
    r.set_global()
    r.gridlines()
    plt.gca().coastlines()
#    plt.savefig(filename[:-8]+".png")
    plt.show()

if __name__ == "__main__":
    main()