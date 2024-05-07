import pathlib
import os
import json
import pandas as pd
from typing import Union, List, Tuple, Dict, Optional

class GeckoSimulation:
    """
    A class to control the GeckoCIRCUITS power electronics simulation tool remotely using inbuilt api services via remote connection.
    Please ensure that the remote access of GeckoCIRCUITS is enabled and set to 43036 port.

    This class is based on the work of https://github.com/MauererM/pygeckocircuits/blob/master/PyGeckoExample.py
    GeckoCIRCUITS: https://github.com/geckocircuits/GeckoCIRCUITS

    Definitions:
     * Parameters are global
       - parameter_key
       - parameter_value
     * Every component (e.g. 'L.1') contains
       - a component_key (e.g. 'L')
       - a component_value (e.g. 100e-6)
     * a node is a net-node in GeckoCIRCUITS, e.g. you can name a net with a label 'v_in'
       
    Method naming:
     * set_   : e.g. to set values or parameters
     * get_   : e.g: to get keys, values or parameters
    """

    timestep: float
    simtime: float
    timestep_pre: float
    simtime_pre: float
    geckoport: int
    geckopath: pathlib.Path
    javapath: pathlib.Path
    simfilepath: Optional[str]
    debug: bool

    def __init__(self, simfilepath: str, geckoport: int = 43036, timestep: float = None, simtime: float = None, timestep_pre: float = 0, simtime_pre: float = 0,
                 debug: bool = True) -> None:
        """
         An initialization block which sets up the required java configuration to run the GeckoCIRCUITS on your PC.
         Java (GeckoCIRCUITS.jar) file located inside the GeckoCIRCUITS directory needs to be provided
         for remote configuration.

         :param simfilepath: absolute or relative path to simulation file
         :type simfilepath: str
         :param geckoport: Port to connect to GeckoCIRCUITS. Default port is 43036
         :type geckoport: int
         :param timestep: simulation fix timestep
         :type timestep: float
         :param simtime: total simulation time
         :type simtime: float
         :param debug: Debug mode displays extra information
         :type debug: bool

         :return: None
         :rtype: None
        """
        # Find out the onelab_path of installed module,
        # or in case of running directly from git, find the onelab_path of git repository
        module_file_path = pathlib.Path(__file__).parent.absolute()
        try:
            config_file = open(module_file_path / 'config.json', 'r', encoding='utf-8')
            file_data = config_file.read()
            json_data = json.loads(file_data)
            if pathlib.Path(json_data['gecko'] + 'GeckoCIRCUITS.jar').exists() and pathlib.Path(json_data['java'] + 'bin').exists():
                self.geckopath = pathlib.Path(json_data['gecko'] + 'GeckoCIRCUITS.jar')
                self.javapath = pathlib.Path(json_data['java'] + 'bin')
            else:
                config_file.close()
                os.remove(module_file_path / 'config.json')
                raise FileNotFoundError
        except FileNotFoundError:
            is_jar_exists = True
            is_bin_exists = True
            path_wrong = True
            while is_jar_exists:
                while path_wrong:
                    gecko_path = input("Enter the path to Gecko directory:")
                    if '\\' in gecko_path:
                        path_wrong = True
                        print("Use '/' instead of '\\'!")
                    else:
                        path_wrong = False
                if gecko_path[-1] != '/':
                    gecko_path = gecko_path + '/'
                is_jar_exists = not pathlib.Path(gecko_path + 'GeckoCIRCUITS.jar').exists()
                self.geckopath = pathlib.Path(gecko_path + 'GeckoCIRCUITS.jar')
            path_wrong = True
            while is_bin_exists:
                while path_wrong:
                    java_path = input("Enter the path to Java directory, see examples \n"
                                      "Example Windows: C:/Programme/Java/jdk*** \n"
                                      "Example Linux: /usr/lib/jvm/java-17-openjdk \n"
                                      "Enter path here:")
                    if '\\' in java_path:
                        path_wrong = True
                        print("Use '/' instead of '\\'!")
                    else:
                        path_wrong = False
                if java_path[-1] != '/':
                    java_path = java_path + '/'
                is_bin_exists = not pathlib.Path(java_path + 'bin').exists()
                self.javapath = pathlib.Path(java_path + 'bin')
            path_dict = {"java": java_path, "gecko": gecko_path}
            file = open(module_file_path / 'config.json', 'w', encoding='utf-8')
            json.dump(path_dict, file, ensure_ascii=False)
            file.close()

        os.environ['CLASSPATH'] = self.geckopath.__str__()
        try:
            from jnius import autoclass
        except Exception:
            os.environ['JDK_HOME'] = self.javapath.__str__()
            os.environ['JAVA_HOME'] = self.javapath.__str__()
            from jnius import autoclass
        global jnius
        import jnius

        # Note that parameters must be passed as java-strings to Gecko, as it otherwise throws a fit:
        self.JString = autoclass('java.lang.String')
        # The class to control GeckoCIRCUITS:
        self.Inst = autoclass('gecko.GeckoRemoteObject')
        print(self.Inst)
        self.geckoport = geckoport
        self.simfilepath = simfilepath
        self.debug = debug
        self.open_file()

        if simtime is None and timestep is None:
            self.simtime, self.timestep, self.simtime_pre, self.timestep_pre = self.get_sim_time()
        else:
            self.timestep = timestep
            self.simtime = simtime
            self.timestep_pre = timestep_pre
            self.simtime_pre = simtime_pre

    # Shutting down any left instances
    def __del__(self):
        """
        A destructor to shut down any instances that are left opened after simulation
        """
        if hasattr(self, 'ginst'):
            print('Shutting down gecko')
            self.ginst.shutdown()

    # -----------------------------------
    # simulation file handling
    # -----------------------------------

    def save_file(self, filename: str) -> None:
        """
        A method to save the current .ipes file

        :param filename: name of the file that needs to be saved (include the path for saving into different directory)
        :type filename: str

        :return: opened .ipes file saved under the provided name and directory

        """
        if hasattr(self, 'ginst'):
            if filename.endswith('.ipes'):
                self.ginst.saveFileAs(filename)
            else:
                self.ginst.saveFileAs(filename+'.ipes')
        else:
            print('No instance is running!')

    def open_file(self) -> None:
        """
        Opens the file that is provided as attribute value to the class object

        :return: Gecko window loaded with the provided .ipes file
        :rtype: None

        """
        is_invalid_path = True
        while is_invalid_path:
            if isinstance(self.simfilepath, str) and self.simfilepath.endswith('.ipes') and pathlib.Path(self.simfilepath).exists():
                # Note: absolute filepaths needed. Otherwise, there will occur java.lang.String error when using relative paths
                self.simfilepath = os.path.abspath(self.simfilepath)
                is_invalid_path = False
                # Start GeckoCIRCUITS. This opens the Gecko window:
                self.ginst = self.Inst.startNewRemoteInstance(self.geckoport)
                # Open the simulation file. Use java-strings:
                file_name = self.JString(self.simfilepath)
                self.ginst.openFile(file_name)
            else:
                self.simfilepath = None
                print('Check the input file path')
                self.simfilepath = input("Enter the filepath (ex: E:/myfolder/BuckConverter.ipes):")
                
    def run_simulation(self, timestep: float = None, simtime: float = None, timestep_pre: float = None, simtime_pre: float = None, save_file: bool = False) -> None:
        """
        Runs the simulation upon execution with the default time step and simulation time.
        Note that file should have been opened for running the simulation.

        :param timestep: the dt time step of each simulation
        :type timestep: float
        :param simtime: simulation time, not including the optional pre simulation time
        :type simtime: float
        :param timestep_pre: the dt time step of the pre simulation
        :type timestep_pre: float
        :param simtime_pre: simulation time of the pre simulation
        :type simtime_pre: float
        :param save_file: True to save the file
        :type save_file: bool

        :return: None
        :rtype: None
        """
        # pre-simulation if defined:
        self.timestep_pre = self.timestep_pre if timestep_pre is None else timestep_pre
        self.simtime_pre = self.simtime_pre if simtime_pre is None else simtime_pre
        self.ginst.set_dt_pre(self.timestep_pre)
        self.ginst.set_Tend_pre(self.simtime_pre)
        # normal simulation:
        self.timestep = self.timestep if timestep is None else timestep
        self.simtime = self.simtime if simtime is None else simtime
        self.ginst.set_dt(self.timestep)  # Simulation time step
        self.ginst.set_Tend(self.simtime)  # Simulation time
        if self.debug:
            print(f"Simulation time: {self.simtime} s")
            print(f"Timestep time: {self.timestep} s")
        if save_file:
            self.save_file(self.simfilepath)
        self.ginst.runSimulation()

    # -----------------------------------
    # working with global parameters
    # -----------------------------------

    def set_global_parameters(self, params_dict: Dict, save_file: bool = False) -> None:
        """
        Sets the values for the declared and defined global parameters specific to the opened .ipes file
        Note: parameters can have '$' at the beginning or even not

        :param params_dict: the name of the global parameters that are in use (works with and without '$')
        :type params_dict: Dict

        :param save_file: set to true if the current file with modified global parameters need to be saved. Default: False
        :type save_file: bool

        :return: None
        :rtype: None
        
        :Example:
        >>> import leapythontoolbox as lpt
        >>> gecko_instance = lpt.GeckoSimulation('path/to/simfile.ipes')
        >>> gecko_instance.set_global_parameters({'V_in': 60})

        """
        for key, value in params_dict.items():
            try:
                if isinstance(key, str) and isinstance(value, (float, int)) and '$' not in key:
                    self.ginst.setGlobalParameterValue('$'+key, value)
                elif isinstance(key, str) and isinstance(value, (float, int)) and '$' in key:
                    self.ginst.setGlobalParameterValue(key, value)
            except jnius.JavaException as e:
                print('Failed!:', e.innermessage)
        if save_file:
            self.save_file(self.simfilepath)

    def get_global_parameters(self, parameters: Union[List, str]) -> Dict:
        """
        Gets the existing value of the provided global parameter variables
        
        :param parameters: names of the global parameters (excluding $)
        :type parameters: List[str] or str

        :return: dict with available parameters
        :rtype: Dict
        
        :Example:
        >>> import leapythontoolbox as lpt
        >>> buck_converter = lpt.GeckoSimulation('path/to/gecko_file.ipes')
        >>> params = buck_converter.get_global_parameters(['V_in', 'f_s', 'duty_cycle', 'V_out', 'L'])
        """
        parameter_list = [parameters] if isinstance(parameters, str) else parameters
        parameter_dict = {}
        
        for name in parameter_list:
            try:
                parameter_value = self.ginst.getGlobalParameterValue('$'+name)
                parameter_dict[name] = parameter_value
                if self.debug:
                    print(f'{name} = {parameter_value}')
            except jnius.JavaException as e:
                print('Failed!:', e.innermessage)
        return parameter_dict
    
    def get_sim_time(self) -> Tuple:
        """
        Prints and returns the current step time and simulation time to the console

        :return: simtime, timestep
        :rtype: Tuple
        """

        simtime = self.ginst.get_Tend()
        timestep = self.ginst.get_dt()
        simtime_pre = self.ginst.get_Tend_pre()
        timestep_pre = self.ginst.get_dt_pre()
        if self.debug:
            print(f"read simtime: {simtime} s")
            print(f"read timestep: {timestep} s")
            print(f"read simtime_pre: {simtime_pre} s")
            print(f"read timestep_pre: {timestep_pre} s")

        return simtime, timestep, simtime_pre, timestep_pre

    def set_sim_time(self, simtime: float, timestep: float = None, simtime_pre: float = None, timestep_pre: float = None) -> None:
        """
        Sets the simulation time and the timestep [optional]

        :param simtime: simulation time
        :type simtime: float
        :param timestep: simulation time step
        :type timestep: float
        :param timestep_pre: the dt time step of the pre simulation
        :type timestep_pre: float
        :param simtime_pre: simulation time of the pre simulation
        :type simtime_pre: float
        :return: None
        :rtype: None

        """
        self.simtime = simtime
        if timestep is not None:
            self.timestep = timestep
        self.simtime_pre = self.simtime_pre if simtime_pre is None else simtime_pre
        self.timestep_pre = self.timestep_pre if timestep_pre is None else timestep_pre
    
    # -----------------------------------
    # working with standard components (R, L, C, ...)
    # -----------------------------------

    def get_component_keys(self, component_name: str) -> List:
        """
        Returns the string list of all component names
        This function is typically not used by the user
        Helper-method for get_component_values()

        :param component_name: the name of the component (ex: IGBT.1)
        :type component_name: str

        :return: list of all the accessible component parameter keys
        :rtype: List
        """
        properties = []
        property_keys = []
        properties = self.ginst.getAccessibleParameters(component_name)
        if self.debug:
            print(f'Component {component_name} has parameters: ', properties)
        for param in properties:
            property_keys.append(param.split("\t")[0])
        return property_keys

    def get_component_values(self, component_name: str) -> Dict:
        """
        Returns the values of the component parameters
        :param component_name: the name of the component (ex: IGBT.1)
        :type component_name: str

        :return: values of the component parameters in a dict
        :rtype: Dict

        :Example:
        >>> import leapythontoolbox as lpt
        >>> gecko_instance = lpt.GeckoSimulation('path/to/simfile.ipes')
        >>> gecko_instance.get_component_values('mosfet.1')

        !NOTE!: all designators and indizees must be chosen with capital letters in the .ipes file
        """
        component_params = self.get_component_keys(component_name.upper())
        values = {}
        for param in component_params:
            values[param] = self.ginst.getParameter(component_name.upper(), param)
        if self.debug:
            print(values)
        return values
    
    def set_component_values(self, component_name: str, component_dict: Dict) -> None:
        """
        Sets the values for the configurable parameters of selected component other than switches

        :param component_name: name of the selected component that needs to be configured
        :param component_dict: the key value pairs that need to be set on the selected component

        :return: None
        :rtype: None

        :raises KeyError: if invalid keys are provided as the component parameters

        :Example:
        >>> import leapythontoolbox as lpt
        >>> gecko = lpt.GeckoSimulation('path/to/simfile.ipes')
        >>> gecko.set_component_values('L.1', {'iL(0)': 100})

        !NOTE!: all designators and indizees must be chosen with capital letters in the .ipes file
        """
        existing_pairs = self.get_component_values(component_name.upper())

        input_keys = list(component_dict.keys())
        valid_keys = list(existing_pairs.keys())
        if set(input_keys).issubset(valid_keys):
            keys_to_check = {}
            for key, value in component_dict.items():
                if existing_pairs[key] != value:
                    keys_to_check[key] = existing_pairs[key]
            values = list(component_dict.values())
            self.ginst.setParameters(component_name, input_keys, values)
            new_pairs = self.get_component_values(component_name.upper())
            for key, value in keys_to_check.items():
                if new_pairs[key] == value:
                    print(f'Warning! {key} of {component_name} can be a global parameter as value could not be updated')
        else:
            msg = 'Invalid keys provided for the selected component'
            raise KeyError(msg)
        

    # -----------------------------------
    # working with switches (mosfet, igbt)
    # -----------------------------------

    def set_switch_values(self, sw_type: str, component_name: str, switch_key_value_dict: dict) -> None:
        """
        A method to set the configuration parameters of the selected switch type. 
            Only switch types of mosfet/igbt/diode are allowed

        :param sw_type: switch type can be either mosfet/igbt/diode
        :type sw_type: str
        :param component_name: name of the selected switch (ex: IGBT.1, MOSFET.1 etc.)
        :type component_name: str
        :param switch_key_value_dict: the configuration parameter names and their values related to selected
            switch type that needs to be set
        :type switch_key_value_dict: Dict

        :return: None
        :rtype: None
        """
        config_items = self.get_switch_keys(sw_type)
        input_keys = list(switch_key_value_dict.keys())
        try:
            if config_items:
                if set(input_keys).issubset(config_items):
                    values = list(switch_key_value_dict.values())
                    self.ginst.setParameters(component_name, input_keys, values)
                else:
                    msg = 'Invalid keys are provided'
                    print(f'Available settings for {sw_type} :', config_items)
                    raise KeyError(msg)
        except jnius.JavaException as e:
            print('Failed: ', e.innermessage)

    def set_loss_file(self, component_names: Union[str, List], loss_file_path: str) -> None:
        """
        Sets the total loss file to the selected switch. Location of the SCL files is required for loading them into the switches

        :param component_names: name of the selected switch (ex: IGBT.1, MOSFET.1 etc.)
        :type component_names: str or list
        :param loss_file_path: the path of the .SCL file that needs to be loaded
        :type loss_file_path: str (r'C:/***/***.scl)

        :return: None
        :rtype: None
        """
        if '\\' in loss_file_path:
            msg = "Use '/' instead of '\\'!"
            raise Exception(msg)
        # bring a relative path to an absolute path if path is relative
        loss_file_path = os.path.abspath(loss_file_path)

        if os.path.exists(loss_file_path) is False:
            raise Exception(f'Loss file path "{loss_file_path}" does not exist!')

        component_names = [component_names] if isinstance(component_names, str) else component_names
        available_components = self.ginst.getCircuitElements()
        if set(component_names).issubset(available_components):
            for name in component_names:
                self.ginst.doOperation(name, "setLossFile", loss_file_path)
        else:
            msg = 'Not all provided component names exists!'
            raise Exception(msg)

    def get_switch_keys(self, sw_type: str) -> List:
        """
        A helper function to configure switch method to set the properties of the selected switch type
        This function does _not_ interact with geckoCircuits!

        :param sw_type: switch type can be either mosfet/igbt/diode
        :type sw_type: str

        :return: characteristics parameter names as list
        :rtype: List

        :Example:
        >>> import leapythontoolbox as lpt
        >>> buck_converter = lpt.GeckoSimulation('Example_Gecko.ipes', simtime=0.05, timestep=50e-9)
        >>> mosfet_parameter_list = buck_converter.get_switch_keys('mosfet')
        """
        switches = {'mosfet': ['rON', 'rOFF', 'ad_uF', 'ad_rON', 'ad_rOFF', 'paralleled'],
             'igbt': ['uF', 'rON', 'rOFF', 'paralleled'],
             'diode': ['uF', 'rON', 'rOFF', 'paralleled']}
        read_keys = switches.get(sw_type.lower())
        if self.debug:
            print(f"{sw_type} parameters: {read_keys}")
        return read_keys

    # -----------------------------------
    # working with signals (scope)
    # -----------------------------------

    def get_scope_data(self, node_names: Union[List, str], file_name: str, start_time: float = None,
                     stop_time: float = None, skip_points: int = 0) -> None:
        """
        Gets the data from the scope that has been recorded after the corresponding simulation.
        The data with respect to specified scope nodes are extracted and save to csv file locally.

        :param node_names: the name provided to the scope nodes
        :type node_names: List[str] or str
        :param file_name: name of the csv file under which the extracted data needed to be exported
        :type file_name: str
        :param start_time: the time from where the data needs to be recorded
        :type start_time: float
        :param stop_time: the time at which the data recording stops
        :type stop_time: float
        :param skip_points: the length of points that needs to be skipped (ex: skip_points = 2 means data is recorded after every 2 data points)
        :type skip_points: int

        :return: None
        :rtype: None
        """
        stop_time = stop_time if stop_time and stop_time > 0 else self.ginst.get_Tend()
        start_time = start_time if start_time and start_time < stop_time else 0
        data = {}
        if isinstance(node_names, list):
            for node in node_names:
                data[node] = self.ginst.getSignalData(node, start_time, stop_time, skip_points)
                if data[node] == []:
                    del data[node]
        if data:
            time = self.ginst.getTimeArray(list(data.keys())[0], start_time, stop_time, skip_points)
            df = pd.DataFrame(data)
            df.insert(0, 'time', time)
            df.to_csv(path_or_buf=file_name+'.csv', encoding='utf-8', index=False, sep=' ', header=True)
        else:
            print('Nothing to be saved')

    def get_values(self, nodes: Union[List, str], operations: Union[List, str],
                   range_start_stop: List[Union[float, str]] = None) -> Dict:
        """
        Provides the applicable mean, rms, THD, ripple, Max, Min operations on the selected field that is being
        provided as a node to the scope

        :param nodes: node names located on the scopes
        :type nodes: name of the signal that is provided as node to the scope block
        :param operations: Mean\RMS\THD\Ripple\Max\Min\Shape operations on the selected signals. 
            Multiple operations can be provided as a list
        :type operations: List or str
        :param range_start_stop: the range of the data that needs to be considered for applying the mentioned 
            operations (ex: [10e-3, start] considers data from 0 to 10e-3)
        :type range_start_stop: [float, str] or [float, float]

        :return: returns operation specific dict data (ex: operations = [mean, rms] expected returns:
             return_dict =  {'mean': {'signal_1': mean_signal_1, 'signal_2': mean_signal_2}, 
             'rms': {'signal_1': rms_signal_1, 'signal_2': rms_signal_2}}
        :rtype: Dict
        """
        nodes = [nodes] if isinstance(nodes, str) else nodes
        operations = [operations] if isinstance(operations, str) else operations
        # Calculation of start and end time of useful data with respect to pre-simulation and simulation times
        # Note that the very first datapoint is mostly useless therefore we skipp the dt time at start
        data_start_time = self.ginst.get_Tend_pre() + self.ginst.get_dt()
        # The end time is often shorter in Geckos own data analysis, therefore subtracting 2*dt as Gecko did
        data_end_time = self.ginst.get_Tend_pre() + self.ginst.get_Tend() - 2 * self.ginst.get_dt()
        range_start_stop = [data_start_time, data_end_time] if range_start_stop is None else range_start_stop
        try:
            if len(range_start_stop) > 2 or isinstance(range_start_stop[0], str) or abs(range_start_stop[0]) > data_end_time:
                msg = f'Sim duration: {data_start_time} to {data_end_time}\n range formats: [start_time, end_time]\n range_start_stop: [+time, \'start\'], \n range_start_stop: [-time, \'end\']'
                raise Exception(msg)
            if isinstance(range_start_stop[1], str):
                if range_start_stop[1] == 'end':
                    end = data_end_time
                    start = data_end_time - abs(range_start_stop[0])
                elif range_start_stop[1] == 'start':
                    start = data_start_time
                    end = start + abs(range_start_stop[0])
                else:
                    msg = f'Invalid string key: {range_start_stop[1]}'
                    raise Exception(msg)
            else:
                start = range_start_stop[0]
                end = range_start_stop[1]
                if start < data_start_time or start > end or start == end or end < data_start_time:
                    msg = f'start ({start}) should be between start_time ({data_start_time}) and end_time ({data_end_time}) and both > start_time ({data_start_time})'
                    raise Exception(msg)
        except Exception as e:
            print('Recheck the range format or time length')
            raise
        operators = {'mean': lambda name, s_time, e_time: self.ginst.getSignalAvg(name, s_time, e_time),
                     'rms': lambda name, s_time, e_time: self.ginst.getSignalRMS(name, s_time, e_time),
                     'max': lambda name, s_time, e_time: self.ginst.getSignalMax(name, s_time, e_time),
                     'min': lambda name, s_time, e_time: self.ginst.getSignalMin(name, s_time, e_time),
                     'thd': lambda name, s_time, e_time: self.ginst.getSignalTHD(name, s_time, e_time),
                     'ripple': lambda name, s_time, e_time: self.ginst.getSignalRipple(name, s_time, e_time),
                     'shape': lambda name, s_time, e_time: self.ginst.getSignalShape(name, s_time, e_time)}
        try:
            data = {}
            for operation_key in operations:
                data[operation_key] = {}
                for signal_node in nodes:
                    try:
                        signal_value = operators[operation_key.lower()](signal_node, start, end)
                        if self.debug:
                            print(operation_key + ' of ' + signal_node + ':', signal_value)
                        data[operation_key][signal_node] = signal_value
                    except jnius.JavaException:
                        pass
        except KeyError as e:
            msg = 'Invalid operator: '+e.args[0]
            raise Exception(msg)
        else:
            return data


if __name__ == '__main__':
    inst = GeckoSimulation(simfilepath=r'../examples/example_Gecko.ipes')
    inst.set_loss_file('MOSFET.1', '../examples/CREE_C3M0060065J_Switch.scl')    # the scl file should be located in the project directory
    inst.run_simulation()