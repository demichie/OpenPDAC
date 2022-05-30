import vtk
import os
import sys
from vtk.numpy_interface import dataset_adapter as dsa
from vtk.util import numpy_support
import numpy as np
from numpy import linalg as LA
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde
from linecache import getline
import pandas as pd
sys.path.insert(0,'./preprocessing')
from preprocessing.ASCtoSTLdict import *
from matplotlib.colors import LightSource
from matplotlib.colors import BoundaryNorm
import matplotlib.ticker as ticker

def fmt(x, pos):
    a, b = '{:.2e}'.format(x).split('e')
    b = int(b)
    return r'${} \times 10^{{{}}}$'.format(a, b)

def readerVTK(filename):

    reader = vtk.vtkDataSetReader() 

    reader.SetFileName(filename)
    reader.ReadAllScalarsOn()
    reader.ReadAllVectorsOn()
    reader.ReadAllTensorsOn()
    reader.ReadAllFieldsOn()
    reader.Update()

    mydata = dsa.WrapDataObject(reader.GetOutput())
   
    origId = np.array(mydata.PointData['origId']).astype(int)
    ImpCpuId = mydata.PointData['lmpCpuId']
    rho = mydata.PointData['rho']
    d = mydata.PointData['d']
    U = mydata.PointData['U']

    Point_coordinates = reader.GetOutput().GetPoints().GetData()
    position = numpy_support.vtk_to_numpy(Point_coordinates)

    #print(d)
    #print(U)
    #print(position)
    #print(rho)
    #print(origId)

    return origId , d, U, position, rho


def readASC(DEM_file,xc,yc):

    print('Reading DEM file: ' + DEM_file)
    # Parse the topography header
    hdr = [getline(DEM_file, i) for i in range(1, 7)]
    values = [float(h.split()[-1].strip()) for h in hdr]
    cols, rows, lx, ly, cell, nd = values
    cols = int(cols)
    rows = int(rows)

    xs_DEM = lx + 0.5 * cell + np.linspace(0, (cols - 1) * cell, cols)
    ys_DEM = ly + 0.5 * cell + np.linspace(0, (rows - 1) * cell, rows)

    extent = lx, lx + cols * cell, ly, ly + rows * cell

    # Load the topography into a numpy array
    DEM = pd.read_table(DEM_file, delim_whitespace=True, header=None,
                    skiprows=6).astype(float).values
    DEM = np.flipud(DEM)
    DEM[DEM == nd] = 0.0

    xinit = np.linspace(0, (cols - 1) * cell, cols) - xc
    yinit = np.linspace(0, (rows - 1) * cell, rows) - yc

    xinit = xs_DEM - xc
    yinit = ys_DEM - yc

    xmin = np.amin(xinit)
    xmax = np.amax(xinit)

    print('xmin,xmax',xmin,xmax)

    ymin = np.amin(yinit)
    ymax = np.amax(yinit)

    print('ymin,ymax',ymin,ymax)

    Xinit, Yinit = np.meshgrid(xinit, yinit)
    Zinit = DEM
   
    return Xinit,Yinit,Zinit,cell,extent


