# Coded by Chat GTP with additions from Thomas Muimboh. Comments by Thomas Murimboh
# May 09 2025

# ----- SETTING THE STAGE -----
# In this program we will be...

import nidaqmx                                                       # This is how we will communicate with the DAQ device                                          
from nidaqmx.constants import AcquisitionType, Edge, WAIT_INFINITELY # import some constants to use in our program                                                  
import matplotlib.pyplot as plt                                      # we will use this librar to plot our data                                                     
from scipy.signal import butter, filtfilt, freqz                            # we will use these modules to create coeficients, and apply a filter to our data, respectively
import numpy as np                                                   # for various calculations and arra manipulation.

device = "Dev2" 
ai_channel = "ai3"
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
    data = np.array(data)


    print("Data acquired.")

def butter_bandpass(order, cutoff, fs):             # use a butterworth filter to create coefficients that will be used to filter the data later. Create four spaces to input values when the function is called
    niquist = fs * 0.5                                          # The niquist frequenc is based on cool math stuff that is beond the scope of this course https://en.wikipedia.org/wiki/Nyquist_frequency
    normal_cutoff = cutoff / niquist                              # the highcut will be used to cut off frequencies higher than this
    b, a = butter(order, normal_cutoff, analog=False, btype="low") # use scipy's butterworth function to generate coefficients to use later
    return b, a                                                 # return these coeficients to use later

def apply_filter(data, cutoff=10, order=6, fs=1000):                                   # create a function to apply a filter to our data and crreate four spaces to input values and make three of them preset
    b, a = butter_bandpass(order=order, cutoff=cutoff, fs=fs) # call the butter_bandpass function defined above and pass it the neccessar arguments                                  
    filtered_data = filtfilt(b, a, data)                                                       # use sciy's filtfilt function to aply a filter to our data                                                            
    return filtered_data                                                                       # retun our filtered data

def derive(data):                                       # create a function to create a derivative                                                                                     
    times = np.linspace(0, total_time, samples_to_read) # calculate when each sample was taken                                                                                         
    derivative = np.gradient(data, times)               # calculate the slope beteen each point (a discrete derivative). this function takes it's argument in the form (y_vals, X_vals)
    return derivative                                   # return the derivative of our data

def filter_response(data, cutoff=10, order=3, fs=1000): # create a function to plot the filter response and create four spaces to input values and make three of them preset
    b, a = butter_bandpass(order=order, cutoff=cutoff, fs=fs) # call the butter_bandpass function defined above and pass it the neccessar arguments                                  
    w, h = freqz(b, a, worN=2000)
    return w, h, cutoff, fs                             # use scipy's freqz function to calculate the frequency response of our filter
                              # add a grid to the plot

deriv = derive(data)              # create the derivative of our data         
filtered = apply_filter(data)     # created filtered data                     
filtered_deriv = derive(filtered) # create the derivative of our filtered data
w, h, cutoff, fs = filter_response(data) # create the frequency response of our filter




# Plot the acquired data
fig, axs = plt.subplot_mosaic([['filter_response','filter_response'],
                               ['original', 'deriv'],
                               ['filtered', 'filtered_deriv']]) # create a figure with four axes to plot data arranged in a 2x2 grid

axs['filter_response'].plot(0.5 * fs * w / np.pi, np.abs(h), 'b')           # plot the frequency response of our filter
axs['filter_response'].plot(cutoff, 0.5 * np.sqrt(2), 'ko')                 # plot the cutoff frequency
axs['filter_response'].axvline(cutoff, color='k')                           # plot a vertical line at the cutoff frequency
axs['filter_response'].set_xlim(0, 200)                                    # set the x axis limits
axs['filter_response'].set_title("Lowpass Filter Frequency Response")            # set the title of the plot
axs['filter_response'].set_xlabel("Frequency [Hz]")                             # set the x axis label
axs['filter_response'].grid()                 

# setting values for the upper left set of axes
axs["original"].plot(data)
axs["original"].set_title("Orginal Data")
axs["original"].set_xlabel("Sample")
axs["original"].set_ylabel("Voltage (V)")
axs["original"].grid(True)

# setting values for the upper right set of axes
axs['deriv'].plot(deriv)
axs['deriv'].set_title("Derivative of Data")
axs['deriv'].set_xlabel("Sample")
axs['deriv'].set_ylabel("Voltage (V)")
axs['deriv'].grid(True)

# setting values for the lower left set of axes
axs['filtered'].plot(filtered)
axs['filtered'].set_title("Filtered Data")
axs['filtered'].set_xlabel("Sample")
axs['filtered'].set_ylabel("Voltage (V)")
axs['filtered'].grid(True)

# setting values for the lower right set of axes
axs['filtered_deriv'].plot(filtered_deriv)
axs['filtered_deriv'].set_title("Derivative of Filtered Data")
axs['filtered_deriv'].set_xlabel("Sample")
axs['filtered_deriv'].set_ylabel("Voltage (V)")
axs['filtered_deriv'].grid(True)

fig.tight_layout()
plt.show()


