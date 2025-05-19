#%%
import dlpyc900.dlpyc900 as dlpyc900
import time
import numpy
# import PIL.Image
from dlpyc900.erle import encode

#%% Helper functions
def configure_video_input(dlp, port_type=0, pixel_mode=0, lanes=2):
    """Configure video input source and lock DisplayPort."""
    dlp.set_input_source(port_type, pixel_mode)
    dlp.set_port_clock_definition(lanes, 0, 0, 0)
    dlp.lock_displayport()
    time.sleep(4)
    if not dlp.get_source_lock():
        raise RuntimeError("Failed to lock DisplayPort source")
    print("Locked to source")

def configure_video_pattern(dlp, exposuretime=15000, bitdepth=8):
    """Configure Video-Pattern mode with LUT."""
    dlp.set_display_mode('video-pattern')
    if dlp.get_display_mode() != 'video-pattern':
        raise RuntimeError("Failed to switch to Video-Pattern mode")
    if not dlp.get_source_lock():
        raise RuntimeError("External source not locked")
    dlp.setup_pattern_LUT_definition(
        pattern_index=0, exposuretime=exposuretime, darktime=0, bitdepth=bitdepth, bit_position=0
    )
    dlp.start_pattern_from_LUT(nr_of_LUT_entries=1, nr_of_patterns_to_display=0)
    dlp.start_pattern()

def create_sample_patterns(num_patterns: int, height: int = 1080, width: int = 1920) -> list[numpy.ndarray]:
    """Generate binary test patterns (black/white stripes)."""
    if num_patterns > 24:
        raise ValueError("DLPC900 supports up to 24 patterns")
    patterns = []
    for i in range(num_patterns):
        img = numpy.zeros((height, width), dtype=numpy.uint8)
        stripe_width = width // num_patterns
        img[:, i * stripe_width:(i + 1) * stripe_width] = 255
        patterns.append(img)
    return patterns



def main():
    #%% Test reading some properties
    try:
        dlp = dlpyc900.dmd()
        status, errors = dlp.get_hardware_status()
        if errors > 0:
            raise RuntimeError(f"Hardware errors: {status}")
        print(dlp.get_display_mode())
        print(f"DMD model is {dlp.get_hardware()[0]}")
        print(dlp.get_main_status())
        print(dlp.get_hardware_status())
        print(dlp.get_current_powermode())
    except Exception as e:
        print(f"Initialization failed: {e}")
        exit(1)

    #%% Setup video mode
    try:
        dlp.set_display_mode('video')
        configure_video_input(dlp)
    except Exception as e:
        print(f"Video mode setup failed: {e}")
        dlp.standby()
        exit(1)

    #%% Video-pattern setup
    try:
        configure_video_pattern(dlp, exposuretime=15000, bitdepth=8)
    except Exception as e:
        print(f"Video-Pattern setup failed: {e}")
        dlp.standby()
        exit(1)

    #%% Pattern mode with on-the-fly loading
    try:
        # Switch to Pattern mode
        dlp.stop_pattern()
        dlp.set_display_mode('pattern')
        if dlp.get_display_mode() != 'pattern':
            raise RuntimeError("Failed to switch to Pattern mode")
        print("Switched to Pattern mode")

        # Generate 3 test patterns
        patterns = create_sample_patterns(num_patterns=3)
        
        # Load patterns on-the-fly
        print("Loading patterns on-the-fly...")
        dlp.load_pattern_on_the_fly(patterns, primary=True)
        
        # Configure LUT for binary patterns
        exposure_time = 1000000  # 1 second per pattern
        dlp.setup_pattern_LUT_definition(
                pattern_index=0,
                exposuretime=exposuretime,
                darktime=0,
                bitdepth=1,  # Binary patterns
                color=7,    # RGB all on
                disable_pattern_2_trigger_out=False,
                extended_bit_depth=False,
                image_pattern_index=0,
                bit_position=0
            )

        # Start pattern display
        print("Starting pattern display...")
        dlp.start_pattern()
        
        # Wait for display (3 patterns x 1 second)
        time.sleep(3)
        
        # Stop pattern display
        dlp.stop_pattern()
        print("Pattern display stopped")
    except Exception as e:
        print(f"Pattern mode failed: {e}")

    #%% Go to sleep
    try:
        dlp.stop_pattern()
        dlp.standby()
        if dlp.get_current_powermode() != "standby":
            raise RuntimeError("Failed to enter Standby mode")
        print("Entered Standby mode")
    except Exception as e:
        print(f"Standby failed: {e}")

    #%% Wakeup!
    try:
        dlp.wakeup()
        if dlp.get_current_powermode() != "normal":
            raise RuntimeError("Failed to enter Normal mode")
        print("Woke up to Normal mode")
        
        dlp.set_display_mode('video')
        configure_video_input(dlp)
        configure_video_pattern(dlp, exposuretime=15000, bitdepth=8)
    except Exception as e:
        print(f"Wakeup or reconfiguration failed: {e}")

    #%% Cleanup
    dlp.standby()
    print("Connection closed")

if __name__ == "__main__":
    main()