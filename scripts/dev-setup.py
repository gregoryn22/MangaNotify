#!/usr/bin/env python3
"""
Development environment setup script for MangaNotify.
This script helps set up a local development environment.
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, description, check=True):
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {cmd}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, check=check, shell=True, capture_output=True, text=True)
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


def check_docker():
    """Check if Docker is available."""
    print("Checking Docker installation...")
    return run_command("docker --version", "Docker version check", check=False)


def check_docker_compose():
    """Check if Docker Compose is available."""
    print("Checking Docker Compose installation...")
    return run_command("docker-compose --version", "Docker Compose version check", check=False)


def create_dev_directory():
    """Create development data directory."""
    print("Creating development data directory...")
    dev_data_dir = Path("dev-data")
    dev_data_dir.mkdir(exist_ok=True)
    
    # Create .gitignore entry if it doesn't exist
    gitignore_path = Path(".gitignore")
    if gitignore_path.exists():
        with open(gitignore_path, "r") as f:
            content = f.read()
        
        if "dev-data/" not in content:
            with open(gitignore_path, "a") as f:
                f.write("\n# Development data\ndev-data/\n")
            print("✅ Added dev-data/ to .gitignore")
    else:
        with open(gitignore_path, "w") as f:
            f.write("# Development data\ndev-data/\n")
        print("✅ Created .gitignore with dev-data/ entry")


def create_env_dev():
    """Create development environment file."""
    print("Creating development environment file...")
    env_dev_path = Path(".env.dev")
    
    if not env_dev_path.exists():
        # Copy from example
        env_example_path = Path("env.dev.example")
        if env_example_path.exists():
            with open(env_example_path, "r") as f:
                content = f.read()
            with open(env_dev_path, "w") as f:
                f.write(content)
            print("✅ Created .env.dev from example")
        else:
            print("⚠️  env.dev.example not found, please create .env.dev manually")
    else:
        print("✅ .env.dev already exists")


def install_dependencies():
    """Install Python dependencies."""
    print("Installing Python dependencies...")
    
    # Check if requirements-dev.txt exists
    if Path("requirements-dev.txt").exists():
        return run_command("pip install -r requirements-dev.txt", "Installing development dependencies")
    elif Path("requirements.txt").exists():
        return run_command("pip install -r requirements.txt", "Installing dependencies")
    else:
        print("⚠️  No requirements file found")
        return True


def run_initial_tests():
    """Run initial tests to verify setup."""
    print("Running initial tests...")
    
    # Check if test script exists
    test_script = Path("scripts/run_tests.py")
    if test_script.exists():
        return run_command("python scripts/run_tests.py --fast", "Running initial tests", check=False)
    else:
        print("⚠️  Test script not found, skipping tests")
        return True


def build_dev_image():
    """Build development Docker image."""
    print("Building development Docker image...")
    return run_command("docker-compose -f docker-compose.dev.yml build", "Building development image", check=False)


def main():
    """Main setup function."""
    print("🚀 Setting up MangaNotify development environment...")
    print("This script will help you set up a local development environment.")
    
    # Check prerequisites
    if not check_docker():
        print("❌ Docker is not installed or not running.")
        print("Please install Docker Desktop and ensure it's running.")
        sys.exit(1)
    
    if not check_docker_compose():
        print("❌ Docker Compose is not available.")
        print("Please ensure Docker Compose is installed.")
        sys.exit(1)
    
    # Setup steps
    steps = [
        ("Creating development directories", create_dev_directory),
        ("Creating environment files", create_env_dev),
        ("Installing dependencies", install_dependencies),
        ("Running initial tests", run_initial_tests),
        ("Building development image", build_dev_image),
    ]
    
    failed_steps = []
    
    for description, func in steps:
        try:
            if not func():
                failed_steps.append(description)
        except Exception as e:
            print(f"❌ Error in {description}: {e}")
            failed_steps.append(description)
    
    # Summary
    print(f"\n{'='*60}")
    print("SETUP SUMMARY")
    print(f"{'='*60}")
    
    if failed_steps:
        print("❌ Some steps failed:")
        for step in failed_steps:
            print(f"   - {step}")
        print("\nYou may need to fix these issues manually.")
    else:
        print("🎉 Development environment setup complete!")
    
    print("\nNext steps:")
    print("1. Review and customize .env.dev if needed")
    print("2. Start development environment:")
    print("   docker-compose -f docker-compose.dev.yml up --build")
    print("3. Access the application at http://localhost:8999")
    print("4. Run tests with: python scripts/run_tests.py")
    
    print(f"\n{'='*60}")


if __name__ == "__main__":
    main()
