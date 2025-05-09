# Coded by Chat GTP with additions from Thomas Muimboh. Comments by Thomas Murimboh
# May 09 2025

# ----- SETTING THE STAGE -----
# In this program we will be...

import nidaqmx                                                       # This is how we will communicate with the DAQ device                                          
from nidaqmx.constants import AcquisitionType, Edge, WAIT_INFINITELY # import some constants to use in our program                                                  
import matplotlib.pyplot as plt                                      # we will use this librar to plot our data                                                     
from scipy.signal import butter, filtfilt                            # we will use these modules to create coeficients, and apply a filter to our data, respectively
import numpy as np                                                   # for various calculations and arra manipulation.

device = "Dev2" 
ai_channel = "ai0"
PFI_channel = "PFI0"
sample_rate = 1000                         # in samples per second                      
samples_to_read = 1000                     # total number of samples                    
total_time = samples_to_read / sample_rate # used to calculate timestamps for data later


# Create a task
with nidaqmx.Task() as task:
    # Add an analog input voltage channel
    task.ai_channels.add_ai_voltage_chan(f"{device}/{ai_channel}") 

    # Configure sample clock

    task.timing.cfg_samp_clk_timing(rate=sample_rate,
                                     sample_mode=AcquisitionType.FINITE,                          
                                     samps_per_chan=samples_to_read)                               # configure a sample sclock to take consistently timed measurements

# Configure digital edge start trigger on PFI0 (rising edge)
    task.triggers.start_trigger.cfg_dig_edge_start_trig(trigger_source=f"/{device}/{PFI_channel}",
                                                        trigger_edge=Edge.RISING)                  # configure a trigger to start data collection. No data will be taken until triggered

    print("Waiting for trigger on PFI0...")                                                       

# Start the task and read data after trigger
    data = task.read(number_of_samples_per_channel=samples_to_read, timeout=WAIT_INFINITELY)       # read samples when triggered. The program will wait forever if not triggered

    print("Data acquired.")

def butter_bandpass(order, high_pass,low_pass, fs):             # use a butterworth filter to create coefficients that will be used to filter the data later. Create four spaces to input values when the function is called
    niquist = fs * 0.5                                          # The niquist frequenc is based on cool math stuff that is beond the scope of this course https://en.wikipedia.org/wiki/Nyquist_frequency
    high_cut = high_pass / niquist                              # the highcut will be used to cut off frequencies higher than this
    low_cut = low_pass / niquist                                # the lowcut will be used to cut off frequencies lower than this
    a, b = butter(order, [low_cut, high_cut], btype="bandpass") # use scipy's butterworth function to generate coefficients to use later
    return a, b                                                 # return these coeficients to use later

def apply_filter(data, high_pass=40, low_pass=0.5, order=3):                                   # create a function to apply a filter to our data and crreate four spaces to input values and make three of them preset
    a, b = butter_bandpass(order=order, high_pass=high_pass, low_pass=low_pass,fs=sample_rate) # call the butter_bandpass function defined above and pass it the neccessar arguments                                  
    filtered_data = filtfilt(b, a, data)                                                       # use sciy's filtfilt function to aply a filter to our data                                                            
    return filtered_data                                                                       # retun our filtered data

def derive(data):                                       # create a function to create a derivative                                                                                     
    times = np.linspace(0, total_time, samples_to_read) # calculate when each sample was taken                                                                                         
    derivative = np.gradient(data, times)               # calculate the slope beteen each point (a discrete derivative). this function takes it's argument in the form (y_vals, X_vals)
    return derivative                                   # return the derivative of our data


deriv = derive(data)              # create the derivative of our data         
filtered = apply_filter(data)     # created filtered data                     
filtered_deriv = derive(filtered) # create the derivative of our filtered data





# Plot the acquired data
fig, axs = plt.subplots(2,2) # create a figure with four axes to plot data arranged in a 2x2 grid

# setting values for the upper left set of axes
axs[0,0].plot(data)
axs[0,0].set_title("Orginal Data")
axs[0,0].set_xlabel("Sample")
axs[0,0].set_ylabel("Voltage (V)")
axs[0,0].grid(True)

# setting values for the upper right set of axes
axs[0,1].plot(deriv)
axs[0,1].set_title("Derivative of Data")
axs[0,1].set_xlabel("Sample")
axs[0,1].set_ylabel("Voltage (V)")
axs[0,1].grid(True)

# setting values for the lower left set of axes
axs[1,0].plot(filtered)
axs[1,0].set_title("Filtered Data")
axs[1,0].set_xlabel("Sample")
axs[1,0].set_ylabel("Voltage (V)")
axs[1,0].grid(True)

# setting values for the lower right set of axes
axs[1,1].plot(filtered_deriv)
axs[1,1].set_title("Derivative of Filtered Data")
axs[1,1].set_xlabel("Sample")
axs[1,1].set_ylabel("Voltage (V)")
axs[1,1].grid(True)

fig.tight_layout()
plt.show()


