"""
What: Simulates noisy ultrasonic distance readings (like the HC-SR04 on my
      arduino-parking-sensor project), then cleans them up with a moving
      average filter and flags sudden spikes as alerts.
Why: I wanted to practice real signal processing on data that behaves like
     my actual sensor instead of a clean textbook sine wave - ultrasonic
     sensors are noisy and occasionally return garbage readings, and I
     wanted to see how a simple filter handles that.
Learned: How a moving average smooths out noise but also lags behind real
     changes, how to pick a threshold that catches real spikes without
     flagging every bit of noise, and that numpy's vectorized operations
     are way faster (and less code) than looping over readings by hand.
"""

import numpy as np
import matplotlib.pyplot as plt

# Seeded so results are reproducible - remove the seed to get different noise each run.
rng = np.random.default_rng(seed=42)

NUM_SAMPLES = 200
SAMPLE_INTERVAL_S = 0.2          # matches the 200ms read loop in arduino-parking-sensor
TRUE_DISTANCE_CM = 40.0          # a car sitting still 40cm from the sensor
NOISE_STD_CM = 1.5               # HC-SR04 realistically jitters by a cm or two
SPIKE_COUNT = 6                  # a few random "someone walked past" spikes
WINDOW_SIZE = 5                  # moving average window, in samples
SPIKE_THRESHOLD_CM = 6.0         # flag any reading this far from the moving average


def simulate_readings():
    """Build a noisy distance signal: a steady baseline plus sensor jitter and a few spikes."""
    time = np.arange(NUM_SAMPLES) * SAMPLE_INTERVAL_S

    baseline = np.full(NUM_SAMPLES, TRUE_DISTANCE_CM)
    noise = rng.normal(0, NOISE_STD_CM, NUM_SAMPLES)
    readings = baseline + noise

    # sprinkle in a few spikes to simulate something briefly passing in front of the sensor
    spike_indices = rng.choice(NUM_SAMPLES, size=SPIKE_COUNT, replace=False)
    spike_sizes = rng.uniform(10, 25, size=SPIKE_COUNT) * rng.choice([-1, 1], size=SPIKE_COUNT)
    readings[spike_indices] += spike_sizes

    # HC-SR04 can't read below ~2cm and clips near 0 on bad readings, so clamp negatives
    readings = np.clip(readings, 0, None)

    return time, readings


def moving_average(readings, window_size):
    """Centered moving average via convolution, edge-padded so the first/last
    few samples don't get dragged toward zero (numpy's default 'same' mode
    zero-pads, which made every run flag false spikes right at the edges)."""
    pad_left = window_size // 2
    pad_right = window_size - 1 - pad_left
    padded = np.pad(readings, (pad_left, pad_right), mode="edge")
    kernel = np.ones(window_size) / window_size
    smoothed = np.convolve(padded, kernel, mode="valid")
    return smoothed


def find_spikes(readings, smoothed, threshold):
    """Flag any raw reading that deviates from the smoothed signal by more than threshold."""
    deviation = np.abs(readings - smoothed)
    return np.where(deviation > threshold)[0]


def main():
    time, readings = simulate_readings()
    smoothed = moving_average(readings, WINDOW_SIZE)
    spike_indices = find_spikes(readings, smoothed, SPIKE_THRESHOLD_CM)

    print(f"Simulated {NUM_SAMPLES} readings around a baseline of {TRUE_DISTANCE_CM} cm.")
    print(f"Flagged {len(spike_indices)} spike(s) at t = "
          f"{np.round(time[spike_indices], 2).tolist()} seconds")

    plt.figure(figsize=(10, 5))
    plt.plot(time, readings, label="Raw (noisy) reading", alpha=0.5, marker=".", linestyle="")
    plt.plot(time, smoothed, label=f"Moving average (window={WINDOW_SIZE})", linewidth=2)
    plt.scatter(time[spike_indices], readings[spike_indices],
                color="red", zorder=5, label="Flagged spike")
    plt.axhline(TRUE_DISTANCE_CM, color="gray", linestyle="--", linewidth=1, label="True distance")

    plt.xlabel("Time (s)")
    plt.ylabel("Distance (cm)")
    plt.title("Simulated Ultrasonic Sensor: Raw vs Filtered Readings")
    plt.legend()
    plt.tight_layout()
    plt.savefig("sensor_plot.png", dpi=150)
    print("Saved plot to sensor_plot.png")
    plt.show()


if __name__ == "__main__":
    main()
