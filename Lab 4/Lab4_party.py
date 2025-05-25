# I've decided that This program doesn't work well and isn't worth my thime to fix



import logging.config
import nidaqmx
from nidaqmx.constants import TerminalConfiguration
import numpy as np
import queue
import time
import threading
import matplotlib.pyplot as plt
from matplotlib.animation import  FuncAnimation
import scipy.signal as signal
import logging
import concurrent.futures as futures



# plt.set_loglevel("warning")

class Nidaq():
    def __init__(self):

        self.device = "Dev2"
        self.ai_channel = "ai0"
        self.ao_channel = "ao0"

        self.sample_rate = 10000
        self.samples_per_point = 1000

        self.plot_queue = queue.Queue()
        self.filtered_queue = queue.Queue()
        self.temp_plot_data_queue = queue.Queue()

        self.control_plot_data = np.zeros((6,1))
        self.temp_plot_data = np.zeros((2,1))
        self.set_point_plot = np.zeros((1,1))

        self.kp = 6.1115
        self.ki = 0.2037
        self.kd = 20 #45.8365
        self.set_point = 27
        self.max_val = 5.0
        self.min_val = 0.0
        self.start_time = time.time()
        self.current_time = 0

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.console_handler =  logging.StreamHandler()
        self.console_handler.setLevel(logging.DEBUG)
        self.file_handler = logging.FileHandler("nidaq.log")
        self.file_handler.setLevel(logging.DEBUG)
        self.fileformatter = logging.Formatter('{threadName} - {funcName}:    {levelname} - {message}',style="{")
        self.consoleformatter = logging.Formatter('{funcName}:    {levelname} - {message}',style="{")
        self.console_handler.setFormatter(self.consoleformatter)
        self.file_handler.setFormatter(self.fileformatter)
        self.logger.addHandler(self.console_handler)
        self.logger.addHandler(self.file_handler)

        self.logger.debug("Starting up")
        self.logger.info("Starting nidaqmx tasks and taking initial readings")

    def initialize_pid_states(self):
        logging.debug("initializing pid states")
        self.pid_state = threading.local()
        self.temp_state = threading.local()
        self.pid_state.old_time = time.time()
        self.pid_state.old_process_variable = 0
        self.pid_state.old_integral = 0

    def initialize_graph(self):
        logging.debug("initializing graph")
        fig, axs = plt.subplot_mosaic([["temperature", "temperature"],
                                    ["pid", "pid"]])


        self.temp_line, = axs['temperature'].plot([],[], label="temperature")
        self.set_point_line, = axs['temperature'].plot([],[], label="set point" )
        self.co_line, = axs['pid'].plot([],[], label="output")
        self.proportional_line, = axs['pid'].plot([],[], label="proportional") 
        self.integral_line, = axs['pid'].plot([],[],label="integral")
        self.derivative_line, = axs['pid'].plot([],[],label="derivative")

        axs["temperature"].set_xlim(0,140)
        axs["temperature"].set_ylim(20,35)
        axs["temperature"].legend()
        axs["pid"].set_xlim(0,140)
        axs["pid"].set_ylim(-15,15)
        axs["pid"].legend()
        plt.tight_layout()

        self.ani = FuncAnimation(fig, self.update, interval=1000, blit=False) 

        plt.show()             

    def thread_start_up(self): # The purpose of this function is to initialize the data variables with our first data_point                                             
        global control_plot_data, temp_plot_data, set_point_plot                                                   # ensure we can edit the data variables  inside this function                                                                             
        self.old_time = time.time()
        with nidaqmx.Task() as ao_task:
            ao_task.ao_channels.add_ao_voltage_chan(f"{self.device}/{self.ao_channel}")
            ao_task.start()
            ao_task.write(0)
            ao_task.stop()
        with nidaqmx.Task() as ai_task:
            ai_task.ai_channels.add_ai_voltage_chan(f"{self.device}/{self.ai_channel}",terminal_config=TerminalConfiguration.DIFF)
            ai_task.timing.cfg_samp_clk_timing(self.sample_rate,samps_per_chan=self.samples_per_point)
            ai_task.start()
            data = ai_task.read(number_of_samples_per_channel=self.samples_per_point)
            ai_task.stop()
        data = np.mean(data)
        
        self.logger.info("Setting up pid_states, and plot for a thread")
        self.initialize_pid_states()

        process_variable = data
        process_variable = process_variable * 1000 - 273.15 # convert voltage to kelvin then to deg C
        error = self.set_point - process_variable
        current_time = time.time()
        dt = current_time - self.old_time

        proportional = self.kp * error
        integral = self.ki * error * dt
        derivative = -self.kd * ((process_variable)/dt)
        control_output = proportional + integral + derivative

        control_plot_data = np.array([[0], [error], [proportional], [integral], [derivative], [control_output]])
        temp_plot_data = np.array([[0],[process_variable]])
        set_point_plot = np.array([self.set_point])
        self.pid_state.old_time = current_time
        return control_output

    def read_daq(self):
        self.logger.debug("performing read daq")
        with nidaqmx.Task() as ai_task:
            self.logger.debug("read daq good until ai_task setup ")
            ai_task.ai_channels.add_ai_voltage_chan(f"{self.device}/{self.ai_channel}",terminal_config=TerminalConfiguration.DIFF)
            ai_task.timing.cfg_samp_clk_timing(self.sample_rate,samps_per_chan=self.samples_per_point)
            ai_task.start()
            self.logger.debug("read daq good until read")
            try:
                data = ai_task.read(number_of_samples_per_channel=self.samples_per_point, timeout=3)
                # self.logger.debug(f"new data: {data}")
            except Exception as e:
                    self.logger.info(f'{type(e).__name__}: {e} data: {data}')
            finally:
                self.logger.debug("read daq good until averaging")
                data_point = np.mean(data)
                self.logger.debug(f"mean data:{data_point}")
                ai_task.stop()
            return data_point

    def pid_controller(self, kp, ki, kd, set_point, max_val=5, min_val=0.5):
        self.logger.debug("performing pid controller")
        process_variable = self.read_daq()
        self.logger.debug("pid good until calcs")
        try:
            process_variable = (process_variable * 1000) - 273 # convert voltage to kelvin then to deg C
            error = set_point - process_variable
            current_time = time.time()
            dt = current_time - self.pid_state.old_time
            relative_time = self.pid_state.old_time + dt - self.start_time

            proportional = kp * error
            integral = self.pid_state.old_integral + ki * error * dt
            derivative = -kd * ((process_variable - self.pid_state.old_process_variable)/dt)
            control_output = proportional + integral + derivative

            if control_output > max_val:
                control_output = max_val
                integral = control_output - proportional - derivative
                # integral = pid_state.old_integral
                if integral > max_val:
                    integral = max_val
            if control_output < min_val:
                control_output = min_val
            if integral < 0:
                integral = 0
        except Exception as e:
            self.logger.warning(f'{type(e).__name__}: {e}') 

        self.pid_state.old_time = current_time
        self.pid_state.old_integral = integral
        
        self.logger.debug("pid good until queue 1")
        try:
            self.pid_state.old_process_variable = self.filtered_queue.get_nowait()
            self.logger.debug(f"   got filtered data {self.pid_state.old_process_variable}")
        except Exception as e:
            self.logger.warning(f'{type(e).__name__}: {e}')
        finally:
            self.logger.debug("pid good until queue 2")
            self.logger.info(f"out: {control_output}v, err: {error}, proportional: {proportional}, integral: {integral}, derivative: {derivative}\n" )
            try:
                self.plot_queue.put((relative_time, error, proportional, integral, derivative, control_output, process_variable))
            except Exception as e:
                self.logger.warning(f'{type(e).__name__}: {e}')
                return control_output

    def daq_task(self, kp, ki, kd, set_point, max_val=5, min_val=0.5):
        self.logger.debug(" performing daq task")
        new_output = self.pid_controller(kp, ki, kd, set_point, max_val, min_val)
        with nidaqmx.Task() as ao_task:
                ao_task.ao_channels.add_ao_voltage_chan(f"{self.device}/{self.ao_channel}", min_val=min_val, max_val=max_val)
                ao_task.write(new_output)
                self.logger.debug(f"outputted {new_output}")
                ao_task.stop()

    def update(self, frames):
        self.logger.debug("performing update")
        try:
            relative_time, error, proportional, integral, derivative, control_output, new_temp = self.plot_queue.get_nowait()
            
        except Exception as e:
            self.logger.warning(f'{type(e).__name__}: {e}')
            return [self.temp_line, self.set_point_line, self.co_line, self.proportional_line, self.integral_line, self.derivative_line]
        
        self.temp_plot_data = np.hstack((temp_plot_data, np.array([[relative_time], [new_temp]])))
        self.control_plot_data = np.hstack((control_plot_data, np.array([[relative_time], [error], [proportional], [integral], [derivative], [control_output]])))
        self.set_point_plot = np.hstack((set_point_plot, np.array([self.set_point])))
        self.temp_line.set_data(temp_plot_data[0], temp_plot_data[1])
        self.set_point_line.set_data(control_plot_data[0], set_point_plot)
        self.co_line.set_data(control_plot_data[0], control_plot_data[5])
        self.proportional_line.set_data(control_plot_data[0], control_plot_data[2])
        self.integral_line.set_data(control_plot_data[0], control_plot_data[3])
        self.derivative_line.set_data(control_plot_data[0], control_plot_data[4])

        self.temp_plot_data_queue.put((relative_time, new_temp))
        self.logger.debug(self.temp_plot_data_queue.queue)
        return [self.temp_line, self.set_point_line, self.co_line, self.proportional_line, self.integral_line, self.derivative_line]

    def butterworth_filter(self, order, freq, fs):
        self.logger.debug("performing butterworth filter")
        niquist = 0.5 * fs
        Wn = freq / niquist
        b, a = signal.butter(order, Wn, fs=fs)
        return b, a

    def apply_filter(self, fs, order=3, freq=40):
        self.logger.debug("performing apply filter")
        try:
            time, temp = self.temp_plot_data_queue.get_nowait()
            data = np.array([[time], [temp]])
            logging.debug(f"got data {data}")
            b, a = self.butterworth_filter(order=order, freq=freq, fs=fs)
            filtered_data = signal.filtfilt(b, a, data)
            self.filtered_queue.put(filtered_data[-1])
        except Exception as e:
            self.logger.warning(f'{type(e).__name__}: {e}')
            data=[0]
            return None
            

def write_read(nidaq : Nidaq):
    nidaq.logger.debug("performing reader")
    nidaq.thread_start_up()
    nidaq.daq_task(nidaq.kp, nidaq.ki, nidaq.kd, nidaq.set_point, nidaq.max_val, nidaq.min_val)

def filter(nidaq : Nidaq):
    nidaq.logger.info("performing filter")
    nidaq.apply_filter(nidaq.sample_rate, order=3, freq=40)

nidaq = Nidaq()

def start_background_threads():
    with futures.ThreadPoolExecutor(max_workers=2) as executor:
        nidaq.logger.info("Starting up threads")
        while True:
            executor.submit(write_read, nidaq)
            executor.submit(filter, nidaq)

# Start background threads in a daemon thread so they don't block the main thread
threading.Thread(target=start_background_threads, daemon=True).start()

# Now run the GUI in the main thread
nidaq.initialize_graph()  # This will call plt.show() and block until the window is closed




    
    





    


