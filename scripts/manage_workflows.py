#!/usr/bin/env python3
"""
Workflow management script for MangaNotify CI/CD.
Helps you understand and manage the GitHub Actions workflows.
"""
import argparse
import subprocess
import json
import sys
from pathlib import Path


def run_gh_command(cmd):
    """Run a GitHub CLI command and return the result."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout) if result.stdout else {}
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        print(f"Error output: {e.stderr}")
        return None
    except json.JSONDecodeError:
        return result.stdout if result.stdout else ""


def list_workflows():
    """List all GitHub Actions workflows."""
    print("🔍 GitHub Actions Workflows:")
    print("=" * 50)
    
    workflows = [
        {
            "name": "Pull Request Checks",
            "file": "pr-checks.yml",
            "description": "Quick validation for PRs (5-10 min)",
            "triggers": ["pull_request", "pull_request_target"],
            "tests": ["Critical poller tests", "Missed notification scenario", "Docker startup", "Code quality"]
        },
        {
            "name": "Test Suite",
            "file": "test.yml", 
            "description": "Comprehensive testing (15-20 min)",
            "triggers": ["push", "pull_request"],
            "tests": ["Full test suite", "Integration tests", "Security scan", "Multi-Python versions"]
        },
        {
            "name": "Docker Build",
            "file": "docker.yml",
            "description": "Build and publish Docker images (10-15 min)",
            "triggers": ["push", "tags"],
            "tests": ["Critical tests", "Multi-platform builds", "Registry publishing"]
        },
        {
            "name": "Docker Publish",
            "file": "docker-publish.yml",
            "description": "Master branch CI/CD (15-20 min)",
            "triggers": ["push to master"],
            "tests": ["Comprehensive tests", "Missed notification scenario", "Docker publishing"]
        },
        {
            "name": "Release Testing",
            "file": "release-test.yml",
            "description": "Thorough release testing (20-30 min)",
            "triggers": ["tags", "manual"],
            "tests": ["Full suite", "Security scan", "Performance", "Docker optimization"]
        }
    ]
    
    for i, workflow in enumerate(workflows, 1):
        print(f"{i}. {workflow['name']}")
        print(f"   File: {workflow['file']}")
        print(f"   Description: {workflow['description']}")
        print(f"   Triggers: {', '.join(workflow['triggers'])}")
        print(f"   Tests: {', '.join(workflow['tests'])}")
        print()


def check_workflow_status():
    """Check the status of recent workflow runs."""
    print("📊 Recent Workflow Runs:")
    print("=" * 50)
    
    # This would require GitHub CLI to be installed and authenticated
    try:
        result = subprocess.run(["gh", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ GitHub CLI is available")
            print("Run 'gh run list' to see recent workflow runs")
        else:
            print("❌ GitHub CLI not found")
            print("Install it from: https://cli.github.com/")
    except FileNotFoundError:
        print("❌ GitHub CLI not found")
        print("Install it from: https://cli.github.com/")


def run_local_tests(test_level="quick"):
    """Run tests locally based on the test level."""
    print(f"🧪 Running {test_level} tests locally...")
    print("=" * 50)
    
    project_root = Path(__file__).parent.parent
    
    if test_level == "quick":
        cmd = ["python", "scripts/run_tests.py", "--poller", "--api", "--fast"]
    elif test_level == "full":
        cmd = ["python", "scripts/run_tests.py", "--coverage"]
    elif test_level == "comprehensive":
        cmd = ["python", "scripts/run_tests.py", "--coverage", "--verbose"]
    else:
        print(f"❌ Unknown test level: {test_level}")
        return False
    
    try:
        result = subprocess.run(cmd, cwd=project_root, check=True)
        print("✅ Tests completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Tests failed with exit code: {e.returncode}")
        return False


def show_test_coverage():
    """Show information about test coverage."""
    print("📈 Test Coverage Information:")
    print("=" * 50)
    
    coverage_file = Path(__file__).parent.parent / "htmlcov" / "index.html"
    if coverage_file.exists():
        print(f"✅ Coverage report available at: {coverage_file}")
        print("Open in browser to view detailed coverage")
    else:
        print("❌ No coverage report found")
        print("Run tests with coverage: python scripts/run_tests.py --coverage")


def validate_workflow_files():
    """Validate that all workflow files exist and are properly formatted."""
    print("🔍 Validating Workflow Files:")
    print("=" * 50)
    
    workflows_dir = Path(__file__).parent.parent / ".github" / "workflows"
    workflow_files = [
        "pr-checks.yml",
        "test.yml", 
        "docker.yml",
        "docker-publish.yml",
        "release-test.yml"
    ]
    
    all_valid = True
    
    for workflow_file in workflow_files:
        file_path = workflows_dir / workflow_file
        if file_path.exists():
            print(f"✅ {workflow_file} exists")
            
            # Basic YAML validation
            try:
                import yaml
                with open(file_path, 'r') as f:
                    yaml.safe_load(f)
                print(f"   ✅ Valid YAML syntax")
            except Exception as e:
                print(f"   ❌ Invalid YAML: {e}")
                all_valid = False
        else:
            print(f"❌ {workflow_file} missing")
            all_valid = False
    
    if all_valid:
        print("\n🎉 All workflow files are valid!")
    else:
        print("\n⚠️ Some workflow files have issues")
    
    return all_valid


def main():
    parser = argparse.ArgumentParser(description="Manage MangaNotify CI/CD workflows")
    parser.add_argument("--list", action="store_true", help="List all workflows")
    parser.add_argument("--status", action="store_true", help="Check workflow status")
    parser.add_argument("--test", choices=["quick", "full", "comprehensive"], 
                       help="Run tests locally")
    parser.add_argument("--coverage", action="store_true", help="Show coverage info")
    parser.add_argument("--validate", action="store_true", help="Validate workflow files")
    parser.add_argument("--all", action="store_true", help="Run all checks")
    
    args = parser.parse_args()
    
    if args.all or not any(vars(args).values()):
        # Run all checks
        list_workflows()
        print()
        check_workflow_status()
        print()
        validate_workflow_files()
        print()
        show_test_coverage()
        print()
        print("💡 Run 'python scripts/manage_workflows.py --test quick' to test locally")
        return
    
    if args.list:
        list_workflows()
    
    if args.status:
        check_workflow_status()
    
    if args.test:
        success = run_local_tests(args.test)
        if not success:
            sys.exit(1)
    
    if args.coverage:
        show_test_coverage()
    
    if args.validate:
        valid = validate_workflow_files()
        if not valid:
            sys.exit(1)


if __name__ == "__main__":
    main()
