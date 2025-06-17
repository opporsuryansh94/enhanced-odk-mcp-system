#!/usr/bin/env python3
"""
Test runner for ODK MCP System tests.

This script runs all tests and generates a test report.
"""

import os
import sys
import argparse
import pytest
import time
from datetime import datetime

def run_tests(test_type=None, verbose=False, coverage=False):
    """Run tests and return the exit code."""
    args = ["-v"] if verbose else []
    
    if coverage:
        args.extend(["--cov=mcps", "--cov=agents", "--cov=ui", "--cov-report=term", "--cov-report=html:tests/coverage"])
    
    if test_type == "unit":
        args.append("tests/unit/")
    elif test_type == "integration":
        args.append("tests/integration/")
    elif test_type == "e2e":
        args.append("tests/e2e/")
    else:
        args.append("tests/")
    
    return pytest.main(args)

def generate_report(test_type=None, result=0):
    """Generate a test report."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report_dir = os.path.join(os.path.dirname(__file__), "reports")
    os.makedirs(report_dir, exist_ok=True)
    
    report_file = os.path.join(report_dir, f"test_report_{test_type or 'all'}_{timestamp}.txt")
    
    with open(report_file, "w") as f:
        f.write(f"ODK MCP System Test Report\n")
        f.write(f"========================\n\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Test Type: {test_type or 'all'}\n")
        f.write(f"Result: {'PASS' if result == 0 else 'FAIL'}\n\n")
        
        if result == 0:
            f.write("All tests passed successfully.\n")
        else:
            f.write(f"Tests failed with exit code {result}.\n")
        
        f.write("\n")
        f.write("For detailed test results, see the test output above.\n")
        
        if os.path.exists(os.path.join(os.path.dirname(__file__), "coverage")):
            f.write("\nCoverage report generated in tests/coverage/index.html\n")
    
    print(f"\nTest report generated: {report_file}")
    return report_file

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Run ODK MCP System tests.")
    parser.add_argument("--type", choices=["unit", "integration", "e2e"], help="Type of tests to run")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--report", action="store_true", help="Generate test report")
    
    args = parser.parse_args()
    
    start_time = time.time()
    result = run_tests(args.type, args.verbose, args.coverage)
    end_time = time.time()
    
    print(f"\nTests completed in {end_time - start_time:.2f} seconds")
    
    if args.report:
        generate_report(args.type, result)
    
    return result

if __name__ == "__main__":
    sys.exit(main())

