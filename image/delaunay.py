import numpy as np
from skimage.filter import canny
from scipy.spatial import Delaunay
from skimage.draw import polygon, line
from skimage.color import rgb2gray

def outline(py,px):
    """Pixels contained in polygon edge"""
    oy, ox = [], []
    for y0,x0,y1,x1 in zip(py,px,np.roll(py,1),np.roll(px,1)):
        ly,lx = line(y0,x0,y1,x1)
        oy += list(ly)
        ox += list(lx)
    return (np.array(oy,int), np.array(ox,int))
        
class DelaunaySegmentation(object):
    def __init__(self,image):
        """Extract points, compute Delaunay tessellation, compute features, and make properties
        available:

        image - ndimage the image data
        segments - a set of N indexes of segments that still exist
        vertices(N) - for each segment, the coordinates of its vertices
        pixels(N) - for each segment, the coordinates of its boundary and interior pixels
        neighbors(N) - for each segment, a set of indicies of neighboring segments
        features(N) - for each segment, a dictionary of features"""
        self.image = image
        points = self.find_points()
        tri = Delaunay(points)
        self.segments = set()
        self.vertices = {}
        self.pixels = {}
        self.neighbors = {}
        self.features = {}
        N = len(tri.vertices)
        for v,n in zip(tri.vertices,range(N)):
            py,px = np.rot90(points[v],3) # ccw for y,x
            iy,ix = [f.astype(int) for f in polygon(py,px)] # interior
            oy,ox = outline(py,px) # edges
            self.segments.add(n)
            self.vertices[n] = (py,px)
            self.pixels[n] = (np.concatenate((iy,oy)),np.concatenate((ix,ox)))
            self.neighbors[n] = set(tri.neighbors[n])
            self.features[n] = self.compute_features(n)
    def merge(self,i,j):
        """Merge segments i and j. They must be neighbors!
        Features are recomputed for the new merged segment"""
        if j not in self.neighbors[i] or i not in self.neighbors[j]:
            raise KeyError('cannot merge non-neighboring segments')
        self.segments.remove(j)
        fy,fx = self.pixels[i]
        gy,gx = self.pixels[j]
        self.pixels[i] = (np.concatenate((fy,gy)),np.concatenate((fx,gx)))
        # now merge neighborhoods
        # a) i and j are no longer neighbors
        self.neighbors[i].remove(j)
        self.neighbors[j].remove(i)
        # b) j's neighbors are now i's neighbors
        for n in self.neighbors[j]:
            if n != -1:
                self.neighbors[n].remove(j)
                self.neighbors[n].add(i)
        # b) i's neighbors now also include j's neighbors
        self.neighbors[i] |= self.neighbors[j]
        self.features[i] = self.compute_features(i)
        # FIXME also: remove shared vertices
        return i
    def find_points(self,image):
        """Override to find a list of points for the Delaunay tessellation"""
        return np.zeros((0,2),int)
    def compute_features(self,i):
        """Override to compute features for a given segment"""
        return {}
    @property
    def size(self):
        return len(self.segments)
    def __iter__(self):
        """Iterate over segment indicies"""
        return iter(self.segments)
    
class CannySegmentation(DelaunaySegmentation):
    """A Delaunay segmentation based on canny edges.
    Note that this is typically a dense tesselation with many very narrow triangles"""
    def find_points(self):
        c = canny(rgb2gray(self.image))
        return np.rot90(np.vstack(np.where(c)))

class AverageColorSegmentation(CannySegmentation):
    """Example features"""
    def compute_features(self,i):
        fy,fx = self.pixels[i]
        return dict(color=[np.average(self.image[fy,fx,c]) for c in range(3)])
