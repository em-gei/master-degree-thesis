# master-degree-thesis

UNIT TESTS
To run all tests together:
- sh ./tests/run_tests.sh

To run all tests in a specific folder:
- python -m unittest discover -s tests/sensors_impl -p "*_tests.py" -v

To run test independently (example):
- python -m unittest discover -s tests/sensors_impl -p "dms_led_tests.py" -v


RUN RASPBERRY PI SETUP (in master-degree-thesis folder)
- chmod +x setup_pi.sh
- ./setup_pi.sh
- sudo reboot
- source venv/bin/activate
- python src/dms_main.py              (with monitor attached)
or
- python src/dms_main.py --headless   (via SSH, no display)


RUN OVER SSH AND SEE THE LIVE VIEW IN YOUR BROWSER (web stream)
Over SSH the Pi has no usable display, and OpenCV windows do not render over X11
forwarding to a Mac. Instead, run with the --web flag: the views (camera
landmarks, weather monitor, alcohol alert) are streamed to your browser.

From the Mac:
- ssh pi@<your-pi-ip>
- source venv/bin/activate
- python src/dms_main.py --web

The terminal prints a URL like  http://<your-pi-ip>:8000
Open it in Safari/Chrome on your Mac to see the live view.
Press Ctrl+C in the SSH terminal to stop.

Notes:
- The "Unable to set line 4 to input" message at startup is a DHT11/libgpiod
  warning. If DHT11 reads keep timing out, the weather panel stays empty
  (it only appears once a read succeeds).
- The "ALCOL ALERT" panel only appears while alcohol is detected.
- The "DMS" camera panel shows an anonymized view (black background with facial
  landmark dots), not the raw camera feed, by design.