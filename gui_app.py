"""
What: A desktop app (tkinter) wrapping sensor_analysis.py's simulation with
      sliders for noise, spike count, filter window, and threshold, so you
      can see how each one changes the plot without editing constants and
      re-running the script.
Why: sensor_analysis.py is a great "how the math works" script, but you have
     to open the file and change numbers to experiment with it. A GUI turns
     it into something someone else can actually play with.
Learned: How to embed a live matplotlib figure inside a tkinter window
      (FigureCanvasTkAgg) and redraw it in place instead of popping a new
      window every time, and that PyInstaller needs matplotlib's Tk backend
      pulled in explicitly (see build_exe.py) or the packaged exe can't
      find it.
"""

import tkinter as tk
from tkinter import ttk

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import sensor_analysis as sa


class SensorApp:
    def __init__(self, root):
        self.root = root
        root.title("Sensor Data Analysis - Pocket Lab")
        root.geometry("900x600")

        self.rng = np.random.default_rng()

        controls = ttk.Frame(root, padding=10)
        controls.pack(side=tk.LEFT, fill=tk.Y)

        self.noise_std = self._add_slider(controls, "Noise std dev (cm)", 0.2, 5.0, sa.NOISE_STD_CM)
        self.spike_count = self._add_slider(controls, "Spike count", 0, 15, sa.SPIKE_COUNT, resolution=1)
        self.window_size = self._add_slider(controls, "Filter window (samples)", 1, 21, sa.WINDOW_SIZE, resolution=2)
        self.threshold = self._add_slider(controls, "Spike threshold (cm)", 1.0, 20.0, sa.SPIKE_THRESHOLD_CM)

        ttk.Button(controls, text="Regenerate", command=self.regenerate).pack(fill=tk.X, pady=(15, 5))
        ttk.Button(controls, text="Save plot as PNG", command=self.save_plot).pack(fill=tk.X)

        self.status = ttk.Label(controls, text="", wraplength=200, justify=tk.LEFT)
        self.status.pack(fill=tk.X, pady=(15, 0))

        self.figure = Figure(figsize=(6, 5), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=root)
        self.canvas.get_tk_widget().pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.regenerate()

    def _add_slider(self, parent, label, lo, hi, default, resolution=0.1):
        ttk.Label(parent, text=label).pack(anchor=tk.W, pady=(10, 0))
        var = tk.DoubleVar(value=default)
        scale = ttk.Scale(parent, from_=lo, to=hi, variable=var, orient=tk.HORIZONTAL)
        scale.pack(fill=tk.X)
        readout = ttk.Label(parent, text=str(default))
        readout.pack(anchor=tk.E)

        def on_move(_event=None, v=var, r=readout, res=resolution):
            snapped = round(v.get() / res) * res if res >= 1 else round(v.get(), 2)
            r.config(text=str(snapped))

        scale.bind("<ButtonRelease-1>", on_move)
        on_move()
        return var

    def regenerate(self):
        window = max(1, int(round(self.window_size.get())))
        if window % 2 == 0:
            window += 1  # keep it odd so the centered padding stays symmetric

        time, readings = sa.simulate_readings(
            noise_std_cm=self.noise_std.get(),
            spike_count=int(round(self.spike_count.get())),
            rng=self.rng,
        )
        smoothed = sa.moving_average(readings, window)
        spikes = sa.find_spikes(readings, smoothed, self.threshold.get())

        self.ax.clear()
        self.ax.plot(time, readings, ".", alpha=0.5, label="Raw (noisy)")
        self.ax.plot(time, smoothed, linewidth=2, label=f"Moving avg (window={window})")
        self.ax.scatter(time[spikes], readings[spikes], color="red", zorder=5, label="Flagged spike")
        self.ax.axhline(sa.TRUE_DISTANCE_CM, color="gray", linestyle="--", linewidth=1)
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Distance (cm)")
        self.ax.legend(loc="upper right", fontsize=8)
        self.canvas.draw()

        self.status.config(text=f"Flagged {len(spikes)} spike(s) out of {len(readings)} readings.")

    def save_plot(self):
        self.figure.savefig("sensor_plot.png", dpi=150)
        self.status.config(text=self.status.cget("text") + "\nSaved to sensor_plot.png")


def main():
    root = tk.Tk()
    app = SensorApp(root)

    import sys
    if "--selftest" in sys.argv:
        # used to smoke-test that the window builds and draws without a human
        # watching - not part of normal usage
        root.update()
        app.save_plot()
        root.after(200, root.destroy)
    root.mainloop()


if __name__ == "__main__":
    main()
