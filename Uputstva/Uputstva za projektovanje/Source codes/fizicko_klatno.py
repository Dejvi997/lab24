import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import tkinter as tk
import numpy as np
import serial
import threading
import serial.tools.list_ports

from scipy.optimize import curve_fit
from scipy.signal import find_peaks

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# Enable LaTeX rendering globaly
#plt.rc('text', usetex=True)

#import matplotlib
#matplotlib.rcParams['text.usetex'] = True
#matplotlib.rcParams['text.latex.preamble'] = [
#    r'\usepackage{graphicx}']

# Automatically finding available COM ports
def find_com_port():
    ports = serial.tools.list_ports.comports()
    available_ports = [port.device for port in ports]
    return available_ports

# Making port list
ports = find_com_port()

# Global variables for data storage
global_data = []

# Function for plotting in tkinter
def plot():
    global global_data, line, canvas, stop_thread
    stop_thread = False
    global_data = []  # Reset the data for new readings

    # Reading serial data
    def read_serial():
        global global_data, line, canvas, stop_thread
        y_vals = []
        
        # ports[-1] - last element of array
        ser = serial.Serial(ports[-1], 9600)  # Replace "ports[0]" with your Arduino's COM port if using multiple COM ports

        try:
            while not stop_thread:
                data = ser.readline().decode().strip()
                if data:
                    data_list = data.split(',')
                    if len(data_list) == 1:  # Modify for a single data stream
                        data1 = int(data_list[0])
                        
                        # Scaling if needed
                        scaled_data = data1/5000*90  # Modify scaling if required
                        global_data.append(scaled_data)

                        try:
                            y_vals.append(scaled_data)

                            x_vals = np.arange(len(y_vals))*0.05 #skalirano je da prikazuje sekunde

                            line.set_xdata(x_vals)
                            line.set_ydata(y_vals)

                            min_y = min(y_vals)
                            max_y = max(y_vals)
                            if min_y == max_y:
                                min_y -= 1
                                max_y += 1

                            ax.set_xlim(0, len(y_vals)*0.05) #Skalirano je da prikazuje sekunde
                            ax.set_ylim(min_y, max_y)

                            canvas.draw()

                        except ValueError:
                            pass

        except KeyboardInterrupt:
            print("Serial communication stopped.")
            ser.close()

    threading.Thread(target=read_serial).start()

# Function for stopping reading data and generating derivative plots
def stop():
    global stop_thread
    stop_thread = True

    # Generate derivative plots
    generate_derivative_plots()

def calculate_period(data):
    data = np.array(data)
    peaks, _ = find_peaks(data)
    troughs, _ = find_peaks(-data)

    # Ensure we have at least two peaks/troughs for calculations
    if len(peaks) >= 2:
        peak_distances = np.diff(peaks)
        #print(np.mean(peak_distances))
        return np.mean(peak_distances)
    #elif len(troughs) >= 2:
    #    trough_distances = np.diff(troughs)
    #    return np.mean(trough_distances)
    else:
        return None
    
# Racunanje logaritmaskog dekrementa
def ln_decrement(data):
    data = np.array(data)
    peaks, _ = find_peaks(data)
    amplitudes = data[peaks]
    
    ratios = []
    for i in range(len(amplitudes) - 1):
        ratio = amplitudes[i] / amplitudes[i + 1]
        ratios.append(ratio)

    average_ratio = np.mean(ratios) if len(ratios) > 0 else None

    if average_ratio is not None:
        ln_average_ratio = np.log(average_ratio)
        return ln_average_ratio
    else:
        return None

