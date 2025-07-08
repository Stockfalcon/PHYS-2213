import nidaqmx
from nidaqmx.constants import TerminalConfiguration
import time

# Analog input channel
AI_CHANNEL = "Dev1/ai0"  # Change to match your device

def read_voltage(samples=10):
    """Read and average voltage samples from the load cell."""
    with nidaqmx.Task() as task:

        task.ai_channels.add_ai_voltage_chan(
            AI_CHANNEL,
            terminal_config=TerminalConfiguration.DIFF,  # Use DIFF, RSE, or NRSE as needed
            min_val=-5.0,
            max_val=5.0
        )
        readings = [task.read() for _ in range(samples)]
        avg_voltage = sum(readings) / samples
        return avg_voltage

def calibrate_load_cell():
    """Perform 2-point calibration: zero and known weight (in grams)."""
    print("🔧 Calibration Step 1: Make sure the load cell is unloaded (0 grams).")
    input("Press Enter when ready...")
    zero_voltage = read_voltage()
    print(f"Zero-load voltage: {zero_voltage:.6f} V")

    print("\n🔧 Calibration Step 2: Apply a known weight.")
    known_grams = float(input("Enter the known weight in grams (e.g., 500): "))
    input("Press Enter after applying the known weight...")
    loaded_voltage = read_voltage()
    print(f"Loaded voltage: {loaded_voltage:.6f} V")

    delta_voltage = loaded_voltage - zero_voltage
    if abs(delta_voltage) < 1e-6:
        raise ValueError("⚠️ No voltage change detected. Check load or wiring.")

    scale = known_grams / delta_voltage  # grams per volt
    print(f"\n✅ Calibration complete.\nScale factor: {scale:.3f} grams/volt")

    return zero_voltage, scale

def read_force(zero_voltage, scale, samples=10):
    """Convert voltage to force in grams using the calibration data."""
    current_voltage = read_voltage(samples)
    delta = current_voltage - zero_voltage
    grams = delta * scale
    return grams, current_voltage

if __name__ == "__main__":
    try:
        print("📏 Load Cell Calibration and Reading (grams)")
        zero_voltage, scale = calibrate_load_cell()

        print("\n📡 Measuring... Press Ctrl+C to stop.")
        while True:
            grams, voltage = read_force(zero_voltage, scale)
            print(f"Voltage: {voltage:.6f} V | Force: {grams:.1f} g")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n⛔ Measurement stopped.")
    except Exception as e:
        print(f"❌ Error: {e}")


