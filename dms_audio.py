import pyaudio
import numpy as np
import threading
import time

# Audio Configurations
CHUNK = 1024       # Samples per block (buffer)
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100       # Hz (Sampling Rate)

class DMSAudio:
    def __init__(self, device_index=None, threshold_db=85):
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.running = False
        self.crash_detected = False
        self.THRESHOLD_DB = threshold_db
        
        # Microphone ID (If None, uses default, but better to specify)
        self.device_index = device_index

    def start_listening(self):
        """Starts the separate listening thread"""
        if self.running: return
        
        try:
            self.stream = self.p.open(format=FORMAT,
                                      channels=CHANNELS,
                                      rate=RATE,
                                      input=True,
                                      input_device_index=self.device_index,
                                      frames_per_buffer=CHUNK)
            
            self.running = True
            # Start the process in a separate thread
            self.thread = threading.Thread(target=self._monitor_loop)
            self.thread.daemon = True # Closes if the main program closes
            self.thread.start()
            print("🎤 Microfono in ascolto (Background)...")
        except Exception as e:
            print(f"❌ Errore apertura microfono: {e}")

    def _monitor_loop(self):
        """Internal thread logic"""
        print(f"--- Audio Monitor Attivo (Soglia: {self.THRESHOLD_DB} dB) ---")
        
        while self.running:
            try:
                # Read raw data from microphone (without overflow exceptions)
                data = self.stream.read(CHUNK, exception_on_overflow=False)
                # Convert to numbers (NumPy array)
                audio_data = np.frombuffer(data, dtype=np.int16)
                # Calculate intensity (RMS - Root Mean Square)
                # Use int64 to avoid mathematical overflow during squaring
                rms = np.sqrt(np.mean(audio_data.astype(np.int64)**2))
                
                # Avoid logarithm of zero
                if rms > 0:
                    db = 20 * np.log10(rms)
                else:
                    db = 0

                # CRASH / ANOMALY CHECK
                if db > self.THRESHOLD_DB:
                    print(f"\n💥 RUMORE FORTE RILEVATO: {db:.2f} dB!")
                    self.crash_detected = True
                    # Optional: Short pause to avoid registering the same bang 100 times
                    time.sleep(2) 

            except Exception as e:
                print(f"Errore Audio Loop: {e}")
                break

    def stop(self):
        """Stops everything cleanly"""
        self.running = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()