import nidaqmx
from nidaqmx.constants import TerminalConfiguration, Edge, AcquisitionType
import numpy as np
import time
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import pandas as pd

device = "dev1"
load_cell_chan = "ai0"
sync = "ctr0"
sample_rate = 5000
samples_per_point = 1000

lead = 8 # this is the technical name for how much the lead screw will move the nut upwards in one rotation in mm
step_angle = 1.8 # in degrees
gear_reduction = 1/27 # from the planetary gearbox

revolutions_per_step = (step_angle * gear_reduction) / 360
distance_per_step = revolutions_per_step * lead

m, b = 0, 0

stress_vs_strain = []

def read_load():
    with nidaqmx.Task() as ai_task:
        ai_task.ai_channels.add_ai_voltage_chan(f"{device}/{load_cell_chan}", terminal_config=TerminalConfiguration.DIFF)
        ai_task.timing.cfg_samp_clk_timing(rate=sample_rate, samps_per_chan=samples_per_point, active_edge=Edge.RISING)
        ai_task.start()
        readings = ai_task.read(number_of_samples_per_channel=samples_per_point)
        return readings

def calibrate():
    global m, b
    cal = True
    index = 0
    calibration_voltages = []
    calibration_masses = []
    while cal == True:
        calibration_masses.append(float(input(f"🔧 Calibration point #{index}: Enter known mass in grams.")))
        input("⚡ Press enter when ready to take reading.")
        calibration_voltages.append(np.mean(read_load()))
        index += 1
        go = input("Add another calibration point? (y/n)")
        if go.lower() == "y":
            cal = True
        else:
            cal = False
    
    coeffs = np.polyfit(np.array(calibration_voltages), np.array(calibration_masses),1)
    print(f"found coefficients! {coeffs}")
    m, b = coeffs[0], coeffs[1]
    time.sleep(1)

def get_force(voltage):
    mass = m * voltage + b
    force = mass * 9.81
    return mass

def read_sync_and_load():
    with nidaqmx.Task() as ai_task:
        ai_task.ai_channels.add_ai_voltage_chan(f"{device}/{load_cell_chan}", terminal_config=TerminalConfiguration.DIFF)
        ai_task.timing.cfg_samp_clk_timing(rate=sample_rate, samps_per_chan=samples_per_point, active_edge=Edge.RISING)

        ai_task.start()
        readings = ai_task.read(number_of_samples_per_channel=samples_per_point)

        count = ctr_task.read()
        
    return readings, count

def calculations(readings, count):
    avg = np.mean(readings)
    stress = get_force(avg)
    strain = count * distance_per_step

    return stress, strain

def setups():
    global stress_vs_strain, ctr_task
    global fig, axs, line, stress_vs_strain
    fig, axs = plt.subplot_mosaic([["StressStrain"]])
    line, = axs["StressStrain"].plot([],[],label="SS")

    ctr_task = nidaqmx.Task()
    ctr_task.ci_channels.add_ci_count_edges_chan(f"{device}/{sync}",edge=Edge.FALLING) # only 5V logic
    ctr_task.start()

    readings, count = read_sync_and_load()
    stress, strain = calculations(readings, count)
    stress_vs_strain = np.array([[strain], [stress]])



    axs["StressStrain"].legend()
    


    
def graph_update(frame):
    global stress_vs_strain
    try:
        readings, count = read_sync_and_load()
        stress, strain = calculations(readings, count)

        stress_vs_strain = np.hstack((stress_vs_strain, np.array([[strain],[stress]])))

        print(f"\n\n{stress}\n\n")

        line.set_data(stress_vs_strain[0], stress_vs_strain[1])
        axs["StressStrain"].set_xlim(0,np.max(stress_vs_strain[0]))
        axs["StressStrain"].set_ylim(np.min(stress_vs_strain[1]),np.max(stress_vs_strain[1]))
        x_ticks = np.linspace(np.min(stress_vs_strain[0]), np.max(stress_vs_strain[0]), 10)
        y_ticks = np.linspace(np.min(stress_vs_strain[1]), np.max(stress_vs_strain[1]), 10)
        axs["StressStrain"].set_xticks(x_ticks)
        axs["StressStrain"].set_xticklabels([round(i,1) for i in x_ticks])
        axs["StressStrain"].set_yticks(y_ticks)
        axs["StressStrain"].set_yticklabels([round(i,1) for i in y_ticks])

    except KeyboardInterrupt as e:
        # print(e)
        pass

    return [line]

def cleanup():
    ctr_task.stop()
    ctr_task.close()

def counter_check():
    go = 0
    while go == 0:
        readings, count = read_sync_and_load()
        if count == 0:
            pass
        else:
            go = 1 



calibrate()
setups()
print(f"\n\n\nPlease turn on a function generator with a digital signal at a maximum frequency of 1 kHz.\n\n\n")
counter_check()
anim = FuncAnimation(fig, graph_update, blit=False)
plt.show()
cleanup()

df = pd.DataFrame(stress_vs_strain)
df = df.transpose()
df.to_csv(r"C:\Users\lenovo\OneDrive - Acadia University\Summer 2025\Python\PHYS-2213\Lab 7- Tensile Tester\Stress Strain Data.csv")