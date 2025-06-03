# Coded by Thomas Murimboh with help from Copilot to resolve minor issues
# May 25 2025

### make size of xaxis change with data
# write data to file

#_____SETTING THE STAGE_____


# I also implemented imporved sntax for communicating with the DAQ. i.e.   with nidaqmx.Task as ao_task:    This is because if the program closes in the middle of the
# task, this automatically closes the task too and ensure's that the DAQ doesn't stay open. This is possible due to something called context managers. https://realpython.com/python-with-statement/
# After finishing this, I also realize I overcomplicated this program with threading. Threading is great if you want to speed up real time graphing when your data aquisition
# speed is very fast, but it doesn't do much if it is slow like it is in this case.

#_____RESOURCES_____
# https://realpython.com/intro-to-python-threading/#race-conditions




import nidaqmx                                      # for communicating with the DAQ Card                                                                                                                   
from nidaqmx.constants import TerminalConfiguration # import some constants that are used by the nidaqmx module for configuration. This is acually an enum (like a variable withonly certain values)        
import numpy as np                                  # import numpy for various array calculations                                                                                                           
import queue                                        # for ensureing thread safe communication of data between threads (see below). Otherwise, we may end up causing someting called race condictions. https: // realpython.com/intro-to-python-threading/ # race-conditions
import time                                         # for taking initial time of measurements and calculating delta t                                                                                       
import threading                                    # for speeding up plotting. This ensures our program doesn't have to wait (be blocked) each time we want to take a readings from the DAQ.               
import matplotlib.pyplot as plt                     # for setting up our plot                                                                                                                               
from matplotlib.animation import  FuncAnimation     # for animating our plot of the data                                                                                                                    
import logging                                      # for debugging and logging purposes                                                                                                                    
from matplotlib import ticker                       # for setting up the x-axis ticks on the plot                                                                                                           
import pandas as pd                                 # for saving data as a .csv                                                                                                                             



device = "Dev2"            # your device number                                                                                                                                                                               
ai_channel = "ai0"         # tour analog input channel                                                                                                                                                                        
ao_channel = "ao0"         # ytour analog output channel                                                                                                                                                                      

sample_rate = 10000        # your desired sample rate                                                                                                                                                                         
samples_per_point = 10000  # the number of samples taken per point. Try and adjust these values to take about one data point per second. If data points are taken too fast you get a lot of noise in your graph.              

plot_queue = queue.Queue() # set up a queue in which to put data to communicate between the main thread (which does all the plotting) and the thread which takes readings from the DAQ.                                       

kp = 6.1115               
ki = 0.2037               
kd = 20                    # 45.8365                                                                                                                                                                                          
set_point = 27             # desired temperature                                                                                                                                                                              
max_val = 5.0              # max voltage to output to the DAQ                                                                                                                                                                 
min_val = 0.0              # min volvtage to outpout to the DAQ                                                                                                                                                               
start_time = time.time()   # the time when we start the program in seconds since Unix epoch (Jan 1 1970). We will subtract this from our acual measurement times to reference since this moment instad of since the Unix epoch
current_time : int         # declare this variable as an integer with no value for later use.                                                                                                                                 
print("Starting nidaqmx tasks and taking initial readings")


def create_logger():
    global logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.warning)
    formatter = logging.Formatter("{levelname} - {message}", style="{")
    console_handler = logging.StreamHandler()
    console_handler.setLevel("DEBUG")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

pid_state = threading.local()          # create an instance of the threading.local() class which will be specific to each thread

def initialize_pid_states():           # will be used to initialize properties of the pid_state instance within each thread     
    pid_state.old_time = time.time()   # this will be used in the pid_control function                                          
    pid_state.old_process_variable = 0 # this will be used in the pid_control function                                          
    pid_state.old_integral = 0         # this will be used in the pid_control function

