# Coded by Thomas Murimboh with help from ChatGTP and Copilot 
# May 05, 2025


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


# ----- LINKS TO DOCUMENTATION -----


import nidaqmx
from nidaqmx.constants import TerminalConfiguration
import numpy as np
import threading 
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import animation
from queue import Queue


device = 'Dev2'
resistor_channel = 'ai0'
diode_channel = 'ai1'
voltage_channel ='ao0'

max_voltage = 2
min_voltage = -2

sample_rate = 1000
total_data_points = 100
samples_per_point = 50 # we will be taking the average of this many samples for each point plotted to get rid of noise
total_time = (samples_per_point * total_data_points) / sample_rate # total time in seconds
ao_voltages = np.linspace(min_voltage, max_voltage, total_data_points)
resistance = 110 # resistance of the resistor in ohms

diode_plot = np.array([[min_voltage],[0]])
  
data_queue = Queue()
voltage_index = 0 # used for looping through ao_voltages


#NOTE TO SELF: WHEN READINGS ARE TAKEN, THEY WILL TAKE A NUMBER OF SAMPLES DEFINED BY samples_per_point  

task_ai, task_ao = nidaqmx.Task(), nidaqmx.Task()
# set up all resistor analog input.
task_ai.ai_channels.add_ai_voltage_chan(f'{device}/{resistor_channel}',
                                                terminal_config=TerminalConfiguration.DIFF) # add an ai channel and set the measurement type to an differential measurement system.
#                                                                                           This ensures that the input measured is NOT referenced to ground, but to the negative ai0 terminal.  
#                                                                                           https://www.ni.com/docs/en-US/bundle/ni-daqmx/page/refsingleended.html
# setup diode analog input. 
task_ai.ai_channels.add_ai_voltage_chan(f'{device}/{diode_channel}',terminal_config=TerminalConfiguration.DIFF) 

# setup analog output. 
task_ao.ao_channels.add_ao_voltage_chan(f'{device}/{voltage_channel}',
                                                min_val=-10.0, max_val=10.0)




def nidaqmx_task(ao_voltages):
    global voltage_index
    task_ao.start()
    task_ai.start()
    task_ao.write(np.tile(0, samples_per_point))

    while voltage_index < len(ao_voltages):
        task_ao.write(ao_voltages[voltage_index])
        data = task_ai.read(number_of_samples_per_channel=samples_per_point)

        resistor_avg = np.mean(data[0])
        diode_avg = np.mean(data[1])

        current = resistor_avg/resistance


        # print(f"current: {current}, diode_avg: {diode_avg}\n")

        data_queue.put((diode_avg, current))

        # print(f"{data_queue.qsize()}")

        voltage_index += 1



fig, ax = plt.subplots()
diode_line, = ax.plot([],[], label='diode')
ax.set_xlim(-0.01,0.01)
ax.set_ylim(-10,1)

def update(frame):
    global diode_plot

    try:
        (diode_avg, current) = data_queue.get_nowait()
    except:
        print(f"nothing to plot yet")
        return [diode_line]


    # Add new points
    diode_plot = np.hstack((diode_plot, [[diode_avg], [current]]))


    # Update plot lines
    diode_line.set_data(diode_plot[0], diode_plot[1])

    return [diode_line]






    
t = threading.Thread(target=nidaqmx_task,args=([ao_voltages]))
t.start()


ax.set_xlim(-10,10)
ax.set_ylim(-0.01,0.1)
ani = animation.FuncAnimation(fig, update, interval=100, blit=True)


plt.show()

t.join()


transposed_data = np.transpose(diode_plot)
df=pd.DataFrame(transposed_data)
print(df)
df.to_csv(r"C:\Users\lenovo\Downloads\data.csv")



