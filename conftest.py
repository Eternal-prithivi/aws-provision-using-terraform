# conftest.py — Root-level pytest configuration
# Adds policy-engine directory to sys.path so tests can import it as 'policy_engine'

import sys
import os

# Make policy-engine importable as 'policy_engine'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "policy-engine"))
