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

Framework methods for the Array datatypes.

.. moduleauthor:: Lia Domide <lia.domide@codemart.ro>
.. moduleauthor:: Stuart A. Knock <Stuart@tvb.invalid>

"""
import numpy
import tvb.basic.traits.types_mapped as mapped
import tvb.basic.datatypes.arrays_data as arrays_data


class BaseArrayFramework(mapped.Array):
    """Basic class for non-mapped arrays."""
    pass

class FloatArrayFramework(arrays_data.FloatArrayData, BaseArrayFramework):
    """ This class exists to add framework methods to FloatArrayData """
    pass


class IntegerArrayFramework(arrays_data.IntegerArrayData, BaseArrayFramework):
    """ This class exists to add framework methods to IntegerArrayData """
    pass


class ComplexArrayFramework(arrays_data.ComplexArrayData, BaseArrayFramework):
    """ This class exists to add framework methods to ComplexArrayData """
    pass


class BoolArrayFramework(arrays_data.BoolArrayData, BaseArrayFramework):
    """ This class exists to add framework methods to BoolArrayData """
    pass


class StringArrayFramework(arrays_data.StringArrayData, BaseArrayFramework):
    """ This class exists to add framework methods to StringArrayData """
    pass


class PositionArrayFramework(arrays_data.PositionArrayData,
                             FloatArrayFramework):
    """ This class exists to add framework methods to PositionArrayData """
    pass


class OrientationArrayFramework(arrays_data.OrientationArrayData,
                                FloatArrayFramework):
    """ This class exists to add framework methods to OrientationArrayData """
    pass


class IndexArrayFramework(arrays_data.IndexArrayData, IntegerArrayFramework):
    """ This class exists to add framework methods to IndexArrayData """
    pass


class MappedArrayFramework(arrays_data.MappedArrayData):
    """ This class will hold methods that should be available to all 
    array types"""

    KEY_SIZE = "size"
    KEY_OPERATION = "operation"
    __tablename__ = None
    
    
    def configure_chunk_safe(self):
        """ Configure part which is chunk safe"""
        data_shape = self.get_data_shape('array_data')
        self.nr_dimensions = len(data_shape)
        for i in range(min(self.nr_dimensions, 4)): 
            setattr(self, 'length_%dd' % (i+1), int(data_shape[i]))
    
    
    def configure(self):
        """After populating few fields, compute the rest of the fields"""
        super(MappedArrayFramework, self).configure()
        if not isinstance(self.array_data, numpy.ndarray):
            return
        self.nr_dimensions = len(self.array_data.shape)
        for i in range(min(self.nr_dimensions, 4)): 
            setattr(self, 'length_%dd' % (i+1), self.array_data.shape[i])
    
    
    @staticmethod  
    def accepted_filters():
        filters = arrays_data.MappedArrayData.accepted_filters()
        filters.update({'datatype_class._nr_dimensions': 
                                {'type': 'int', 'display':'Dimensionality',
                                 'operations': ['==', '<', '>']},
                        'datatype_class._length_1d': 
                                {'type': 'int', 'display':'Shape 1',
                                 'operations': ['==', '<', '>']},
                       'datatype_class._length_2d': 
                                {'type': 'int', 'display':'Shape 2',
                                 'operations': ['==', '<', '>']}})
        return filters
    
    
    def reduce_dimension(self, ui_selected_items):
        """
        ui_selected_items is a dictionary which contains items of form:
        '$name_$D : [$gid_$D_$I,..., func_$FUNC]' where '$D - int dimension', '$gid - a data type gid',
        '$I - index in that dimension' and '$FUNC - an aggregation function'.

        If the user didn't select anything from a certain dimension then it means that the entire
        dimension is selected
        """

        #The fields 'aggregation_functions' and 'dimensions' will be of form:
        #- aggregation_functions = {dimension: agg_func, ...} e.g.: {0: sum, 1: average, 2: none, ...}
        #- dimensions = {dimension: [list_of_indexes], ...} e.g.: {0: [0,1], 1: [5,500],...}
        dimensions, aggregation_functions, required_dimension, shape_restrictions = \
        self.parse_selected_items(ui_selected_items)

        if required_dimension is not None:
            #find the dimension of the resulted array
            dim = len(self.shape)
            for key in aggregation_functions.keys():
                if aggregation_functions[key] != "none":
                    dim -= 1
            for key in dimensions.keys():
                if (len(dimensions[key]) == 1 and 
                    (key not in aggregation_functions 
                     or aggregation_functions[key] == "none")):
                    dim -= 1
            if dim != required_dimension:
                self.logger.debug("Dimension for selected array is incorrect")
                raise Exception("Dimension for selected array is incorrect!")

        result = self.array_data
        full = slice(0, None)
        cut_dimensions = 0
        for i in range(len(self.shape)):
            if i in dimensions.keys():
                my_slice = [full for _ in range(i - cut_dimensions)]
                if len(dimensions[i]) == 1:
                    my_slice.extend(dimensions[i])
                    cut_dimensions += 1
                else:
                    my_slice.append(dimensions[i])
                result = result[tuple(my_slice)]
            if i in aggregation_functions.keys():
                if aggregation_functions[i] != "none":
                    result = eval("numpy." + aggregation_functions[i] + 
                                  "(result,axis=" + str(i -cut_dimensions) +")")
                    cut_dimensions += 1

        #check that the shape for the resulted array respects given conditions
        result_shape = result.shape
        for i in range(len(result_shape)):
            if i in shape_restrictions:
                flag = eval(str(result_shape[i]) +
                           shape_restrictions[i][self.KEY_OPERATION] +
                           str(shape_restrictions[i][self.KEY_SIZE]))
                if not flag:
                    msg = ("The condition is not fulfilled: dimension " 
                           + str(i + 1) + " " 
                           + shape_restrictions[i][self.KEY_OPERATION] + " "
                           + str(shape_restrictions[i][self.KEY_SIZE]) + 
                           ". The actual size of dimension " + str(i + 1) 
                           + " is " + str(result_shape[i]) + ".")
                    self.logger.debug(msg)
                    raise Exception(msg)
        if (required_dimension is not None and required_dimension >= 1
            and len(result.shape) != required_dimension):
            self.logger.debug("Dimensions of the selected array are incorrect")
            raise Exception("Dimensions of the selected array are incorrect!")

        return result


    def parse_selected_items(self, ui_selected_items):
        """
        Used for parsing the user selected items.

        ui_selected_items is a dictionary which contains items of form:
        'name_D : [gid_D_I,..., func_FUNC]' where 'D - dimension', 'gid - a data type gid',
        'I - index in that dimension' and 'FUNC - an aggregation function'.
        """
        expected_shape_str = ''
        operations_str = ''
        dimensions = dict()
        aggregation_functions = dict()
        required_dimension = None
        for key in ui_selected_items.keys():
            split_array = str(key).split("_")
            current_dim = split_array[len(split_array) - 1]
            list_values = ui_selected_items[key]
            if list_values is None or len(list_values) == 0:
                list_values = []
            elif not isinstance(list_values, list):
                list_values = [list_values]
            for item in list_values:
                if str(item).startswith("expected_shape_"):
                    expected_shape_str = str(item).split("expected_shape_")[1]
                elif str(item).startswith("operations_"):
                    operations_str = str(item).split("operations_")[1]
                elif str(item).startswith("requiredDim_"):
                    required_dimension = int(str(item).split("requiredDim_")[1])
                elif str(item).startswith("func_"):
                    agg_func = str(item).split("func_")[1]
                    aggregation_functions[int(current_dim)] = agg_func
                else:
                    str_array = str(item).split("_")
                    if int(str_array[1]) in dimensions:
                        dimensions[int(str_array[1])].append(int(str_array[2]))
                    else:
                        dimensions[int(str_array[1])] = [int(str_array[2])]
        return dimensions, aggregation_functions, required_dimension, \
               self._parse_expected_shape(expected_shape_str, operations_str)


    def _parse_expected_shape(self, expected_shape_str='', operations_str= ''):
        """
        If we have the inputs of form: expected_shape='x,512,x' and operations='x,&lt;,x'.
        The result will be: {1: {'size':512, 'operation':'<'}}
        """
        result = {}
        if len(expected_shape_str.strip()) == 0 or \
           len(operations_str.strip()) == 0:
            return result

        shape_array = str(expected_shape_str).split(",")
        op_array = str(operations_str).split(",")

        operations = self._get_operations()
        for i in range(len(shape_array)):
            if (str(shape_array[i]).isdigit() and i < len(op_array) 
                and op_array[i] in operations):
                result[i] = {self.KEY_SIZE : int(shape_array[i]),
                             self.KEY_OPERATION : operations[op_array[i]]}
        return result


    @staticmethod
    def _get_operations():
        """Return accepted operations"""
        operations = {'&lt;': '<', '&gt;': '>', '&ge;': '>=', 
                      '&le;': '<=', '==': '=='}
        return operations


    