def thread_start_up():                                                                                                   # The purpose of this function"""  is to initialize the data variables with our first data_point                                                                     
    global control_plot_data, temp_plot_data, set_point_plot                                                             # ensure we can edit the data variables  inside this function                                                                                                        
    old_time = time.time()                                                                                               # for calculating dt later in this function                                                                                                                          
    with nidaqmx.Task() as ao_task:                                                                                      # better syntax for communicating with DAQ card                                                                                                                      
        ao_task.ao_channels.add_ao_voltage_chan(f"{device}/{ao_channel}")                                                # add an analog output channel to the task                                                                                                                           
        ao_task.start()                                                                                                  # start the task                                                                                                                                                     
        ao_task.write(0)                                                                                                 # write 0 volts to the DAQ card                                                                                                                                      
        with nidaqmx.Task() as ai_task:                                                                                  # start a task to communicate with the DAQ card                                                                                                                      
            ai_task.ai_channels.add_ai_voltage_chan(f"{device}/{ai_channel}",terminal_config=TerminalConfiguration.DIFF) # add an analog input task and configure it to compare readings from the positive analog in 0 terminal to the negative analog in 0 terminal (not to ground like .RSE)
            ai_task.timing.cfg_samp_clk_timing(sample_rate,samps_per_chan=samples_per_point)                             # ens """ure the DAQ card takes samples_per_ppint many samples at a rate set by sample_rate
            ai_task.start()                                                                                              # satrt the analog input task                                                                                                                                        
            data = ai_task.read(number_of_samples_per_channel=samples_per_point)                                         # read samples_per_point many data points                                                                                                                            
            ai_task.stop()                                                                                               # stop the analog input task                                                                                                                                         
        ao_task.stop()                                                                                                   # stop the analog output task                                                                                                                                        
    data = np.mean(data)                                                                                                 # take the mean of the collected samples                                                                                                                             
                                                                                                                        
    print("Setting up pid_states, and plot for a thread")                                                               
    initialize_pid_states()                                                                                              # initialized the pid_state properites for whichever thread calls this (thread_start_up) function                                                                    

    process_variable = data                                                                                              # reassign data to process_variable                                                                                                                                  
    process_variable = process_variable * 1000 - 273.15                                                                  # convert voltage to kelvin then to deg C                                                                                                                            
    error = set_point - process_variable                                                                                 # calculate the error between the set point and the actual temperature                                                                                               
    current_time = time.time()                                                                                           # get the current time since Unix epoch                                                                                                                              
    dt = current_time - old_time                                                                                         # calculate delta t                                                                                                                                                  

    proportional = kp * error                                                                                            # calculate the proportional term                                                                                                                                    
    integral = ki * error * dt                                                                                           # calculate the integral term                                                                                                                                        
    derivative = -kd * ((process_variable)/dt)                                                                           # calcyulate the derinvative term                                                                                                                                    
    control_output = proportional + integral + derivative                                                                # calculate the sum of the terms to and assign it to control output                                                                                                  

    control_plot_data = np.array([[0], [error], [proportional], [integral], [derivative], [control_output]])             # create a new variable where we will store PID control data to plot                                                                                                 
    temp_plot_data = np.array([[0],[process_variable]])                                                                  # create a new variable where we will store temperatiure data to plot                                                                                                
    set_point_plot = np.array([set_point])                                                                               # create a new variable where we willstore set point data to plot                                                                                                    
    pid_state.old_time = current_time                                                                                    # set old time as now
    return control_output 

def read_daq():                                                                                                      # create a function to read data from the DAQ card                                                                                                                   
    with nidaqmx.Task() as ai_task:                                                                                  # start a task to communicate with the DAQ card                                                                                                                      
        ai_task.ai_channels.add_ai_voltage_chan(f"{device}/{ai_channel}",terminal_config=TerminalConfiguration.DIFF) # add an analog input task and configure it to compare readings from the positive analog in 0 terminal to the negative analog in 0 terminal (not to ground like .RSE)
        ai_task.timing.cfg_samp_clk_timing(sample_rate,samps_per_chan=samples_per_point)                             # ensure the DAQ card takes samples_per_ppint many samples at a rate set by sample_rate                                                                              
        ai_task.start()                                                                                              # satrt the analog input task                                                                                                                                        
        data = ai_task.read(number_of_samples_per_channel=samples_per_point)                                         # read samples_per_point many data points                                                                                                                            
        ai_task.stop()                                                                                               # stop the analog input task                                                                                                                                         
        data_point = np.mean(data)                                                                                   # a=take the average of the data to reduce noise                                                                                                                     
    return data_point                                                                                                # return the averaged data point

