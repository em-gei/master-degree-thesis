import pyaudio

p = pyaudio.PyAudio()

print("--- Elenco Dispositivi Audio ---")
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    # Cerchiamo dispositivi che hanno canali di Input (>0)
    if info['maxInputChannels'] > 0:
        print(f"ID: {i} | Nome: {info['name']}")

p.terminate()