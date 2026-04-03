#!/bin/bash

# 1. Get the absolute path to the project's root folder
#    Script lives in <root>/tests/, so go up one level.
SCRIPT_DIR=$(dirname "$(realpath "$0")")
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

# 2. Add source directories to PYTHONPATH so bare imports work
export PYTHONPATH="$PYTHONPATH:$PROJECT_ROOT/src/sensors_impl:$PROJECT_ROOT/src/units_impl"

echo "Project Root: $PROJECT_ROOT"
echo "Avvio suite di test..."
echo "--------------------------------------------------"

# 3. Run ALL tests from both test folders
echo "=== Sensors Tests ==="
python3 -m unittest discover -s "$PROJECT_ROOT/tests/sensors_impl" -p "*_tests.py" -v

echo ""
echo "=== Units Tests ==="
python3 -m unittest discover -s "$PROJECT_ROOT/tests/units_impl" -p "*_tests.py" -v