def pid_controller(kp, ki, kd, set_point, max_val=5, min_val=0.5):                                                                    # create a function to calculate the P, I, and D components of the controller                                                              
    process_variable = read_daq()                                                                                                     # request data from the DAQ and return the data point                                                                                      
    process_variable = (process_variable * 1000) - 273                                                                                # convert voltage to kelvin then to deg C                                                                                                  
    error = set_point - process_variable                                                                                              # calculate the error between the setpoint and the actual temperature                                                                      
    current_time = time.time()                                                                                                        # get the current time relative to the Unix epoch                                                                                          
    dt = current_time - pid_state.old_time                                                                                            # calculate delta t (using pid_state because this will be called inside the thread and pid_state is a thread local class)                  
    relative_time = pid_state.old_time + dt - start_time                                                                              # calculate the time this measurement was taken relative to start time (not Unix epoch)                                                    


    proportional = kp * error                                                                                                         # calculate the proportional term                                                                                                          
    integral = pid_state.old_integral + ki * error * dt                                                                               # calculate the integrak term                                                                                                              
    derivative = -kd * ((process_variable - pid_state.old_process_variable)/dt)                                                       # calculate the derivatve term                                                                                                             
    control_output = proportional + integral + derivative                                                                             # calculate the sum of the terms to and assign it to control output                                                                        

    if control_output > max_val:                                                                                                      # clip control output to a max value and don't integrate if the control output is above the maximum value set at the top of the program    
        control_output = max_val                                                                                                     
        integral = control_output - proportional - derivative                                                                        
        if integral > max_val:                                                                                                        # if the integral is still higher than the maximum value, clip it                                                                          
            integral = max_val                                                                                                       
    if control_output < min_val:                                                                                                      # if the control output is lower than the minimum value set at the top ofthe program, clip it                                              
        control_output = min_val                                                                                                     
    if integral < 0:                                                                                                                  # if the integral term is negative, make it zero                                                                                           
        integral = 0                                                                                                                 

    pid_state.old_time = current_time                                                                                                 # update the old time to reference next time                                                                                               
    pid_state.old_integral = integral                                                                                                 # update the old integral to reference next time                                                                                           
    pid_state.old_process_variable = process_variable                                                                                 # update the old temperature to reference next time                                                                                        

    logger.debug(f"output: {control_output}, error: {error}, proportional: {proportional}, integral: {integral}, derivative: {derivative}" )


    plot_queue.put((relative_time, error, proportional, integral, derivative, control_output, process_variable))                      # add the new P, I, D and control vatiables to a queue so the main thread (the one that plots) can use them whenm it is ready              
    return control_output                                                                                                             # return the control output to the parent function (daq_task_loop), so that it will output this to the DAQ card to increase the temperature

def daq_task_loop(kp, ki, kd, set_point, max_val=5, min_val=0.5):                                               # this is the MAIN FUNCTION of the program that will continually read values, update P, I, and D values and output voltages
    thread_start_up()                                                                                          
    create_logger()                                                                                             # initialize the plot data arrays, and the thread local class instances for pid_state                                      
    for i in range(400):                                                                                        # rund the following 400 times                                                                                             
        new_output = pid_controller(kp, ki, kd, set_point, max_val, min_val)                                    # get the control output value calulated by the pid_controller function                                                    
        with nidaqmx.Task() as ao_task:                                                                         # initialize an nidaqmx task to communicate with the DAQ card                                                              
            ao_task.ao_channels.add_ao_voltage_chan(f"{device}/{ao_channel}", min_val=min_val, max_val=max_val) # add an analog out channel to the task                                                                                    
            ao_task.write(new_output)                                                                           # write the output generated by the pid function to the task                                                               
            logger.debug(f"outputted {new_output}")                                                            
            ao_task.stop()                                                                                      # stop the task

def update(frames):                                                                                                                                      # This function is used to update the graph and will be called behind the scenes by matplotlib.animate.FuncAnimation automatically        
    global control_plot_data, temp_plot_data, set_point_plot                                                                                             # ensure these variables can be edited inside this function                                                                               
    try:                                                                                                                                                 # use a try except loop to gracefully handle any errors that could stop the program                                                       
        relative_time, error, proportional, integral, derivative, control_output, new_temp = plot_queue.get_nowait()                                    
                                                                                                                                                        
    except:                                                                                                                                              # some errors that may occur could include the queue being empty, or currently being occupied by pid_controller putting data to the queue.
                                                                                                                                                         # Try writing the following to see what specific errors you get--> except Exception as e:                                                 
                                                                                                                                                         # print(e)                                                                                                                                
        return [temp_line, set_point_line, co_line, proportional_line, integral_line, derivative_line]                                                   # this returns the previous value of these variables witgout modifying them and stops the function                                        
                                                                                                                                                        
    temp_plot_data = np.hstack((temp_plot_data, np.array([[relative_time], [new_temp]])))                                                                # stack the new data horizontally onto the old data                                                                                       
    control_plot_data = np.hstack((control_plot_data, np.array([[relative_time], [error], [proportional], [integral], [derivative], [control_output]]))) # stack the new data horizontally onto the old data
    set_point_plot = np.hstack((set_point_plot, np.array([set_point])))                                                                                  # stack the new data horizontally onto the old data                                                                                       
    temp_line.set_data(temp_plot_data[0], temp_plot_data[1])                                                                                             # set new values to display for the temperature line                                                                                      
    set_point_line.set_data(control_plot_data[0], np.full_like(control_plot_data[0], set_point_plot))                                                    # set new values to display for the set point line                                                                                        
    co_line.set_data(control_plot_data[0], control_plot_data[5])                                                                                         # set new values to display for the control output line                                                                                   
    proportional_line.set_data(control_plot_data[0], control_plot_data[2])                                                                               # set new values to display for the proportional line                                                                                     
    integral_line.set_data(control_plot_data[0], control_plot_data[3])                                                                                   # set new values to display for the integral line                                                                                         
    derivative_line.set_data(control_plot_data[0], control_plot_data[4])                                                                                 # set new values to display for the deriavetive line                                                                                      

    logger.info(f"{relative_time}")                                                                                                                      # for helping me to debug

