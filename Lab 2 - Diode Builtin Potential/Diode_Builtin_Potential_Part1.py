import nidaqmx
from nidaqmx.constants import TerminalConfiguration, AcquisitionType, Edge
from nidaqmx.stream_readers import AnalogMultiChannelReader
from nidaqmx.stream_writers import AnalogSingleChannelWriter
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

sample_rate = 1000
total_data_points = 1000
samples_per_point = 50 # we will be taking the average of this many samples for each point plotted to get rid of noise
total_time = (samples_per_point * total_data_points) / sample_rate # total time in seconds
ao_voltages = np.linspace(-10,10,total_data_points)

data = np.zeros((2,samples_per_point))
plot_buffer = np.zeros((2,1000)) # rolling window

resistor_plot = np.array([[-10],[0]])
diode_plot = np.array([[-10],[0]])
  
data_queue = Queue()
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
        voltage_val = ao_voltages[voltage_index]

        data_queue.put((voltage_val, resistor_avg, diode_avg))

        voltage_index += 1




            
        

        
    



fig, ax = plt.subplots()
resistor_line, = ax.plot([],[], label='resistor') # The ax.plot() function returns a list of lines and we only wan't one line
diode_line, = ax.plot([],[], label='diode')
ax.set_xlim(-10,10)
ax.set_ylim(-0.01,0.1)

def update(frame):
    global resistor_plot, diode_plot

    try:
        voltage_val, resistor_avg, diode_avg = data_queue.get_nowait()
    except:
        print("nothing to plot yet")
        return [resistor_line, diode_line]

    # Add new points
    resistor_plot = np.hstack((resistor_plot, [[voltage_val], [resistor_avg]]))
    diode_plot = np.hstack((diode_plot, [[voltage_val], [diode_avg]]))

    print(f"voltage: {voltage_val}, resistor: {resistor_avg}, diode: {diode_avg}")

    # Update plot lines
    resistor_line.set_data(resistor_plot[0].flatten(), resistor_plot[1].flatten())
    diode_line.set_data(diode_plot[0].flatten(), diode_plot[1].flatten())


    return [resistor_line, diode_line]






    
t = threading.Thread(target=nidaqmx_task,args=([ao_voltages]))
t.start()


ax.set_xlim(-10,10)
ax.set_ylim(-0.01,0.1)
ani = animation.FuncAnimation(fig, update, interval=50, blit=True)


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