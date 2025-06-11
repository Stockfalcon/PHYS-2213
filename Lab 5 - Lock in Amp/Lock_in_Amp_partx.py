import nidaqmx
from nidaqmx.constants import TerminalConfiguration, Edge
import numpy as np
import scipy.signal as sig
import scipy
import tkinter as tk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
from matplotlib.figure import FigureBase
import time

device = "dev3"
signal_channel = "ai0"
sync_channel = "ai1"
pfi_channel = "PFI0"
counter = "ctr0"
sample_rate = 1000
samples_per_point = 1000



root = tk.Tk()
root.title("Lock in Amplifer")

frequency = 1
phase = 0.0
index = 0

def daq_read(ai_channel):
    with nidaqmx.Task() as ai_task:
        ai_task.ai_channels.add_ai_voltage_chan(f"{device}/{ai_channel}", terminal_config=TerminalConfiguration.DIFF)
        ai_task.triggers.start_trigger.cfg_dig_edge_start_trig(f"/{device}/{pfi_channel}", trigger_edge=Edge.RISING)
        ai_task.timing.cfg_samp_clk_timing(sample_rate, samps_per_chan=samples_per_point)
        data = ai_task.read(number_of_samples_per_channel=samples_per_point)
    return data

def create_square_wave():
    t = np.linspace(0, 1, samples_per_point, endpoint=False) # create samples_per_point many evenly spaced points from 0 to 1
    square_wave = 0.5*(sig.square(2 * np.pi * frequency * t + phase)+1)

    return t, square_wave

def update_phase(new_val):
    global phase

    phase = float(new_val)
    t, square_wave = create_square_wave()
    reference.set_data(t, square_wave)
    canvas.draw()

def update_plots():
    global index, frequency

    data = daq_read(signal_channel)
    t, square_wave = create_square_wave()

    filtered_signal = np.multiply(data, square_wave)
    average = np.mean(filtered_signal)

    signal.set_data(t, data)
    reference.set_data(t, square_wave)
    avg_label["text"] = round(average,4)

    ax["signal"].set_xlim(np.min(t), np.max(t))
    ax["signal"].set_ylim(np.min(data), np.max(data))
    ax["square"].set_xlim(np.min(t), np.max(t))
    ax["square"].set_ylim(-0.2, 1.2)  # For a square wave

    canvas.draw()
    if index >= 10:
        freq = get_frequency()
        frequency = freq
        index = 0
    else:
        index += 1

    root.after(50, update_plots)

def get_frequency():
    with nidaqmx.Task() as counter_task:
        counter_task.ci_channels.add_ci_count_edges_chan(f"{device}/{counter}", edge=Edge.RISING)
        counter_task.ci_channels.ci_count_edge_term = f"/{device}/{pfi_channel}"

        dt = 1
        counter_task.start()
        read1 = counter_task.read()
        time.sleep(dt)
        read2 = counter_task.read()


        count = read2 - read1
        frequency = count / (dt)

        print(frequency)


    return frequency



fig, ax = plt.subplot_mosaic([["signal"],
                             ["square"]])
signal, = ax["signal"].plot([],[], label="signal")
reference, = ax["square"].plot([],[], label="square")
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.draw()
toolbar = NavigationToolbar2Tk(canvas, root, pack_toolbar=False)
toolbar.update()

frame = tk.Frame(master=root)
slider = tk.Scale(master=frame, command=update_phase, length=400, 
                  from_=0, to_=np.pi, resolution=np.pi/100,orient=tk.VERTICAL)
avg_label = tk.Label(master = frame, text=0, background="gray30", foreground="white", font="Arial, 18", width=6)

avg_label.pack(side=tk.BOTTOM)
slider.pack(side=tk.BOTTOM)
frame.pack(side=tk.LEFT)
canvas.get_tk_widget().pack(side=tk.BOTTOM, expand=True, fill="both")

get_frequency()

root.after(1000, update_plots)
root.mainloop()