# To Create a Moving X-Axis
    if temp_plot_data.shape[1] > 0:                                                                # if we have collected more than one data point (this won't work if there is no data)       
        xmax = temp_plot_data[0, -1]                                                               # retrieve the last time recorded                                                           
        xmin = 0                                                                                   # we want our time to always be zero                                                        
        ticks = np.linspace(xmin, xmax, 5)                                                         # create 5 evenly spaced (linearly spaced) ticks                                            
        axs["temperature"].set_xlim(xmin, xmax)                                                    # set the x limits                                                                          
        axs["temperature"].set_xticks(ticks)                                                       # set x-ticks                                                                               
        axs["temperature"].set_xticklabels([f"{tick:.1f}" for tick in ticks])                      # Format x-tick labels to one decimal place                                                 


                                                                                                   # For PID plot                                                                              
    if control_plot_data.shape[1] > 0:                                                             # if we have collected more than one data point (this won't work if there is no data)       
        xmax = control_plot_data[0, -1]                                                            # retrieve the last time recorded                                                           
        xmin = 0                                                                                   # we want our time to always be zero                                                        
        ticks = np.linspace(xmin, xmax, 5)                                                         # create 5 evenly spaced (linearly spaced) ticks                                            
        axs["pid"].set_xlim(xmin, xmax)                                                            # set the x limits                                                                          
        axs["pid"].set_xticks(ticks)                                                               # set x-ticks                                                                               
        axs["pid"].set_xticklabels([f"{tick:.1f}" for tick in ticks])                              # Format x-tick labels to one decimal place                                                 
                                                                                                  
    return [temp_line, set_point_line, co_line, proportional_line, integral_line, derivative_line] # return each line to FuncAnimation inside a list because this is what FuncAnimation expects




t = threading.Thread(target=daq_task_loop, args=(kp, ki, kd, set_point, max_val, min_val)) # create a thread that will run daq_task_loop to collect data and update the output voltage
t.daemon = True                                                                            # make this thread finnish the function before stopping when we close the program          
t.start()                                                                                  # start the thread!



fig, axs = plt.subplot_mosaic([["temperature", "temperature"],
                               ["pid", "pid"]])  # create a figure with two axes arranged in a specific way https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.subplot_mosaic.html

temp_line, = axs['temperature'].plot([],[], label="temperature")     # create lines associated with each set of axes                                                                          
set_point_line, = axs['temperature'].plot([],[], label="set point" ) # NOTE: the comma is very important as .plot() will return a tupple of Line2D objects and we only want the first one
co_line, = axs['pid'].plot([],[], label="output")                    # this is called tuple unpacking and it allows us to edit the Line2D object later
proportional_line, = axs['pid'].plot([],[], label="proportional") 
integral_line, = axs['pid'].plot([],[],label="integral")
derivative_line, = axs['pid'].plot([],[],label="derivative")

# formatting the plots...
axs["temperature"].set_ylim(20,35)
axs["temperature"].legend()
axs["temperature"].set_xlabel("Time (s)")
axs["temperature"].set_ylabel("Temperature (°C)")
axs["pid"].set_ylim(-15,15)
axs["pid"].legend(ncols=4)
axs["pid"].set_xlabel("Time (s)")
axs["pid"].set_ylabel("Voltage (V)")
plt.tight_layout()

ani = FuncAnimation(fig, update, interval=500, blit=False, save_count=None) # create the animation! Turning blitting off allows us to redraw the axes every time it calls update().
#                                                                            blitting is not super important in this case, because we aren't aquireing data very fast
plt.show()                                                                  # show the plot!


temp_data = np.transpose(temp_plot_data)
co_data = np.transpose(control_plot_data)
df = pd.DataFrame(co_data)

df.to_csv("PID and Control Output")








    


