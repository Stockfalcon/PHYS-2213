# Coded by Thomas Murimboh with help from ChatGTP and Copilot; comments by Thomas Murimboh
# May 07, 2025

# ----- MISTAKES(?) IN LAST WEEK'S LAB -----
# apparently, it is better to use    with nidaqmx.Task() as task:   instead of    task = nidaqmx.Task()
# because if the program stops unexpectedly, it won't give you a warning about resources being reserved or something like that
# I could have changed it in the last lab after I learned this but I didn't want to :)
# You'll also notice I didn't make the change for this lab. This was because I couldn't figure out a way to make it work efficiently with the threading library

# Also in the last lab, the TerminalConfiguration argument in the nidaqmx task setup was set to .RSE
# I think this referenced the analog input to ground and should have been set to .DIFF (differential)
# Some one with more competency than me should look here to verify if I'm correct
# https://www.ni.com/docs/en-US/bundle/ni-daqmx/page/refsingleended.html

# ----- SETTING THE STAGE -----
# In this part we will be taking voltage readings from both the diode and the resistor and plotting them using matplotlib. Because the signals we get back from 
# the resistor and diode are digital signals, using a filter like the last lab won't work, so we will take a whole bunch of readings for each voltage we output
# and then take the average of al of those readings to filter out the noise.


# ----- LINKS TO DOCUMENTATION -----
# https://nidaqmx-python.readthedocs.io/en/stable/task_collections.html#nidaqmx.task.collections.AOChannelCollection.add_ao_voltage_chan
# https://nidaqmx-python.readthedocs.io/en/stable/task.html#nidaqmx.task.Task.write


# ----- NOTE -----
# Apparently hardware timing is not supported on the NI USB-6002 which is the device I was using.
# So, this program is built around software timing instead wich is less precice and slower, but it gets the job done.

import nidaqmx                                      # use to communicate with our DAQ card                                                                                   
from nidaqmx.constants import TerminalConfiguration # an enum (variable with very specific values) that indicate to the nidaqmx.Task() function how to configure each channel
import numpy as np                                  # for doing calulations and modifying arrays                                                                             
import matplotlib.pyplot as plt                     # used to help plot our data                                                                                             
import pandas as pd                                 # for easily sorting our data as a .CSV                                                                                  


# Device Parameters
device = 'Dev2'          # your device name                              
resistor_channel = 'ai0' # you resistor port                             
diode_channel = 'ai1'    # your diode port                               
voltage_channel ='ao0'   # your analog out port connected to your circuit

# Sampling Parameters (How to sample data)
max_voltage = 10                                                        # the maximum voltage that will be outputted (dependent on your device)                                
min_voltage = -10                                                       # the minimum voltage that will be outputted (dependent on your device)                                
sample_rate = 1000                                                     # the number of samples per second that will be taken                                                  
total_data_points = 100                                                # the total number of data points that will be plotted (the more points, the longer it takes)          
samples_per_point = 50                                                 # we will be taking the average of this many samples for each point plotted to get rid of noise        
ao_voltages = np.linspace(min_voltage, max_voltage, total_data_points) # this evenly spaces total_data_points numper of points between min_voltage and max_voltage (inclusive)
resistance = 110                                                       # resistance of the resistor in ohms

# Other Various parameters
voltage_index = 0 # used for looping through ao_voltages

def start_up():                                                          # The purpose of this function is to initialize the diode_plot variable with our first data_point                                             
    print("Setting up diode plot")                                      
    global diode_plot                                                   
    task_ao.start()                                                      # start our analog out task                                                                                                                   
    task_ai.start()                                                      # start our analog in task                                                                                                                    
    task_ao.write(min_voltage)                                        
    data = task_ai.read(number_of_samples_per_channel=samples_per_point) # collect samples_per_point many data points from each channel and store them in a 2d array.                                                  
                                                                         # resistor data will be stored in data[0] and diode data will be stored in data[1] because this is the order in which we added them to task_ai
    resistor_avg = np.mean(data[0])                                      # take the average of all collected data points to reduce noise                                                                               
    diode_avg = np.mean(data[1])                                         # take the average of all collected data points to reduce noise                                                                               
    current = resistor_avg/resistance                                    # calculate the currrent through the diode & resistor                                                                                         
    diode_plot = [[diode_avg],[current]]                                 # save the initial averages to the data to plot                                                                                               
    task_ai.stop()                                                       # stop the analog input task                                                                                                                  
    task_ao.stop()                                                       # stop the analog output task

