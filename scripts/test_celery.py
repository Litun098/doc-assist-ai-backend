import sys
import os
import time

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.celery_worker import celery_app
from app.workers.tasks import process_file_task

def test_celery():
    """Test Celery configuration with a simple task"""
    print("Testing Celery configuration...")
    
    # Create a test file
    test_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads')
    os.makedirs(test_dir, exist_ok=True)
    
    test_file_id = "test_file_123"
    test_file_path = os.path.join(test_dir, f"{test_file_id}.txt")
    
    # Create a simple text file for testing
    with open(test_file_path, "w") as f:
        f.write("This is a test file for Celery.\n")
        f.write("It contains some text that will be processed.\n")
        f.write("The processing should split this into chunks.\n")
    
    print(f"Created test file: {test_file_path}")
    
    # Submit a task to process the file
    print("Submitting task to Celery...")
    result = process_file_task.delay(test_file_id)
    
    print(f"Task ID: {result.id}")
    print("Waiting for task to complete...")
    
    # Wait for the task to complete (with timeout)
    timeout = 30  # seconds
    start_time = time.time()
    
    while not result.ready() and time.time() - start_time < timeout:
        print("Task still running...")
        time.sleep(2)
    
    if result.ready():
        if result.successful():
            print("✅ Task completed successfully!")
            print(f"Result: {result.get()}")
        else:
            print("❌ Task failed!")
            try:
                result.get()  # This will re-raise the exception
            except Exception as e:
                print(f"Error: {str(e)}")
    else:
        print("⚠️ Task timed out (still running in background)")
    
    print("\nCelery test complete!")

if __name__ == "__main__":
    test_celery()
