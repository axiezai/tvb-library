# -*- coding: utf-8 -*-
#
#
# (c)  Baycrest Centre for Geriatric Care ("Baycrest"), 2012, all rights reserved.
#
# No redistribution, clinical use or commercial re-sale is permitted.
# Usage-license is only granted for personal or academic usage.
# You may change sources for your private or academic use.
# If you want to contribute to the project, you need to sign a contributor's license. 
# Please contact info@thevirtualbrain.org for further details.
# Neither the name of Baycrest nor the names of any TVB contributors may be used to endorse or 
# promote products or services derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY BAYCREST ''AS IS'' AND ANY EXPRESSED OR IMPLIED WARRANTIES, INCLUDING, 
# BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE 
# ARE DISCLAIMED. IN NO EVENT SHALL BAYCREST BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, 
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS 
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY 
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE
#
#

"""
Scientific methods for the Sensor dataTypes.

.. moduleauthor:: Lia Domide <lia@tvb.invalid>
.. moduleauthor:: Stuart A. Knock <Stuart@tvb.invalid>

"""

import numpy
import tvb.basic.datatypes.sensors_data as sensors_data


class SensorsScientific(sensors_data.SensorsData):
    """ This class exists to add scientific methods to SensorsData. """
    __tablename__ = None
    
    
    def _find_summary_info(self):
        """
        Gather scientifically interesting summary information from an instance
        of this datatype.
        """
        summary = {"Sensor type": self.sensors_type}
        summary["Number of Sensors"] = self.number_of_sensors
        return summary
    
    
    def sensors_to_surface(self, surface_to_map):
        """
        Map EEG sensors onto the head surface (skin-air).
        
        EEG sensor locations are typically only given on a unit sphere, that is,
        they are effectively only identified by their orientation with respect
        to a coordinate system. This method is used to map these unit vector
        sensor "locations" to a specific location on the surface of the skin.
        
        Assumes coordinate systems are aligned, i.e. common x,y,z and origin.
        
        """
        #TODO: Think I did this assuming zero centered head, if so need to 
        #      change to support coordinate origins not in the center... Should
        #      just require a check with offset included in calculus though as it
        #      won't be center of mass, getting the correct offset will be a pain.
        #SK  : Works but it's a bit of a mess, cleanup...
        
        #Normalize sensor and vertex locations to unit vectors
        norm_sensors = numpy.sqrt(numpy.sum(self.locations**2, axis=1))
        unit_sensors = self.locations / norm_sensors[:, numpy.newaxis]
        norm_verts = numpy.sqrt(numpy.sum(surface_to_map.vertices**2, axis=1))
        unit_vertices = surface_to_map.vertices / norm_verts[:, numpy.newaxis]
        
        sensor_tri = numpy.zeros((self.number_of_sensors, 1), dtype=numpy.int32)
        sensor_locations = numpy.zeros((self.number_of_sensors, 3))
        for k in range(self.number_of_sensors):
            #Find the surface vertex most closely aligned with current sensor.
            sensor_loc = unit_sensors[k]
            allignment = numpy.dot(sensor_loc, unit_vertices.T)
            one_ring = []
            while not one_ring:
                closest_vertex = allignment.argmax()
                
                #Get the set of triangles in the neighbourhood of that vertex.
                #NOTE: Intersection doesn't always fall within the 1-ring, so, all 
                #      triangles contained in the 2-ring are considered.
                one_ring = surface_to_map.vertex_neighbours[closest_vertex]
                if not one_ring:
                    allignment[closest_vertex] = min(allignment)
            local_tri = [surface_to_map.vertex_triangles[vertex] for vertex in one_ring]
            local_tri = list(set([tri for subar in local_tri for tri in subar]))
            
            #Calculate a parameterized plane line intersection [t,u,v] for the
            #set of local triangles, which are considered as defining a plane.
            tuv = numpy.zeros((len(local_tri), 3))
            i = 0
            for tri in local_tri:
                edge_01 = (surface_to_map.vertices[surface_to_map.triangles[tri, 0]] - 
                           surface_to_map.vertices[surface_to_map.triangles[tri, 1]])
                edge_02 = (surface_to_map.vertices[surface_to_map.triangles[tri, 0]] - 
                           surface_to_map.vertices[surface_to_map.triangles[tri, 2]])
                see_mat = numpy.vstack((sensor_loc, edge_01, edge_02))
                
                tuv[i] = numpy.linalg.solve(see_mat.T, surface_to_map.vertices[surface_to_map.triangles[tri, 0].T])
                i += 1
            #import pdb; pdb.set_trace()
            #Find find which line-plane intersection falls within its triangle 
            #by imposing the condition that u, v, & u+v are contained in [0 1]
            local_triangle_index = ((0 < tuv[:, 1]) * (tuv[:, 1] < 1) *
                                    (0 < tuv[:, 2]) * (tuv[:, 2] < 1) *
                                    (0 < (tuv[:,1] + tuv[:,2])) *
                                    ((tuv[:,1] + tuv[:,2]) < 1)).nonzero()[0]
            #TODO: add checks for no or multiple intersections...
            #      no: surface incomplete, misaligned, irregular triangulation
            #      multiple: surface possibly too folded or misaligned...
            sensor_tri[k] = local_tri[local_triangle_index]
            #Scale sensor unit vector by t so that it lies on the surface.
            sensor_locations[k] = sensor_loc * tuv[local_triangle_index, 0]
        
        return sensor_tri, sensor_locations 


class SensorsEEGScientific(sensors_data.SensorsEEGData, SensorsScientific):
    """ This class exists to add scientific methods to SensorsEEGData. """
    pass


class SensorsMEGScientific(sensors_data.SensorsMEGData, SensorsScientific):
    """ This class exists to add scientific methods to SensorsMEGData. """
    pass


class SensorsInternalScientific(sensors_data.SensorsInternalData,
                                SensorsScientific):
    """ This class exists to add scientific methods to SensorsInternalData. """
    pass