def generate_derivative_plots():
    global global_data

    # Calculate first and second derivatives
    first_derivative = np.gradient(global_data)
    second_derivative = np.gradient(first_derivative)
    
    #Fitovanje eksponencijalne funkcije na lokalne maksimume originalnog signala
    # Define the function to fit (exponential decay)
    def envelope_function(x, A, B):
        return A * np.exp(-B * x)
    
    time = np.arange(len(global_data))
    amplitude = np.array(global_data)  #real time data

    # Find peaks or local maxima in the amplitude data
    peaks, _ = find_peaks(amplitude, prominence=0.02)  # Adjust prominence as needed

    # Extract envelope from the peaks
    #print("peaks",type(peaks))
    #print('amplitude',type(amplitude))
    
    x_data = time[peaks]*0.05
    y_data = amplitude[peaks]

    # Fit the function to the data
    params, covariance = curve_fit(envelope_function, x_data, y_data)

    # Extract the fitted parameters
    A_fit, B_fit = params

    # Generate the fitted curve
    y_fit = envelope_function(x_data, A_fit, B_fit)
    
    time_in_s = time*0.05

    # Plotting both derivatives in the same window with subplots
    fig, axs = plt.subplots(2, figsize=(6, 4))
    
    #print(len(time_in_s))
    #print(len(global_data))
    #print(len(x_data))
    #print(len(y_fit))
    #print(len(first_derivative))
    #print(len(second_derivative))
    
    # Izjednacavanje za svaki slucaj
    if len(global_data) > len(time_in_s):
        difference = len(global_data) - len(time_in_s)
        global_data=global_data[:-difference]

    # Plot originalni signal i prvi izvod da bi se videla fazna razlika
    axs[0].plot(time_in_s, global_data, label=r'$\theta(t)$')
    axs[0].plot(x_data, y_fit, 'g', label=r'$A e^{-Bt}$')
    axs[0].plot(time_in_s, first_derivative, 'r', label=r'$\frac{d \theta(t)}{dt}$')
    #axs[0].set_ylabel(r'$\frac{d \theta(t)}{dt}$', rotation=0)
    axs[0].grid()
    axs[0].legend()
    
    # Plot prvi i drugi izvod da se vidi razlika fazna
    axs[1].plot(time_in_s, first_derivative, 'r', label=r'$\frac{d \theta(t)}{dt}$') #plot i prvi derivativ
    axs[1].plot(time_in_s, second_derivative, 'b', label=r'$\frac{d^2 \theta(t)}{dt^2}$')
    axs[1].set_xlabel('t [s]')
    #axs[1].set_ylabel(r'$\frac{d^2 \theta(t)}{dt^2}$', rotation=0)
    axs[1].grid()
    axs[1].legend()
    

    # Calculate the period of input signal
    period = calculate_period(global_data)
    # Scaling period to show in seconds
    period = period * 0.05
    #print(period)
    #print(str(period))
    
    #Prirodni dekrement lambda
    ln_dec = ln_decrement(global_data)
    
    # Show the plot in a tkinter window
    root = tk.Tk()
    root.title("Zavod za fiziku tehničkih fakulteta - Fizičko klatno")  
    
    # Set the minimum window size
    root.minsize(800, 600)  # Adjust these values as needed

    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.get_tk_widget().pack()
    
    # Navigation bar
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    
    # Add Matplotlib toolbar for navigation (zoom, pan, etc.)-------------------------------------
    toolbar = NavigationToolbar2Tk(canvas, root)  #cansvas, root
    canvas_widget.config(cursor="arrow")
    toolbar.update()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
    toolbar.pack(side=tk.TOP, fill=tk.BOTH)
    
    # Add a label for the calculated period
    params_label = tk.Label(root, text=r'Parametri fitovane funkcije su: A = '+str(A_fit)+' B = '+str(B_fit))
    params_label.pack()
    
    # Create a frame to contain the labels
    frame_labels = tk.Frame(root)
    frame_labels.pack(pady=20)  # Add padding to the top and bottom of the frame

    
    # Add a label for the calculated period
    period_label = tk.Label(frame_labels, text=f"Period oscilacija: T = {period:.2f} [s]" if period is not None else "Period T nije izračunljiv")
    period_label.pack(side='left', padx=10)
    
    # Add a label for the calculated logaritmic decrement
    lambda_label = tk.Label(frame_labels, text=f"Logaritamski dekrement: Λ = {ln_dec:.4f}" if ln_dec is not None else r"Logaritamski dekrement Λ nije izračunljiv")
    lambda_label.pack(side='left', padx=10)
    
    
    #Faktor dobrote
    Q = 2*np.pi/(1-np.e**(-2*ln_dec))
    
    # Add a label for the calculated Q faktor dobrote
    Q_label = tk.Label(frame_labels, text=f"Faktor dobrote: Q = {Q:.4f}" if Q is not None else "Faktor dobrote Q nije izračunljiv")
    Q_label.pack(side='left', padx=10)
    
    #Faktor prigusenja
    alpha = ln_dec/period
    
    # Add a label for the calculated Q faktor dobrote
    alpha_label = tk.Label(frame_labels, text=f"Faktor prigušenja: α = {alpha:.4f}" if alpha is not None else "Faktor prigušenja α nije izračunljiv")
    alpha_label.pack(side='left', padx=10)
    

    root.mainloop()

#Putanja do ikonice
icon_path = 'icon/zafi_logo.ico'

root = tk.Tk()
root.geometry("900x600")
root.title("Zavod za fiziku tehničkih fakulteta - Fizičko klatno")
# Postavljanje ikonice prozora
root.iconbitmap(default=icon_path)

# Set minimum window size (optional)
root.minsize(450, 300)  # Set the minimum width and height

fig, ax = plt.subplots()
line, = ax.plot([], [])
ax.set_ylabel(r"$\theta (t)$", rotation=0)
ax.set_xlabel("t [s]")
plt.grid()

# Create a resizable frame inside the window
frame = tk.Frame(root)
frame.pack(fill=tk.BOTH, expand=True)

canvas = FigureCanvasTkAgg(fig, master=frame)
canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

frame = tk.Frame(root)
frame.pack()

tk.Button(frame, text="Pokreni očitavanje", command=plot).pack(pady=10)
tk.Button(frame, text="Zaustavi očitavanje", command=stop).pack(pady=10)

root.mainloop()