# Task Setup
task_ai, task_ao = nidaqmx.Task(), nidaqmx.Task()                                                               # inititlize two Task classes 

# set up resistor analog input.
task_ai.ai_channels.add_ai_voltage_chan(f'{device}/{resistor_channel}',
                                        terminal_config=TerminalConfiguration.DIFF)                            # add an ai channel and set the measurement type to a differential measurement system. 
#                                                                                                                This ensures that the input measured is NOT referenced to ground, but to the negative ai0 terminal.           
#                                                                                                                https://www.ni.com/docs/en-US/bundle/ni-daqmx/page/refsingleended.html
#setup diode analog input.                                                                                                                                                                               
task_ai.ai_channels.add_ai_voltage_chan(f'{device}/{diode_channel}',terminal_config=TerminalConfiguration.DIFF) # add an ai channel and set the measurement type to a differential measurement system. 
#                                                                                                                We can use task_ai for both the diode and resistor because one task can control multiple
#                                                                                                                channels as long as they can be configured in the same way (eg. timing, start trigger). 

# setup analog output.
task_ao.ao_channels.add_ao_voltage_chan(f'{device}/{voltage_channel}',                                           # add an ao channel and set the max and min output values (varies depending on device).
                                        min_val=-10.0, max_val=10.0)


def nidaqmx_task(ao_voltages):       # create a function with a space to put our voltagesto output
    global voltage_index, diode_plot # ensure we can modify these variables inside our function   
    task_ao.start()                  # start our analog out task                                  
    task_ai.start()                  # start our analog in task

    while voltage_index < len(ao_voltages):                                  # keep running this code until we have outputted and read data from all the voltages                                                                
        task_ao.write(ao_voltages[voltage_index])                            # output the voltage in the list ao_voltages indexed by the value voltage index (we would have to ouput more data if we were usinng hardawre timing)
        data = task_ai.read(number_of_samples_per_channel=samples_per_point) # collect samples_per_point many data points from each channel and store them in a 2d array.                                                        
                                                                             # resistor data will be stored in data[0] and diode data will be stored in data[1] because this is the order in which we added them to task_ai      
        resistor_avg = np.mean(data[0])                                      # take the average of all collected data points to reduce noise                                                                                     
        diode_avg = np.mean(data[1])                                         # take the average of all collected data points to reduce noise                                                                                     
        current = resistor_avg/resistance                                    # calculate the currrent through the diode & resistor                                                                                               
        diode_plot = np.hstack((diode_plot, [[diode_avg], [current]]))       # add this to the data we will be plotting                                                                                                          
        voltage_index += 1                                                   # update the voltage index to read the next voltage in the ao_voltages list




start_up()                                          # initialize diode_plot                                                           
nidaqmx_task(ao_voltages)                           # run the function defined above and give it the ao_voltages data                              

# Create The Figure
fig, ax = plt.subplots()                            # create ture and initialize a subplot with the name ax                                      
ax.plot(diode_plot[0],diode_plot[1], label='diode') # this creates a list of line 2D objects which will be used by matplotlib to create the graph
ax.set_xlim(min_voltage,max_voltage)                # set x axis limits in Volts                                                                 
ax.set_ylim(-0.01,0.03)                             # set y axis limits in Ampères                                                               
ax.set_xlabel("Diode Voltage (v)")                  # set x axis title                                                                           
ax.set_ylabel("Current (A)")                        # set y axis titile                                                                          
ax.set_title("Diode Built-in Potential")            # set Axes title                                                                             
plt.show()                                          # show our graph!                                                                            
                                                    # Next try to write some code to save the graph!

transposed_data = np.transpose(diode_plot)          # make our columns rows and vice versa                                                         
df=pd.DataFrame(transposed_data)                    # create a data frame (like a python spreadsheet)                                              
df.to_csv(r"C:\Users\lenovo\Downloads\data.csv")    # save the data to a place on our computer (the r indicates that the string is a file path)