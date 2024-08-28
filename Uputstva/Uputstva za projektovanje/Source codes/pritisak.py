import serial
import threading
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import serial.tools.list_ports

from scipy.optimize import curve_fit
from scipy.signal import find_peaks

from matplotlib.figure import Figure

# Import the library
from scipy.signal import savgol_filter

# Automatically finding available COM ports
def find_com_port():
    ports = serial.tools.list_ports.comports()
    available_ports = [port.device for port in ports]
    return available_ports

# Making port list
ports = find_com_port()

# Create a Tkinter window
root = tk.Tk()
root.title("Zavod za fiziku tehničkih fakulteta - Vežba Cp/Cv")

#Putanja do ikonice
icon_path = 'icon/zafi_logo.ico'
# Postavljanje ikonice prozora
root.iconbitmap(default=icon_path)

root.minsize(800, 600)

# Create a figure and axis for the plot
fig, ax = plt.subplots()
line1, = ax.plot([], [], label='Pritisak')
line2, = ax.plot([], [], label='Temperatura')
ax.grid()
ax.legend()
ax.set_ylabel('Pritisak [mbar]', rotation=90, labelpad=20)
ax.set_xlabel('Vreme t[s]')

# Create a Tkinter canvas to embed the plot
canvas = FigureCanvasTkAgg(fig, master=root)
canvas_widget = canvas.get_tk_widget()
canvas_widget.pack()

# Declare global variables
global global_data1, global_data2, data_counter, is_collecting
is_collecting = False
global_data1 = []  # Reset the data for the first reading
global_data2 = []  # Reset the data for the second reading
data_counter = 0

toolbar_flag=0
start_flag=0

ss1=0
ss2=0

label1=None
label2=None

# Reading serial data
def read_serial():
    global data_counter, is_collecting, smoothed_data1, smoothed_data2

    y_vals1 = []
    y_vals2 = []

    # ports[-1] - last element of array
    ser = serial.Serial(ports[-1], 9600)  # Replace "ports[0]" with your Arduino's COM port if using multiple COM ports

    cnt1 = 0
    pressure_mean = 0
    pressure_mean_pom = 0

    try:
        while is_collecting:
            data = ser.readline().decode().strip()
            if data:
                data_list = data.split(',')
                if len(data_list) == 2:  # Modify for two data streams
                    data1 = int(data_list[0])
                    data2 = int(data_list[1])

                    # Skip the first 4 data points
                    if data_counter < 4:
                        data_counter += 1
                        continue

                    if cnt1 != 100:
                        if cnt1 < 50:
                            pressure_mean_pom += data1
                            cnt1 += 1
                        else:
                            pressure_mean = pressure_mean_pom / cnt1
                            cnt1 = 100

                    # Scaling if needed
                    zeroing_data1 = data1 - pressure_mean  # Nuliranje pritiska
                    scaled_data1 = (zeroing_data1 / 62) * 100
                    scaled_data2 = data2 / 10  # Modify scaling if required

                    global_data1.append(scaled_data1)
                    global_data2.append(scaled_data2)

                    try:
                        y_vals1.append(scaled_data1)
                        y_vals2.append(scaled_data2)

                        x_vals = np.arange(len(y_vals1)) * 0.05  # Scaled to display in seconds

                        # Apply a moving average filter
                        window_size = 5  # Adjust as needed
                        smoothed_data1 = np.convolve(y_vals1, np.ones(window_size)/window_size, mode='valid')
                        smoothed_data2 = np.convolve(y_vals2, np.ones(window_size)/window_size, mode='valid')

                        line1.set_xdata(x_vals[:len(smoothed_data1)])
                        line1.set_ydata(smoothed_data1)

                        line2.set_xdata(x_vals[:len(smoothed_data2)])
                        line2.set_ydata(smoothed_data2)

                        min_y = min(min(smoothed_data1), min(smoothed_data2))
                        max_y = max(max(smoothed_data1), max(smoothed_data2))
                        if min_y == max_y:
                            min_y -= 1
                            max_y += 1

                        ax.set_xlim(0, len(smoothed_data1) * 0.05)  # Scaled to display in seconds
                        ax.set_ylim(min_y-5, max_y+5)

                        canvas.draw()

                    except ValueError:
                        pass

    except KeyboardInterrupt:
        print("Serial communication stopped.")
        ser.close()

# Function to start collecting data
def start_collection():
    global is_collecting, data_counter, start_flag
    is_collecting = True
    data_counter = 0
    threading.Thread(target=read_serial).start()
    start_flag=1
    
def info_data():
    global ss1, ss2
    pom_flag=0
    for i in range(len(smoothed_data1)-20):
        if smoothed_data1[i]>0.8*max(smoothed_data1) and smoothed_data1[i+20]<0.5 and smoothed_data1[i+20]>-0.5:
            ss1=smoothed_data1[i]
            pom_flag=1
            if pom_flag:
                ss2 = max(smoothed_data1[i+20:])
    
# Function to stop collecting data
def stop_collection():
    global is_collecting, toolbar_flag
    is_collecting = False
    if not toolbar_flag and start_flag:
        add_toolbar()  # Add the toolbar after stopping data collection
        info_data()
        add_labels()
        toolbar_flag=1

# Function to add two labels
def add_labels():
    global label1, label2
    label1 = tk.Label(root, text=f"Prvo stacionarno stanje je {ss1:.2f} mbar")
    label1.pack(side=tk.BOTTOM,before=stop_button)

    label2 = tk.Label(root, text=f"Drugo stacionarno stanje je {ss2:.2f} mbar")
    label2.pack(side=tk.BOTTOM,before=label1)

# Function to add Matplotlib toolbar
def add_toolbar():
    toolbar = NavigationToolbar2Tk(canvas, root)
    toolbar.update()
    canvas_widget.pack_forget()
    canvas_widget.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=1)

# Stop Button
stop_button = tk.Button(root, text="Stop", command=stop_collection)
stop_button.pack(side=tk.BOTTOM, ipadx=10)    

# Start Button
start_button = tk.Button(root, text="Start", command=start_collection)
start_button.pack(side=tk.BOTTOM, ipadx=10)

def on_window_resize(event, canvas):
    canvas.get_tk_widget().pack_forget()  # Remove the canvas
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)  # Re-add the canvas to update its size
    canvas.draw_idle()  # Redraw the canvas

# Bind the function to the window resize event
root.bind("<Configure>", lambda event: on_window_resize(event, canvas))

# Start the Tkinter main loop
root.mainloop()

