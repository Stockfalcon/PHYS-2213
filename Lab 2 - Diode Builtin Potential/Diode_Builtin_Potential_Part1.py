import nidaqmx
from nidaqmx.constants import TerminalConfiguration, AcquisitionType, Edge
from nidaqmx.stream_readers import AnalogMultiChannelReader
from nidaqmx.stream_writers import AnalogSingleChannelWriter
import numpy as np
import threading 
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import animation

# ----- MISTAKES(?) IN LAST WEEK'S LAB -----

# apparently, it is better to use    with nidaqmx.Task() as task:   instead of    task = nidaqmx.Task()
# because if the program stops unexpectedly, it won't give you a warning about resources being reserved or something like that
# I could have changed it in the last lab after I learned this but I didn't want to :)

# Also in the last lab, the TerminalConfiguration argument in the nidaqmx task setup was set to .RSE
# I think this referenced the analog input to ground and should have been set to .DIFF (differential)
# Some one with more competency than me should look here to verify if I'm correct
# https://www.ni.com/docs/en-US/bundle/ni-daqmx/page/refsingleended.html


device = 'Dev2'
resistor_channel = 'ai0'
diode_channel = 'ai1'
voltage_channel ='ao0'

SampleClock = "Dev2/ao/SampleClock"
trigger_line = "Dev2/ao/StartTrigger"


sample_rate = 1000
total_data_points = 1000
samples_per_point = 50 # we will be taking the average of this many samples for each point plotted to get rid of noise
total_time = (samples_per_point * total_data_points) / sample_rate # total time in seconds
ao_voltages = np.linspace(-10,10,total_data_points)

all_data = [[]] # an empy 2D array
data = np.zeros((2,samples_per_point))
plot_buffer = np.zeros((2,1000)) # rolling window

take_readings=True

#NOTE TO SELF: WHEN READINGS ARE TAKEN, THEY WILL TAKE A NUMBER OF SAMPLES DEFINED BY samples_per_point  

def nidaqmx_task():
    global data

    with nidaqmx.Task() as task_ai,  nidaqmx.Task() as task_ao:
        # set up all resistor analog input. This will be a follower which listens for a trigger, and timing signals to take readings 
        task_ai.ai_channels.add_ai_voltage_chan(f'{device}/{resistor_channel}',
                                                        terminal_config=TerminalConfiguration.DIFF) # add an ai channel and set the measurement type to an differential measurement system.
        #                                                                                           This ensures that the input measured is NOT referenced to ground, but to the negative ai0 terminal.  
        #                                                                                           https://www.ni.com/docs/en-US/bundle/ni-daqmx/page/refsingleended.html
        '''
        task_resistor_ai.timing.cfg_samp_clk_timing(sample_rate, 
                                                    source=SampleClock,
                                                    sample_mode=AcquisitionType.FINITE,
                                                    samps_per_chan=samples_per_point)
        '''
        
        # setup diode analog input. This will be a follower which listens for a trigger, and timing signals to take readings 
        task_ai.ai_channels.add_ai_voltage_chan(f'{device}/{diode_channel}',terminal_config=TerminalConfiguration.DIFF) 
        '''
        task_diode_ai.timing.cfg_samp_clk_timing(sample_rate, 
                                                    source=SampleClock,
                                                    sample_mode=AcquisitionType.FINITE,
                                                    samps_per_chan=samples_per_point) 
        
        task_ai.triggers.start_trigger.cfg_dig_edge_start_trig(trigger_source=trigger_line,
                                                                trigger_edge=Edge.RISING)         
        '''
        # setup analog outpu. This will be the Leader for sending triggers and telling the Followers when to take readings
        task_ao.ao_channels.add_ao_voltage_chan(f"{device}/{voltage_channel}",min_val=-10, max_val=10)
        '''
        task_ao.timing.cfg_samp_clk_timing(sample_rate, 
                                            source=SampleClock,
                                            sample_mode=AcquisitionType.FINITE,
                                            samps_per_chan=samples_per_point)
        
        task_ao.triggers.start_trigger.disable_start_trig() # this is to tell the Leader that it's job is to make a start signal and not to wait until it receives one
        '''
        reader = AnalogMultiChannelReader(task_ai.in_stream)
        writer = AnalogSingleChannelWriter(task_ao.in_stream)

        task_ai.start()
        task_ao.start()
        writer.write_many_sample(ao_voltages)

        while take_readings:
            reader.read_many_sample(data, samples_per_point,timeout=10.0)
             # Shift old data and add new samples for plotting (NOT THREAD SAFE!)
            plot_buffer[:, :-samples_per_point] = plot_buffer[:, samples_per_point:]
            plot_buffer[:, -samples_per_point:] = data


t=threading.Thread(target=nidaqmx_task)

t.start()

fig, ax = plt.subplots()
lines = [ax.plot(plot_buffer[i])[0] for i in range(2)]
ax.set_ylim(-0.01),0.1

def update(frame):
    for i, line in enumerate(lines):
        line.set_ydata(plot_buffer[i])
    return lines


ani = animation.FuncAnimation(fig, update, interval=50, blit=True)


plt.show()
take_readings = False
t.join() # wait for all threads to finnish
print(data)


            



    # for i in range(len(ao_voltages)):# this is currently software controlled data aquisition, later we will make this hardware controlled (faster and therefore better)
    #     task_ao.write(voltage_channel[i], auto_start=False)

    #     task_ao.start()
    #     task_resistor_ai.start()
    #     task_diode_ai.start()

    #     resistor_data = task_resistor_ai.read()
    #     diode_data = task_diode_ai.read()

    #     task_ao.stop()
    #     task_resistor_ai.stop()
    #     task_diode_ai.stop()


    # task_resistor_ai.stop()
    # task_diode_ai.stop()
    # task_resistor_ai.close()
    # task_diode_ai.close()
