# master-degree-thesis

UNIT TESTS
To run all tests together:
- sh ./test/sensors_impl/run_tests.sh

To run test indipendentely (example):
- python -m unittest tests.sensors_impl.dms_led_tests


RUN RASPBERRY PI SETUP
- chmod +x setup_pi.sh
- ./setup_pi.sh
- sudo reboot
- source/venv/bin/activate
- python src/dms_main.py