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
import nidaqmx                                      # use to communicate with our DAQ card                                                                                   
from nidaqmx.constants import TerminalConfiguration # an enum (variable with very specific values) that indicate to the nidaqmx.Task() function how to configure each channel
import numpy as np                                  # for doing calulations and modifying arrays                                                                             
import matplotlib.pyplot as plt                     # used to help plot our data    
from matplotlib import animation                    # used to help animate our plot                                                                                         
import pandas as pd                                 # for easily sorting our data as a .CSV                                                                                  
from queue import Queue                             # we will be using this to control how data is accessed between data aquisition and ploting.
#                                                     It's knind of like a fancy python list and is especially important when we to use the threading library to speed up our program
import threading # this library can make our code run faster. A regular python program will wait for each function to finnish. If a function takes a really long time to complete
#                 (like reading thousands of data points), it will make the whole program take a really long time, even if your program is not actively using CPU power and just waiting for data from a DAQ  
#                  device. The threading library forces your CPU to keep working on a different function (defined in a different thread) while it's waiting so that things happen more efficiently. It's also worth
#                 noting that it doesn't make your CPU do two things at once (like multiprocessing does), it just makes your CPU do work instead of waiting when your DAQ card is reading data.               


# Device Parameters
device = 'Dev2'          # your device name                              
resistor_channel = 'ai0' # you resistor port                             
diode_channel = 'ai1'    # your diode port                               
voltage_channel ='ao0'   # your analog out port connected to your circuit

# Sampling Parameters (How to sample data)
max_voltage = 2                                                        # the maximum voltage that will be outputted (dependent on your device)                                
min_voltage = -2                                                       # the minimum voltage that will be outputted (dependent on your device)                                
sample_rate = 1000                                                     # the number of samples per second that will be taken                                                  
total_data_points = 100                                                # the total number of data points that will be plotted (the more points, the longer it takes)          
samples_per_point = 50                                                 # we will be taking the average of this many samples for each point plotted to get rid of noise        
ao_voltages = np.linspace(min_voltage, max_voltage, total_data_points) # this evenly spaces total_data_points numper of points between min_voltage and max_voltage (inclusive)
resistance = 110                                                       # resistance of the resistor in ohms

# Other Various parameters
diode_plot = np.array([[min_voltage],[0]]) # this will be a 2D into which we will store our data points (the legth of the final array will be equal to total_data_points)
data_queue = Queue()                       # We will use this to shuttle data from our aquisition function (nidaqmx_task) to our animation function (update)             
voltage_index = 0                          # used for looping through ao_voltages

#NOTE TO SELF: WHEN READINGS ARE TAKEN, THEY WILL TAKE A NUMBER OF SAMPLES DEFINED BY samples_per_point  

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

        data_queue.put((diode_avg, current))                                 # add this new data to the queue                                                                                                                    


        voltage_index += 1                                                   # update the voltage index to read the next voltage in the ao_voltages list                                                                         




fig, ax = plt.subplots()
diode_line, = ax.plot([],[], label='diode') # ax.plot() returns a tuple (uneditable list) of Line 2D elements which makes diode_line really hard to edit later on. To get around this, we
#                                            use a comma after the variable name to unpack the tuple and turn it into a single Line 2D object that we can edit.

def update(frame):
    global diode_plot                                              # ensure we can update this variable using this function                                                                         

    try:                                                           # use try except to deal with any exceptions raised                                                                              
        (diode_avg, current) = data_queue.get_nowait()             # get and remove the oldest data from the queue only if the nidaqmx_task function is not busy adding more data to it             
    except:                                                        # occurs when the queue is empty or when nidaqmx_task function is adding more data to the queue when we also want to read from it
        print(f"nothing to plot yet")                             
        return [diode_line]                                        # return our line as a list to FuncAnimation at the end of our code                                                              


                                                                  
    diode_plot = np.hstack((diode_plot, [[diode_avg], [current]])) # Add new points to the data we're collecting                                                                                    



    diode_line.set_data(diode_plot[0], diode_plot[1])              # Update plot lines unsing the new data

    return [diode_line]                                            # Return our line as a list to FuncAnimation at the end of our code






    
t = threading.Thread(target=nidaqmx_task,args=([ao_voltages]))
t.start()

#\/ \/ \/ \/ \/ EVERYTHING BELOW HERE RUNS ON THE MAIN THREAD \/ \/ \/ \/ (it also doesn't need to be explicitly defined)

ax.set_xlim(-10,10)
ax.set_ylim(-0.01,0.1)
ani = animation.FuncAnimation(fig, update, interval=100, blit=True) # calls the update() function every 100 ms to update the plot. The blit=True tells FuncAnimation to use a technique called blitting
#                                                                     which allows the plot to be drawn quicker if the interval is small. Blitting works by remembering most of the details of the plot so that it only has to redraw the line each time update is called.
#                                                                    (I think)

plt.show()

t.join() # when the plot is closed, wait for the thread to finnish


transposed_data = np.transpose(diode_plot)          # make our columns rows and vice versa                                                         
df=pd.DataFrame(transposed_data)                    # create a data frame (like a python spreadsheet)                                              
df.to_csv(r"C:\Users\lenovo\Downloads\data.csv")    # save the data to a place on our computer (the r indicates that the string is a file path)