def main():

    print('DEM_file',DEM_file)
    filename = './preprocessing/'+DEM_file
    Xinit,Yinit,Zinit,cell,extent = readASC(filename,xc,yc)
 
 
    ls = LightSource(azdeg=45, altdeg=45)

    
    # plt.xlim([plt_xmin, plt_xmax])
    # plt.ylim([plt_ymin, plt_ymax])

    
    current_dir = os.getcwd()
    working_dir = current_dir+'/VTK/lagrangian/cloud'
    files = os.listdir(working_dir)
    n_files = len(files)
    file_idx = []
    for filename in files:
        # print(filename)
        file_idx.append(int(filename.split('_')[1].split('.')[0]))
        
        
    sorted_files = [files[i] for i in np.argsort(file_idx)]
    # print(sorted_files)

    full_filename = working_dir+'/'+sorted_files[1]

    origId,d, U, position, rho = readerVTK(full_filename)

    diams = np.unique(d)
    
    nballistics = d.shape[0]
    n_times = n_files-1
    print('nballistics',nballistics)
    A = np.zeros((nballistics,3,n_times))
    B = np.zeros((nballistics,3,n_times))
    matr = np.zeros((n_times,8,nballistics))
    
    for i,filename in enumerate(sorted_files[-1:]):
    
        full_filename = working_dir+'/'+filename
        print(full_filename)
        origId,d, U, position, rho = readerVTK(full_filename)
        A[:,:,i] = U
        B[:,:,i] = position
        for k in range(nballistics):
            matr[i,1:4,k] = B[k,:,i]
            matr[i,4:7,k] = A[k,:,i]
            matr[i,7,k] = LA.norm(matr[i,4:7,k])
    

    x = np.array(position[:,0]) 
    y = np.array(position[:,1]) 
    diam = np.array(d)

    xy = np.vstack([x,y])
    kde = gaussian_kde(xy,bw_method=1.0)
    z = gaussian_kde(xy)(xy)
    step_dens = 50.0
    x_density = np.arange(np.amin(Xinit),np.amax(Xinit),step=step_dens)
    y_density = np.arange(np.amin(Yinit),np.amax(Yinit),step=step_dens)

    x_dens_min = xc+np.amin(x_density)
    x_dens_max = xc+np.amax(x_density)
    y_dens_min = yc+np.amin(y_density)
    y_dens_max = yc+np.amax(y_density)
    

    extent_density = x_dens_min , x_dens_max , y_dens_min , y_dens_max

    xx,yy = np.meshgrid(x_density,y_density)
    
    count_ballistic_class = np.zeros((len(diams)+1,xx.shape[0],xx.shape[1]))
    zz = np.zeros_like(xx)
    
    for xi,yi,di in zip(x,y,diam):
    
        i = ( xi + xc - x_dens_min ) / step_dens
        j = ( yi + yc - y_dens_min ) / step_dens

        i = int(np.ceil(i))		
        j = int(np.ceil(j))
        
        
        count_ballistic_class[-1,j,i] +=1        
        k = int(np.argwhere(di==diams)[0]) 
        count_ballistic_class[k,j,i] +=1        
        
 
    for i in range(len(diams)+1):
     
        fig, ax = plt.subplots()
    
        im = ax.imshow(ls.hillshade(np.flipud(Zinit),vert_exag=1.0,
                     dx=cell,dy=cell),cmap='gray',extent=extent)
        
        ax.set_aspect('equal', 'box')
   
        zz[:,:] = np.squeeze(count_ballistic_class[i,:,:])
        sum_zz = np.nansum(zz)
        print('sum_zz',sum_zz)
        zz = zz / np.sum(zz) * 100.0
        zz = np.log10(zz)   
    
        min_arr = np.amin(zz)
        max_arr = np.amin(zz)
    
        zz_max = np.amax(zz)
        zz_linspace = np.linspace(0,zz_max,num=11)
        ticks = []
        for val in zz_linspace:
            ticks.append(str(val))
    
        im_ratio = Xinit.shape[0] / Xinit.shape[1]
           
        levels = np.linspace(min_arr, max_arr, 11)
        label_str = 'Probabilty [0;1]'

        cmap = plt.get_cmap('terrain_r')
        norm = BoundaryNorm(levels, ncolors=cmap.N, clip=True)
       
        # ax.scatter(x+xc,y+yc,c=z,s=3,alpha=0.1,edgecolors='none')
    
        p1 = ax.imshow(np.flipud(zz),cmap=cmap, interpolation='nearest', 
                       extent=extent_density, alpha=0.65)
        clb = plt.colorbar(p1)

        label_str = 'Log of % ballistic'
        clb.set_label(label_str, labelpad=-40, y=1.05, rotation=0)
      
        if i<len(diams):
                
            string = '_d'+str(i)+'_'
            title = 'Diameter = '+str(diams[i])+'m' 
            
        else:
        
            string = '_tot_'
            title = 'All sizes'
      
        plt.title(title)
      
        png_file = DEM_file.replace('.asc', string+'ballistic.png')
             
        plt.savefig(png_file, dpi=200)
        plt.close(fig)
 
        nd = -9999
 
        zz[zz==-np.inf] = nd   		

        asc_file = DEM_file.replace('.asc', string+'ballistic.asc')
    
        header = "ncols     %s\n" % xx.shape[1]
        header += "nrows    %s\n" % xx.shape[0]
        header += "xllcorner " + str(x_dens_min) + "\n"
        header += "yllcorner " + str(y_dens_min) + "\n"
        header += "cellsize " + str(step_dens) + "\n"
        header += "NODATA_value " + str(nd)

        np.savetxt(asc_file,
               np.flipud(zz),
               header=header,
               fmt='%1.5f',
               comments='')

        # plt.show()

    
if __name__ == '__main__':

    main()
