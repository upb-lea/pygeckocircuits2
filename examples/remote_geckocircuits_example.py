"""Example to show how to control GeckoCircuits from python."""
import pygeckocircuits2 as pgc
import logging

# logging introduction:
# to see no debug information (quiet program while running), comment this lines
# if you want to see detailed information about the program messages, set the level to DEBUG.
# the default logging level is WARNING
# available logging levels: DEBUG (All details), WARNING, ERROR, CRITICAL (Show only critical errors)
# logging.basicConfig(format='%(levelname)s,%(asctime)s:%(message)s', encoding='utf-8')
# logging.getLogger('pygeckocircuits2').setLevel(logging.WARNING)

# open a gecko instance
buck_converter = pgc.GeckoSimulation('remote_geckocircuits_example.ipes', simtime=0.05, timestep=50e-9, simtime_pre=100e-3, timestep_pre=20e-9)

print(buck_converter.get_sim_time())

print("# -----------------------------------")
print("# working with global parameters")
print("# -----------------------------------")

# get the global parameter values
global_parameters = buck_converter.get_global_parameters(['V_in', 'f_s', 'duty_cycle', 'V_out', 'L'])
print(f"{global_parameters=}")

# set a single global parameter
buck_converter.set_global_parameters({'V_in': 60})

# set multiple global parameters. Works with and without '$' in front of key
buck_converter.set_global_parameters({'f_s': 555000, '$duty_cycle': 0.3})

# get the global parameter values in a list. See what has changed.
params = buck_converter.get_global_parameters(['V_in', 'f_s', 'duty_cycle', 'V_out', 'L'])
print(f"{params=}")


print("# -----------------------------------")
print("# working with standard components")
print("# -----------------------------------")

values_u1 = buck_converter.get_component_values('U.1')
print(f"{values_u1=}")
buck_converter.get_component_values('L.1')
buck_converter.set_component_values('L.1', {'iL(0)': 100})
buck_converter.get_component_values('L.1')

print("# -----------------------------------")
print("# working with switches (mosfet, igbt)")
print("# -----------------------------------")

# read mosfet parameters that can be changed in the next command
mosfet_parameter_list = buck_converter.get_switch_keys('mosfet')
print(mosfet_parameter_list)

# get the parameters of MOSFET.1
mosfet_parameters = buck_converter.get_component_values('MOSFET.1')
print(mosfet_parameters)

# set rON of MOSFET.1 to 5 Ohms
buck_converter.set_switch_values('mosfet', 'MOSFET.1', {'rON': 5, 'rOFF': 99999})

# set the loss files for the MOSFET
buck_converter.set_loss_file('MOSFET.1', r'CREE_C3M0060065J_Switch.scl')

print("# -----------------------------------")
print("# run the simulation")
print("# -----------------------------------")

# run the simulation and save the .ipes file
buck_converter.run_simulation(save_file=True)

print("# -----------------------------------")
print("# working with scopes / values")
print("# -----------------------------------")

# save the scope data to a csv.file
buck_converter.get_scope_data(node_names=['v_HS', 'v_LS', 'i_L', 'i_HS', 'i_LS'], file_name='scope_data')

# read back rms and mean values
return_dict = buck_converter.get_values(nodes=['v_HS', 'v_LS', 'i_L', 'i_HS', 'i_LS'], operations=['mean', 'rms'], range_start_stop=[110e-3, 120e-3])
print(return_dict)
