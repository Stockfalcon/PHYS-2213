# All code written by Thomas Murimboh except the get frequency function which was written by Chat GTP
# June 15 2025

import nidaqmx
from nidaqmx.constants import TerminalConfiguration, Edge
import numpy as np
import scipy.signal as sig
import scipy.fft as fft
import tkinter as tk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
from matplotlib.figure import FigureBase
import time

device = "Dev3"          # your device number                                   
signal_channel = "ai0"   # your signal channel                                  
sync_channel = "ai1"     # your sync channel                                    
pfi_channel = "PFI0"     # your PFI channel                                     
sample_rate = 1000       # rate in Hz to take samples                           
samples_per_point = 1000 # number of samples that will be averaged              
pad_len = 100            # length of zero padding used in the fourrier transform




root = tk.Tk()                 # create a tkinter window             
root.title("Lock in Amplifer") # name the aplication window          

frequency = 1                  # default frequency of the square wave
phase = 0.0                    # default phase of the square wave

def daq_read(ai_channel):
    with nidaqmx.Task() as ai_task:                                                                                   # create a nidaqmx task                                               
        ai_task.ai_channels.add_ai_voltage_chan(f"{device}/{ai_channel}", terminal_config=TerminalConfiguration.DIFF) # add an analog input                                                 
        ai_task.triggers.start_trigger.cfg_dig_edge_start_trig(f"/{device}/{pfi_channel}", trigger_edge=Edge.RISING)  # trigger this to start collecting data on the rising edge of the sync
        ai_task.timing.cfg_samp_clk_timing(sample_rate, samps_per_chan=samples_per_point)                             # configure the sample clock timing                                   
        data = ai_task.read(number_of_samples_per_channel=samples_per_point)                                          # read samples per point many point
    return data

def create_square_wave():                                              
    t = np.linspace(0, 1, samples_per_point, endpoint=False)            # create samples_per_point many evenly spaced points from 0 to 1
    square_wave = 0.5*(sig.square(2 * np.pi * frequency * t + phase)+1) # generate a square wave with the correct frequency and phase. sig.square actually returns a square wave from -1 to 1, so it had to be shifted and squished a bit.

    return t, square_wave

def update_phase(new_val):                # this will be called whenever we move the slider
    global phase                          # ensure we can edit this variable.              

    phase = float(new_val)                # make the phase a float                         
    t, square_wave = create_square_wave() # make a square wave                             
    reference.set_data(t, square_wave)    # set the data on as the reference line          
    canvas.draw()                         # draw the new lines

def update_plots():
    global frequency                                  # ensure we can edit this variable                                         

    data = daq_read(signal_channel)                   # get data                                                                 
    t, square_wave = create_square_wave()             # create a square wave                                                     

    filtered_signal = np.multiply(data, square_wave)  # multiply the data and the square wave                                    
    average = np.mean(filtered_signal)                # take the average of the multiplied signal. This acts as a low pass filter

    signal.set_data(t, data)                          # set the new data on the top axes                                         
    reference.set_data(t, square_wave)                # set the new data on the bottom axes                                      
    avg_label["text"] = round(average,4)              # update the label to display the new avrerage                             

    ax["signal"].set_xlim(np.min(t), np.max(t))       # reset the x limit of the top axes to match new data                      
    ax["signal"].set_ylim(np.min(data), np.max(data)) # reset the y limit of the top axes to match new data                      
    ax["square"].set_xlim(np.min(t), np.max(t))       # reset the x limit of the bottom axes to match new data                   
    ax["square"].set_ylim(-0.2, 1.2)                  # alwasys a good y axis choice for a square wave                           

    freq = get_frequency(daq_read(sync_channel))      # get the frequncy of the sync channel                                     
    frequency = freq                                  # set the frequency mfor the whole program                                 

    canvas.draw()                                     # updat the canvas                                                         
    root.after(50, update_plots)                      # call this update function again after 50 milliseconds                    

def get_frequency(data):                                      #  Take a fourrier transform of the data and zero-pad it to increase resolution. Here is a good explanation of how this works if you are intrigued: https: // www.bitweenie.com/listings/fft-zero-padding                                   
    N = len(data)                                             #  get the legth  of the data                                                                                                                             
    zero_padded = np.pad(data, (0, pad_len * N), 'constant')  #  10x zero-padding                                                                                                                                       

    fft_vals = fft.fft(zero_padded)                           #  take a fourrier transform of the zero padded data. This ouputs complex numbers symetrically about the x axis becasue our data is real                  
    fft_magnitude = np.abs(fft_vals[:len(zero_padded)         // 2])                                                                                                                                                     #  get the absolute values of each fft point on the right side of the x_axis.     // refers to floor division
    freqs = fft.fftfreq(N, 1 / sample_rate)[:len(zero_padded) // 2]                                                                                                                                                      #  get the corresponding frequencies for each of the corresponding fft magnitudes


    fft_magnitude[0:pad_len] = np.zeros([pad_len])            #  replace the first pad_len number of samples with zeroes. This is because tere is a big spike in fft_magnitudes close to zero.                          
    dominant_freq = freqs[np.argmax(fft_magnitude)]           #  get the frequrency correxponding to the largest fft magnitude. argmax returns the position of the biggest number in the fft_magnitude array            
    print(f"Dominant frequency: {dominant_freq} Hz")          #  print the dominant frequency of the array

    return dominant_freq



fig, ax = plt.subplot_mosaic([["signal"],                                                                       
                             ["square"]])                                                                        # create a figure with two axes
signal, = ax["signal"].plot([],[], label="signal")                                                               # create a line called signal for the top axes. Note: the comma is important for tuple unpacking
reference, = ax["square"].plot([],[], label="square")                                                            # create a line called reference for the bottom axes. Note: the comma is important for tuple unpacking
ax["signal"].legend()                                                                                            # put a legend for the line on the op axes
ax["square"].legend()                                                                                            # put a legend for the line on the op axes
canvas = FigureCanvasTkAgg(fig, master=root)                                                                     # create a canvas for the matplotlib figure using the tkinter backend
canvas.draw()                                                                                                    # draw the initial lines f=on the axes
toolbar = NavigationToolbar2Tk(canvas, root, pack_toolbar=False)                                                 # create a toolbar for the matplotlib axes using the tkinter backend
toolbar.update()                                                                                                 # update the toolbar so that it shows

frame = tk.Frame(master=root)                                                                                    # create a frame to put other tkinter widgets in
slider = tk.Scale(master=frame, command=update_phase, length=400,                                               
                  from_=0, to_=np.pi, resolution=np.pi/100,orient=tk.VERTICAL)                                   # create a sliding scale to update the phase of the square wave
avg_label = tk.Label(master = frame, text=0, background="gray30", foreground="white", font="Arial, 18", width=6) # create a label to display the average value of the multiplied signal

# These lines of code put each widget on the screen. The order in which they are put on the screen matters. Play around with it if you like!
avg_label.pack(side=tk.BOTTOM)
slider.pack(side=tk.BOTTOM)
frame.pack(side=tk.LEFT)
canvas.get_tk_widget().pack(side=tk.BOTTOM, expand=True, fill="both")


root.after(1000, update_plots) # wait 1 second, then start updating the parts               
root.mainloop()                # ensure that tkinter knows to check when you move the slider


