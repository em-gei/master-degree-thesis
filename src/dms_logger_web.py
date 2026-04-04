import time
import csv
import threading
from datetime import datetime
from flask import Flask, render_template_string
from dms_camera import DMSCamera
from dms_gyro import DMSGyro
from dms_temp import DMSTemp
from dms_light import DMSLight
from dms_air import DMSAir
from dms_alcohol import DMSAlcohol
from dms_audio import DMSAudio

# --- LOGGER CONFIGURATION ---
CSV_FILENAME = f"dataset_raw_road_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
TICK_RATE = 0.5  # 2 Hz frequency
HEADERS = [
    "Timestamp", "Label_ML", "Cam_Face_Det", "Cam_Pitch", "Cam_Yaw", "Cam_EAR",
    "Gyro_Acc_X", "Gyro_Acc_Y", "Gyro_Acc_Z", "Gyro_Rot_X", "Gyro_Rot_Y", "Gyro_Rot_Z",
    "Audio_dB", "Light_Lux", "Temp_C", "Humidity_Perc", "Gas_Pin", "Alcohol_Pin"
]
current_label = "VIGILE"

# --- SERVER WEB FLASK ---
app = Flask(__name__)
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>DMS Logger</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; background: #121212; color: white; margin: 0; padding: 10px; }
        button { width: 100%; padding: 25px; margin: 8px 0; font-size: 22px; font-weight: bold; border-radius: 8px; border: none; color: white; touch-action: manipulation; }
        button:active { opacity: 0.7; }
        .vigile { background: #28a745; }
        .distrazione { background: #ffc107; color: black; }
        .sonnolenza { background: #17a2b8; }
        .nervoso { background: #fd7e14; }
        .ebbrezza { background: #7f7f7f; }
        .malore { background: #800080; }
        .crash { background: #ed143d; }
        #status { font-size: 24px; margin: 15px; font-weight: bold; color: #28a745; border: 2px solid white; padding: 10px; }
    </style>
    <script>
        function setLabel(label, color) {
            fetch('/set_label/' + label)
            .then(response => response.text())
            .then(data => {
                let statusDiv = document.getElementById('status');
                statusDiv.innerText = "ATTUALE: " + label;
                statusDiv.style.color = color;
            });
        }
    </script>
</head>
<body>
    <h2>DMS Controllo Remoto</h2>
    <div id="status">ATTUALE: VIGILE</div>
    <button class="vigile" onclick="setLabel('VIGILE', '#28a745')">1. VIGILE</button>
    <button class="distrazione" onclick="setLabel('DISTRAZIONE', '#ffc107')">2. DISTRAZIONE</button>
    <button class="sonnolenza" onclick="setLabel('SONNOLENZA', '#17a2b8')">3. SONNOLENZA</button>
    <button class="nervoso" onclick="setLabel('NERVOSO', '#fd7e14')">4. NERVOSO</button>
    <button class="ebbrezza" onclick="setLabel('EBBREZZA', '#7f7f7f')">5. EBBREZZA</button>
    <button class="malore" onclick="setLabel('MALORE', '#800080')">6. MALORE</button>
    <button class="crash" onclick="setLabel('CRASH', '#ed143d')">7. CRASH</button>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@app.route('/set_label/<label>')
def set_label(label):
    global current_label
    current_label = label
    return "OK"

def run_server():
    """
        Run on port 5000, accessible within the local network
    """
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR) # Set level ERROR to keep terminal clean
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)


def main():
    print("🌐 Starting Web Server in the background...")
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    print("🔧 Headless Hardware Initialization (No Video)...")
    camera = DMSCamera()
    gyro = DMSGyro()
    temp_sensor = DMSTemp()
    light = DMSLight()
    air = DMSAir()
    alcohol = DMSAlcohol()
    audio = DMSAudio(device_index=0)
    audio.start_listening()

    last_temp_c = 0.0
    last_hum_p = 0.0
    last_temp_time = 0

    print(f"📊 Dataset: {CSV_FILENAME}")
    
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    print("\n" + "="*50)
    print(f"🚀 CONNECT FROM YOUR PHONE TO: http://{IP}:5000")
    print("="*50 + "\n")

    with open(CSV_FILENAME, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(HEADERS)

        try:
            while True:
                loop_start = time.time()
                timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                # READ RAW DATA
                cam_raw = camera.get_raw_data() or {}
                c_face = 1 if cam_raw.get("face_detected", False) else 0
                c_pitch = cam_raw.get("pitch", 0.0)
                c_yaw = cam_raw.get("yaw", 0.0)
                c_ear = cam_raw.get("ear", 0.0)
                
                gyr_raw = gyro.get_raw_data() or {}
                g_ax, g_ay, g_az = gyr_raw.get("accel_x", 0.0), gyr_raw.get("accel_y", 0.0), gyr_raw.get("accel_z", 0.0)
                g_rx, g_ry, g_rz = gyr_raw.get("gyro_x", 0.0), gyr_raw.get("gyro_y", 0.0), gyr_raw.get("gyro_z", 0.0)
                
                aud_raw = audio.get_raw_data() or {}
                a_db = aud_raw.get("decibel", 0.0)
                
                lit_raw = light.get_raw_data() or {}
                l_lux = lit_raw.get("lux", 0.0)
                
                air_raw = air.get_raw_data() or {}
                air_pin = 1 if air_raw.get("pin_value") else 0
                
                alc_raw = alcohol.get_raw_data() or {}
                alc_pin = 1 if alc_raw.get("pin_value") else 0
                
                if time.time() - last_temp_time >= 2.0:
                    print(f"{timestamp}: still running")
                    tmp_raw = temp_sensor.get_raw_data()
                    if tmp_raw:
                        last_temp_c, last_hum_p = tmp_raw.get("temperature", last_temp_c), tmp_raw.get("humidity", last_hum_p)
                    last_temp_time = time.time()

                # WRITE CSV ROW
                row = [
                    timestamp, current_label,
                    c_face, c_pitch, c_yaw, c_ear,
                    g_ax, g_ay, g_az, g_rx, g_ry, g_rz,
                    round(a_db, 2), l_lux, last_temp_c, last_hum_p, air_pin, alc_pin
                ]
                writer.writerow(row)
                file.flush()

                # SYNCHRONIZATION (No cv2.waitKey)
                elapsed = time.time() - loop_start
                wait_time = max(0.001, TICK_RATE - elapsed)
                time.sleep(wait_time)

        except KeyboardInterrupt:
            print("\n🛑 Manual stop.")
        finally:
            camera.stop()
            gyro.stop()
            temp_sensor.stop()
            light.stop()
            air.stop()
            alcohol.stop()
            audio.stop()
            print(f"Dataset successfully generated: {CSV_FILENAME}")

if __name__ == "__main__":
    main()