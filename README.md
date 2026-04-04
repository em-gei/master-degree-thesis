# master-degree-thesis

UNIT TESTS
To run all tests together:
- sh ./tests/run_tests.sh

To run all tests in a specific folder:
- python -m unittest discover -s tests/sensors_impl -p "*_tests.py" -v

To run test independently (example):
- python -m unittest discover -s tests/sensors_impl -p "dms_led_tests.py" -v


RUN RASPBERRY PI SETUP
- chmod +x setup_pi.sh
- ./setup_pi.sh
- sudo reboot
- source venv/bin/activate
- python src/dms_main.py