"""
Pytest configuration for the FortiFi backend test suite.

Ensures the `backend` directory is on sys.path so that `app.*`
modules are importable regardless of where pytest is invoked from,
and loads the project-root `.env` so the app Settings can initialize.
"""

import os
import sys

# Add the backend directory (parent of tests/) to sys.path.
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# The app's Settings reads env_file=".env" relative to the CWD. When
# pytest runs from backend/, the real .env lives one level up at the
# project root. Load it into the process environment so Settings can
# initialize regardless of the invocation directory.
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")

if os.path.exists(ENV_PATH):
    with open(ENV_PATH, encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()

            if not line or line.startswith("#") or "=" not in line:
                continue

            key, _, value = line.partition("=")

            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if key and key not in os.environ:
                os.environ[key] = value

