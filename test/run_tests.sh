#!/bin/bash

# 1. Get the absolute path to the project's root folder
PROJECT_ROOT=$(dirname $(dirname $(realpath $0)))

# 2. Add the project root to the PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$PROJECT_ROOT

echo "📂 Project Root: $PROJECT_ROOT"
echo "🚀 Avvio suite di test..."
echo "--------------------------------------------------"

# 3. Run tests
# -s test: Find the tests in the "test" folder
# -p "*_tests.py": Only run files ending in "_tests.py"
python3 -m unittest discover -s "$PROJECT_ROOT/test" -p "*_tests.py"