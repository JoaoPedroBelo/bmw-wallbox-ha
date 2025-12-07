#!/usr/bin/env python3
"""Debug test runner to capture output."""
import sys
import subprocess

print("Starting pytest...")
print("=" * 80)

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
    cwd="/Users/joaobelo/Git/Belo/wallbox",
    capture_output=False,
    text=True
)

print("=" * 80)
print(f"Pytest exit code: {result.returncode}")
sys.exit(result.returncode)
