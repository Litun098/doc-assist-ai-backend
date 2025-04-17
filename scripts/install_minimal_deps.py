"""
Script to install minimal dependencies for AnyDocAI.
"""
import subprocess
import sys
import os


def install_package(package):
    """Install a package using pip."""
    print(f"Installing {package}...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])


def main():
    """Install minimal dependencies for AnyDocAI."""
    print("Installing minimal dependencies for AnyDocAI...")
    
    # Core dependencies
    dependencies = [
        "langchain>=0.1.9",
        "langchain-openai>=0.0.5",
        "pypdf>=4.0.0",
        "docx2txt>=0.8",
        "pillow>=3.3.2,<=9.5.0",  # Compatible with python-pptx
    ]
    
    # Install dependencies
    for dependency in dependencies:
        install_package(dependency)
    
    print("\nMinimal dependencies installed successfully!")
    print("\nTo run the simplified agent test:")
    print("python scripts/test_simple_agent.py")


if __name__ == "__main__":
    main()
