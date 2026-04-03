#!/bin/bash

# 1. Get the absolute path to the project's root folder
#    Script lives in <root>/tests/sensors_impl/, so go up two levels.
SCRIPT_DIR=$(dirname "$(realpath "$0")")
PROJECT_ROOT=$(dirname "$(dirname "$SCRIPT_DIR")")

# 2. Add src/sensors_impl to PYTHONPATH so bare imports (e.g. "import dms_led") work
export PYTHONPATH="$PYTHONPATH:$PROJECT_ROOT/src/sensors_impl"

echo "Project Root: $PROJECT_ROOT"
echo "Avvio suite di test..."
echo "--------------------------------------------------"

# 3. Run tests
# -s tests/sensors_impl: Find tests in the sensors_impl folder
# -p "*_tests.py": Only run files ending in "_tests.py"
python3 -m unittest discover -s "$PROJECT_ROOT/tests/sensors_impl" -p "*_tests.py" -v