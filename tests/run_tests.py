#!/usr/bin/env python3
# Test runner for PyRpiCamController
# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project

import os
import sys
import subprocess
import argparse
from pathlib import Path

def run_tests(test_type="all", verbose=False, coverage=True):
    """
    Run tests for the PyRpiCamController project.
    
    Args:
        test_type: Type of tests to run ("all", "unit", "integration")
        verbose: Enable verbose output
        coverage: Enable coverage reporting
    """
    
    # Get project root directory
    project_root = Path(__file__).parent.parent
    tests_dir = project_root / "tests"
    
    # Ensure we're in the right directory
    os.chdir(project_root)
    
    # Build pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add test path based on test type
    if test_type == "unit":
        cmd.append(str(tests_dir / "unit"))
    elif test_type == "integration": 
        cmd.append(str(tests_dir / "integration"))
    else:  # all
        cmd.append(str(tests_dir))
    
    # Add verbosity
    if verbose:
        cmd.extend(["-v", "-s"])
    
    # Add coverage
    if coverage:
        cmd.extend([
            "--cov=CamController",
            "--cov=Settings", 
            "--cov-report=html:tests/reports/coverage_html",
            "--cov-report=term-missing"
        ])
    
    # Create reports directory if it doesn't exist
    reports_dir = tests_dir / "reports"
    reports_dir.mkdir(exist_ok=True)
    
    print(f"Running {test_type} tests...")
    print(f"Command: {' '.join(cmd)}")
    
    # Run tests
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        return 1
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1

def check_requirements():
    """Check if test requirements are installed."""
    try:
        import pytest
        import pytest_cov
        import mock
        return True
    except ImportError as e:
        print(f"Missing test dependencies: {e}")
        print("Please install test requirements:")
        print("  pip install -r tests/requirements.txt")
        return False

def main():
    parser = argparse.ArgumentParser(description="Run PyRpiCamController tests")
    parser.add_argument(
        "--type", 
        choices=["all", "unit", "integration"],
        default="all",
        help="Type of tests to run (default: all)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--no-coverage",
        action="store_true", 
        help="Disable coverage reporting"
    )
    parser.add_argument(
        "--check-requirements",
        action="store_true",
        help="Check if test requirements are installed"
    )
    
    args = parser.parse_args()
    
    # Check requirements if requested
    if args.check_requirements:
        if check_requirements():
            print("All test requirements are installed ✓")
            return 0
        else:
            return 1
    
    # Check requirements before running tests
    if not check_requirements():
        return 1
    
    # Run tests
    return run_tests(
        test_type=args.type,
        verbose=args.verbose,
        coverage=not args.no_coverage
    )

if __name__ == "__main__":
    sys.exit(main())