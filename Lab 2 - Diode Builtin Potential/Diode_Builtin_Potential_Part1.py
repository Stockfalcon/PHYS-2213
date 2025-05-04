import nidaqmx
from nidaqmx.constants import TerminalConfiguration, AcquisitionType, Edge
from nidaqmx.stream_readers import AnalogMultiChannelReader
from nidaqmx.stream_writers import AnalogSingleChannelWriter
import numpy as np
import threading 
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import animation
import time



device = 'Dev2'
resistor_channel = 'ai0'
diode_channel = 'ai1'
voltage_channel ='ao0'

SampleClock = "Dev2/ao/SampleClock"
trigger_line = "Dev2/ao/StartTrigger"


sample_rate = 100
total_data_points = 1000
samples_per_point = 500 # we will be taking the average of this many samples for each point plotted to get rid of noise
total_time = (samples_per_point * total_data_points) / sample_rate # total time in seconds
ao_voltages = np.linspace(-10,10,total_data_points)

all_data = np.empty((3,0))
data = np.zeros((2,samples_per_point))
plot_buffer = np.zeros((2,1000)) # rolling window

take_readings=True

resistor_plot = np.empty((2,0))
diode_plot = np.empty((2,0))
  
resistor_data = np.array([])
diode_data = np.array([])

voltage_index = 0


averager_index = 0

#NOTE TO SELF: WHEN READINGS ARE TAKEN, THEY WILL TAKE A NUMBER OF SAMPLES DEFINED BY samples_per_point  

task_ai, task_ao = nidaqmx.Task(), nidaqmx.Task()
# set up all resistor analog input.
task_ai.ai_channels.add_ai_voltage_chan(f'{device}/{resistor_channel}',
                                                terminal_config=TerminalConfiguration.DIFF) # add an ai channel and set the measurement type to an differential measurement system.
#                                                                                           This ensures that the input measured is NOT referenced to ground, but to the negative ai0 terminal.  
#                                                                                           https://www.ni.com/docs/en-US/bundle/ni-daqmx/page/refsingleended.html
# setup diode analog input. 
task_ai.ai_channels.add_ai_voltage_chan(f'{device}/{diode_channel}',terminal_config=TerminalConfiguration.DIFF) 
task_ai.timing.cfg_samp_clk_timing(sample_rate, sample_mode=AcquisitionType.FINITE, samps_per_chan=samples_per_point) # set the sample rate and clock source for the input channel

# setup analog output. 
task_ao.ao_channels.add_ao_voltage_chan(f'{device}/{voltage_channel}',
                                                min_val=-10.0, max_val=10.0)

task_ao.timing.cfg_samp_clk_timing(sample_rate, sample_mode=AcquisitionType.FINITE, samps_per_chan=total_data_points) # set the sample rate and clock source for the output channel



def nidaqmx_task(ao_voltages):
    global data, resistor_data, diode_data

    voltage_index=0
    analog_out = np.tile(ao_voltages[voltage_index],samples_per_point)
    task_ao.write(analog_out)
    task_ao.start()
    task_ai.start()
    data = task_ai.read(number_of_samples_per_channel=samples_per_point) # this will read data from both ai tasks
    voltage_index += 1
    task_ao.stop()
    task_ai.stop()

        
    np.hstack([resistor_data, data[0]])
    np.hstack([diode_data, data[1]])
        
        

        
    


print(plot_buffer)
fig, ax = plt.subplots()
lines=[]
lines = [ax.plot(plot_buffer[i])[0] for i in range(2)]
ax.set_ylim(-0.01,0.1)

def averager():
    global averager_index, resistor_data, diode_data
    resistor_avg = np.mean(resistor_data[averager_index : averager_index+samples_per_point])
    diode_avg = np.mean(diode_data[averager_index : averager_index+samples_per_point])
    averager_index += samples_per_point
    return resistor_avg, diode_avg, averager_index

def update(frame, plot_buffer):
    global all_data, resistor_plot, diode_plot

    resistor_avg, diode_avg, averager_index = averager()

    ao_voltages_index = (averager_index/samples_per_point)

    np.hstack([resistor_plot,[[ao_voltages[0]],[resistor_avg]]])
    np.hstack([diode_plot,[[ao_voltages[0]],[diode_avg]]])

    lines[0].set_data(resistor_plot[0], resistor_plot[1])
    lines[1].set_data(diode_plot[0], diode_plot[1])

    return lines




    
t = threading.Thread(target=nidaqmx_task,args=(list(ao_voltages)))
t.start()

ani = animation.FuncAnimation(fig, update, fargs=[plot_buffer], interval=(samples_per_point/sample_rate)*1000, blit=True)


plt.show()
# time.sleep(5)
t.join()


# print(all_data)
# all_data = np.transpose(all_data)
# df=pd.DataFrame(all_data)
# print(df)
# df.to_csv(r"C:\Users\lenovo\Downloads\data.csv")

# ----- MISTAKES(?) IN LAST WEEK'S LAB -----

# apparently, it is better to use    with nidaqmx.Task() as task:   instead of    task = nidaqmx.Task()
# because if the program stops unexpectedly, it won't give you a warning about resources being reserved or something like that
# I could have changed it in the last lab after I learned this but I didn't want to :)

# Also in the last lab, the TerminalConfiguration argument in the nidaqmx task setup was set to .RSE
# I think this referenced the analog input to ground and should have been set to .DIFF (differential)
# Some one with more competency than me should look here to verify if I'm correct
# https://www.ni.com/docs/en-US/bundle/ni-daqmx/page/refsingleended.html

# Hi! i'm writing some code to plot the builtin potential of a diode using nidaqmx in python, but i don't know how to assign  get the voltage values out (x axis) 