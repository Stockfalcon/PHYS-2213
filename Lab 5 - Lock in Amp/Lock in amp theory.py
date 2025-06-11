import numpy as np
import scipy
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
import tkinter as tk


root = tk.Tk()

min_x = 0
max_x = 1
samples_per_point = 1000


freq = 1/(2*np.pi)
phase = 0
sin_freq = 1

t = np.linspace(min_x,max_x, samples_per_point)
x1 = 0.5*(scipy.signal.square(freq * t + phase)+1)
x2 = [np.sin(sin_freq*i) for i in t]

m = np.multiply(x1, x2)


fig, ax = plt.subplot_mosaic([["square","sin", "mult"]])
square, = ax["square"].plot(t,x1,label="square")
sin, = ax["sin"].plot(t, x2, label="sin")
mult, = ax["mult"].plot(t, m, label="mult")

ticks = np.linspace(min_x, max_x, 5)
#tick_labels = [f"{tick/np.pi:.1f} Pi" for tick in ticks]
tick_labels = [f"{tick:.1f}" for tick in ticks]
ax["mult"].set_ylim(np.min(m)-0.05, np.max(m)+0.05)
ax["sin"].set_ylim(np.min(x2)-0.05, np.max(x2)+0.05)
ax["square"].set_xticks(ticks)
ax["sin"].set_xticks(ticks)
ax["mult"].set_xticks(ticks)
ax["square"].set_xticklabels(tick_labels)
ax["sin"].set_xticklabels(tick_labels)
ax["mult"].set_xticklabels(tick_labels)

def update_freq(val):
    global freq
    freq=float(val)/(2*np.pi)
    redraw()

def update_phase(val):
    global phase
    phase=float(val)*(np.pi/180)
    redraw()

def x_max_update(val):
    global max_x
    max_x=float(val)*np.pi
    redraw()

def update_sin(val):
    global sin_freq
    sin_freq = float(val)
    redraw()
    
def redraw():
    t = np.linspace(min_x,max_x, samples_per_point)
    x1 = 0.5*(scipy.signal.square(freq * t + phase)+1)
    x2 = [np.sin(sin_freq*i) for i in t]
    m = np.multiply(x1, x2)
    square.set_data(t,x1)
    sin.set_data(t,x2)
    mult.set_data(t,m)
    average = np.mean(m)
    average_label["text"] = f"avg {round(average,3)}"
    ax["mult"].set_ylim(np.min(m)-0.05, np.max(m)+0.05)
    ax["sin"].set_ylim(np.min(x2)-0.05, np.max(x2)+0.05)
    ax["square"].set_xlim(0,max_x)
    ax["sin"].set_xlim(0,max_x)
    ax["mult"].set_xlim(0,max_x)
    ticks = np.linspace(min_x, max_x, 5)
    # tick_labels = [f"{tick/np.pi:.1f} Pi" for tick in ticks]
    tick_labels = [f"{tick:.1f}" for tick in ticks]
    ax["square"].set_xticks(ticks)
    ax["sin"].set_xticks(ticks)
    ax["mult"].set_xticks(ticks)
    ax["square"].set_xticklabels(tick_labels)
    ax["sin"].set_xticklabels(tick_labels)
    ax["mult"].set_xticklabels(tick_labels)
    canvas.draw()

    




canvas = FigureCanvasTkAgg(fig, root)
canvas.draw()
toolbar = NavigationToolbar2Tk(canvas=canvas,window=root, pack_toolbar=False)
toolbar.update()


freq_frame = tk.Frame(master=root)
phase_frame = tk.Frame(master=root)
x_max_frame = tk.Frame(master=root)
sin_frame = tk.Frame(master=root)
slider_freq = tk.Scale(master=freq_frame, from_=1, to_=10, resolution=1, orient=tk.VERTICAL, command=update_freq, length=500, width=20)
slider_phase = tk.Scale(master=phase_frame, from_=0, to_=180, resolution=1, orient=tk.VERTICAL, command=update_phase, length=500, width=20)
freq_label = tk.Label(master=freq_frame, text="[Hz]", font="14")
phase_label = tk.Label(master=phase_frame, text="[deg]", font="14")
x_max_slider = tk.Scale(master=x_max_frame, from_=1, to_=25, resolution=1, orient=tk.HORIZONTAL, command=x_max_update, length=500, width=20)
x_max_label = tk.Label(master=x_max_frame, text="x max", font="14")
average_label = tk.Label(master=x_max_frame, text=f"avg {0}", font="14",padx=11,pady=10, background="gray10", foreground="white")
slider_sin_freq = tk.Scale(master=sin_frame, from_=1, to_=10, resolution=1, orient=tk.VERTICAL, command=update_sin, length=500, width=20)
sin_label = tk.Label(master=sin_frame, text="sin freq", font="14")






slider_freq.pack(side=tk.BOTTOM)
freq_label.pack(side=tk.BOTTOM)
freq_frame.pack(side=tk.LEFT)

slider_phase.pack(side=tk.BOTTOM)
phase_label.pack(side=tk.BOTTOM)
phase_frame.pack(side=tk.LEFT)

x_max_label.pack(side=tk.RIGHT)
x_max_slider.pack(side=tk.RIGHT)
average_label.pack(side=tk.RIGHT)
x_max_frame.pack(side=tk.BOTTOM)

slider_sin_freq.pack(side=tk.BOTTOM)
sin_label.pack(side=tk.TOP)
sin_frame.pack(side=tk.RIGHT)

canvas.get_tk_widget().pack(side=tk.BOTTOM, expand=True, fill="both")


root.mainloop()