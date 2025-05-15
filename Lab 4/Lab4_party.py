import sys
import time
import threading
import numpy as np
import nidaqmx
from nidaqmx.constants import TerminalConfiguration
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLineEdit, QLabel
from pyqtgraph import PlotWidget, PlotDataItem
import queue

class TemperatureControllerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Temperature Controller")
        self.setGeometry(100, 100, 800, 600)

        self.device = "Dev2"
        self.ai_channel = "ai0"
        self.ao_channel = "ao1"
        self.sample_rate = 10000
        self.samples_per_point = 1000
        self.set_point = 27.0  # Default setpoint in °C

        # Initialize DAQ tasks
        self.ai_task = nidaqmx.Task()
        self.ao_task = nidaqmx.Task()
        self.ai_task.ai_channels.add_ai_voltage_chan(f"{self.device}/{self.ai_channel}", terminal_config=TerminalConfiguration.DIFF)
        self.ao_task.ao_channels.add_ao_voltage_chan(f"{self.device}/{self.ao_channel}")
        self.ai_task.timing.cfg_samp_clk_timing(rate=self.sample_rate, samps_per_chan=self.samples_per_point, sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS)

        # PID parameters
        self.kp: float = 0.2037
        self.ki: float = 6.1115
        self.kd: float = 45.8365

        # Initialize GUI components
        self.init_ui()

        # Initialize communication queue
        self.plot_queue = queue.Queue()


        # Initialize plot data
        self.temp_plot_data = np.zeros((2, 1))
        self.control_plot_data = np.zeros((7, 1))
        self.set_point_plot = np.zeros((1, 1))

        self.start_time = time.time()
        self.pid_state = threading.local()
        self.get_data: bool = True

        # Initialize data thread
        self.data_thread = None

        self.start_data_acquisition()

    def init_ui(self):
        layout = QVBoxLayout()

        # Temperature plot
        self.temp_plot = PlotWidget()
        self.temp_plot.setTitle("Temperature vs Time")
        self.temp_plot.setLabel('left', 'Temperature (°C)')
        self.temp_plot.setLabel('bottom', 'Time (s)')
        self.temp_curve = self.temp_plot.plot([], [], pen='g', name='Temperature')
        self.set_point_curve = self.temp_plot.plot([], [], pen='r', name='Set Point')
        layout.addWidget(self.temp_plot)

        # Setpoint input
        self.setpoint_input = QLineEdit(str(self.set_point))
        self.setpoint_input.setPlaceholderText("Enter Setpoint (°C)")
        self.setpoint_input.returnPressed.connect(self.update_setpoint)
        layout.addWidget(self.setpoint_input)

        # Control output plot
        self.control_plot = PlotWidget()
        self.control_plot.setTitle("Control Output vs Time")
        self.control_plot.setLabel('left', 'Control Output')
        self.control_plot.setLabel('bottom', 'Time (s)')
        self.control_plot.setYRange(-10, 10)
        self.proportional_curve = self.control_plot.plot([], [], pen='r', name='Proportional')
        self.integral_curve = self.control_plot.plot([], [], pen='g', name='Integral')
        self.derivative_curve = self.control_plot.plot([], [], pen='orange', name='Derivative')
        self.control_curve = self.control_plot.plot([], [], pen='b', name='Control Output')
        layout.addWidget(self.control_plot)

        # Start/Stop button
        self.start_stop_button = QPushButton("Stop")
        self.start_stop_button.clicked.connect(self.toggle_data_acquisition)
        layout.addWidget(self.start_stop_button)

        # Status label
        self.status_label = QLabel("Status: Running")
        layout.addWidget(self.status_label)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def update_setpoint(self):
        try:
            new_setpoint = float(self.setpoint_input.text())
            self.set_point = new_setpoint
        except ValueError:
            self.status_label.setText("Invalid setpoint value")

    def toggle_data_acquisition(self):
        if hasattr(self, 'data_thread') and self.data_thread is not None and self.data_thread.is_alive():
            self.stop_data_acquisition()
        else:
            self.start_data_acquisition()

    def start_data_acquisition(self):
        
        self.get_data = True
        self.data_thread = threading.Thread(target=self.data_acquisition_loop, args=())
        self.data_thread.daemon = True
        self.data_thread.start()
        self.status_label.setText("Status: Running")
        self.start_stop_button.setText("Stop")

    def init_data_aquisition_loop(self):
        old_time = time.time()
        self.ao_task.start()                                                      # start our analog out task                                                                                                                   
        self.ai_task.start()                                                      # start our analog in task                                                                                                                    
        self.ao_task.write(0)                                          
        data = self.ai_task.read(number_of_samples_per_channel=self.samples_per_point)
        data = np.mean(data)              

        self.pid_state = threading.local()
        self.pid_state.old_time = time.time()
        self.pid_state.old_process_variable = 0
        self.pid_state.old_integral = 0                   
        
        process_variable = data
        process_variable = process_variable * 1000 - 273.15 # convert voltage to kelvin then to deg C
        error = self.set_point - process_variable
        current_time = time.time()
        dt = current_time - old_time

        proportional = self.kp * error
        integral = self.ki * error * dt
        derivative = -self.kd * ((process_variable)/dt)
        control_output = proportional + integral + derivative

        self.control_plot_data = np.array([[0], [error], [proportional], [integral], [derivative], [control_output]])
        self.temp_plot_data = np.array([[0],[process_variable]])
        self.set_point_plot = np.array([self.set_point])
        self.pid_state.old_time = current_time

    def update_plots(self, relative_time, error, proportional, integral, derivative, control_output, temperature):
        self.temp_plot_data = np.hstack((self.temp_plot_data, np.array([[relative_time], [temperature]])))
        self.control_plot_data = np.hstack((self.control_plot_data, np.array([[relative_time], [error], [proportional], [integral], [derivative], [control_output]])))
        self.set_point_plot = np.hstack((self.set_point_plot, np.array([self.set_point])))

        self.temp_curve.setData(self.temp_plot_data[0], self.temp_plot_data[1])
        self.set_point_curve.setData(self.temp_plot_data[0], self.set_point_plot)
        self.control_curve.setData(self.control_plot_data[0], self.control_plot_data[5])
        self.proportional_curve.setData(self.control_plot_data[0], self.control_plot_data[2])
        self.integral_curve.setData(self.control_plot_data[0], self.control_plot_data[3])
        self.derivative_curve.setData(self.control_plot_data[0], self.control_plot_data[4])

    def stop_data_acquisition(self):

        self.get_data = False
        self.data_thread.join()
        self.ai_task.stop()
        self.ao_task.stop()
        self.status_label.setText("Status: Stopped")
        self.start_stop_button.setText("Start")

    def data_acquisition_loop(self):
        self.init_data_aquisition_loop()
        while True:
            process_variable = self.read_temperature()
            relative_time, error, proportional, integral, derivative, control_output, process_variable = self.pid_control(process_variable)
            self.ao_task.write(control_output)

            # Update plots
            self.update_plots(relative_time, error, proportional, integral, derivative, control_output, process_variable)

            time.sleep(1 / self.sample_rate)

    def read_temperature(self):
        data = self.ai_task.read(number_of_samples_per_channel=self.samples_per_point)
        voltage = np.mean(data)
        temperature = (voltage * 1000) - 273.15  # Convert from Kelvin to Celsius
        return temperature

    def pid_control(self, process_variable) -> int:
        error = self.set_point - process_variable
        current_time = time.time()
        dt = current_time - self.pid_state.old_time
        relative_time = self.pid_state.old_time + dt - self.start_time

        proportional = self.kp * error
        integral = self.pid_state.old_integral + self.ki * error * dt
        derivative = self.kd * (process_variable - self.pid_state.old_process_variable) / dt
        control_output = proportional + integral + derivative

        # Saturate control output
        control_output = np.clip(control_output, -10, 10)

        # Update PID state
        self.pid_state.old_time = current_time
        self.pid_state.old_process_variable = process_variable
        self.pid_state.old_integral = integral

        
        return (relative_time, error, proportional, integral, derivative, control_output, process_variable)

    def closeEvent(self, event):
        self.ai_task.stop()
        self.ao_task.stop()
        self.ai_task.close()
        self.ao_task.close()

 
def main():
    app = QApplication([])
    window = TemperatureControllerApp()
    window.show()
    app.exec()

if __name__ == "__main__":
    main()

