import subprocess
import os
import signal
import time

class VSCaptureManager:
    """
    Manages the VSCapture CLI process using the shell wrapper script.
    Designed for integration into a simple Python GUI or script.
    """

    def __init__(self):
        self.vscapture_process = None
        self.is_running = False
        self.vscapture_command = "/usr/local/bin/run_vscapture.sh"

        print(f"[Manager] VSCapture Script path: {self.vscapture_command}")

    def start(self):
        """Start the VSCapture process."""
        if self.is_running:
            print("[Manager] VSCapture is already running.")
            return

        if not os.path.exists(self.vscapture_command):
            print(f"[Manager ERROR] VSCapture wrapper script not found at {self.vscapture_command}")
            return
        
        # Arguments for the VSCapture CLI
        vsc_args = [
            "--devices", "1",
            "--device1type", "1",
            "--device1model", "2",
            "--device1arg", "-port /dev/ttyUSB0 -interval 1 -export 4 -waveset 2"
        ]
        
        # Command: Explicitly call bash interpreter with the script and arguments
        cmd = ["/bin/bash", self.vscapture_command] + vsc_args
        
        print(f"[Manager] Starting command: {' '.join(cmd)}")

        try:
            # Use Popen to run the script asynchronously
            self.vscapture_process = subprocess.Popen(
                cmd,
                # Note: We let the process output go to the terminal standard I/O (no pipes)
                # If you need to capture output in the GUI, you'd use pipes and threads here,
                # similar to your ROS node.
                preexec_fn=os.setsid 
            )

            # Quick check for immediate failure
            time.sleep(0.5)
            poll_result = self.vscapture_process.poll()
            
            if poll_result is not None:
                print(f"[Manager ERROR] VSCapture failed to start immediately (Exit Code: {poll_result})")
                self.vscapture_process = None
                return

            self.is_running = True
            print(f"[Manager SUCCESS] VSCapture started (PID={self.vscapture_process.pid})")

        except Exception as e:
            print(f"[Manager CRITICAL ERROR] Failed to start VSCapture: {e}")
            self.is_running = False

    def stop(self):
        """Stop the VSCapture process."""
        if not self.is_running or not self.vscapture_process:
            print("[Manager] VSCapture is not running.")
            return

        print("[Manager] Stopping VSCapture...")
        
        try:
            # Graceful termination (SIGTERM to the process group)
            os.killpg(os.getpgid(self.vscapture_process.pid), signal.SIGTERM)
            
            # Wait for graceful exit
            self.vscapture_process.wait(timeout=5)
            print("[Manager SUCCESS] VSCapture stopped gracefully")

        except subprocess.TimeoutExpired:
            print("[Manager WARNING] Force killing VSCapture (timeout)")
            os.killpg(os.getpgid(self.vscapture_process.pid), signal.SIGKILL)
            self.vscapture_process.wait()
        except Exception as e:
            print(f"[Manager WARNING] Process already terminated or error during kill: {e}")

        finally:
            self.vscapture_process = None
            self.is_running = False
            print("[Manager] VSCapture process cleaned up")


if __name__ == "__main__":
    # Example usage for testing outside a GUI/ROS node
    manager = VSCaptureManager()
    
    # Simulate a button click to start
    manager.start()
    
    # Wait 10 seconds (in a real GUI, this would be user interaction)
    print("Capturing data for 10 seconds...")
    time.sleep(10)
    
    # Simulate a button click to stop
    manager.stop()