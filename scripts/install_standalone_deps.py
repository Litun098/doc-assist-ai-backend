"""
Script to install standalone dependencies for AnyDocAI.
"""
import subprocess
import sys
import os


def install_package(package):
    """Install a package using pip."""
    print(f"Installing {package}...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])


def main():
    """Install standalone dependencies for AnyDocAI."""
    print("Installing standalone dependencies for AnyDocAI...")
    
    # Core dependencies
    dependencies = [
        "langchain>=0.1.9",
        "langchain-openai>=0.0.5",
    ]
    
    # Install dependencies
    for dependency in dependencies:
        install_package(dependency)
    
    print("\nStandalone dependencies installed successfully!")
    print("\nTo run the standalone agent test:")
    print("python scripts/test_standalone_agent.py")


if __name__ == "__main__":
    main()
