#!/usr/bin/env python3
"""
Comprehensive test runner for MangaNotify.
Runs all tests and provides detailed reporting.
"""
import sys
import subprocess
import argparse
import os
from pathlib import Path


def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ SUCCESS")
        if result.stdout:
            print("Output:", result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("❌ FAILED")
        print("Return code:", e.returncode)
        if e.stdout:
            print("Output:", e.stdout)
        if e.stderr:
            print("Error:", e.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Run MangaNotify tests")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--poller", action="store_true", help="Run poller tests only")
    parser.add_argument("--api", action="store_true", help="Run API tests only")
    parser.add_argument("--config", action="store_true", help="Run config tests only")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--fast", action="store_true", help="Skip slow tests")
    
    args = parser.parse_args()
    
    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    # Base pytest command
    pytest_cmd = ["python", "-m", "pytest"]
    
    if args.verbose:
        pytest_cmd.append("-v")
    else:
        pytest_cmd.append("-q")
    
    if args.coverage:
        # Check if pytest-cov is available
        try:
            import pytest_cov
            pytest_cmd.extend(["--cov=src/manganotify", "--cov-report=html", "--cov-report=term"])
        except ImportError:
            print("⚠️  pytest-cov not installed, skipping coverage")
            print("   Install with: pip install pytest-cov")
    
    # Test selection
    test_files = []
    if args.unit:
        test_files.append("tests/test_api.py")
        test_files.append("tests/test_auth.py")
    elif args.integration:
        test_files.append("tests/test_integration.py")
    elif args.poller:
        test_files.append("tests/test_poller.py")
    elif args.api:
        test_files.append("tests/test_api_endpoints.py")
    elif args.config:
        test_files.append("tests/test_config.py")
    else:
        # Run all tests
        test_files.append("tests/")
    
    pytest_cmd.extend(test_files)
    
    # Skip slow tests if requested
    if args.fast:
        pytest_cmd.extend(["-m", "not slow"])
    
    # Run the tests
    success = run_command(pytest_cmd, "Running MangaNotify test suite")
    
    if args.coverage:
        print(f"\nCoverage report generated in htmlcov/index.html")
    
    # Additional checks
    if success:
        print(f"\n{'='*60}")
        print("Running additional checks...")
        print(f"{'='*60}")
        
        # Lint check
        try:
            import flake8
            run_command(["python", "-m", "flake8", "src/"], "Code linting")
        except ImportError:
            print("⚠️  flake8 not installed, skipping linting")
        
        # Type checking
        try:
            import mypy
            run_command(["python", "-m", "mypy", "src/"], "Type checking")
        except ImportError:
            print("⚠️  mypy not installed, skipping type checking")
        
        # Security scan
        try:
            import bandit
            run_command(["python", "-m", "bandit", "-r", "src/"], "Security scan")
        except ImportError:
            print("⚠️  bandit not installed, skipping security scan")
    
    # Summary
    print(f"\n{'='*60}")
    if success:
        print("🎉 ALL TESTS PASSED!")
        print("Your code is ready for deployment.")
    else:
        print("❌ TESTS FAILED!")
        print("Please fix the issues before deploying.")
        sys.exit(1)
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
