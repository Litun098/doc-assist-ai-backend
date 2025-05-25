"""
Test script to verify WebSocket integration is working correctly.
"""
import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_websocket_manager():
    """Test WebSocket manager import and basic functionality."""
    try:
        print("Testing WebSocket manager import...")
        from app.services.websocket_manager import websocket_manager
        print("✅ WebSocket manager imported successfully")
        
        print(f"✅ SocketIO server instance: {websocket_manager.sio}")
        print(f"✅ Connected users: {len(websocket_manager.connected_users)}")
        
        return True
    except Exception as e:
        print(f"❌ Error importing WebSocket manager: {str(e)}")
        return False

async def test_app_import():
    """Test main app import."""
    try:
        print("Testing main app import...")
        from app.main import app
        print("✅ Main app imported successfully")
        
        print("Testing socket_app import...")
        from app.main import socket_app
        print("✅ Socket app imported successfully")
        
        return True
    except Exception as e:
        print(f"❌ Error importing app: {str(e)}")
        return False

async def test_socketio_dependency():
    """Test SocketIO dependency."""
    try:
        print("Testing SocketIO dependency...")
        import socketio
        print(f"✅ SocketIO version: {socketio.__version__}")
        
        # Test creating a simple server
        sio = socketio.AsyncServer(cors_allowed_origins=["*"])
        print("✅ SocketIO server created successfully")
        
        return True
    except Exception as e:
        print(f"❌ Error with SocketIO: {str(e)}")
        return False

async def main():
    """Run all tests."""
    print("🔧 Testing WebSocket Integration\n")
    
    tests = [
        ("SocketIO Dependency", test_socketio_dependency),
        ("WebSocket Manager", test_websocket_manager),
        ("App Import", test_app_import)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} test...")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {str(e)}")
            results.append((test_name, False))
    
    print("\n" + "="*50)
    print("📊 TEST RESULTS SUMMARY")
    print("="*50)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("="*50)
    if all_passed:
        print("🎉 All tests passed! WebSocket integration is ready.")
        print("\nNext steps:")
        print("1. Start the server: uvicorn app.main:socket_app --host 0.0.0.0 --port 8000 --reload")
        print("2. Implement frontend using WEBSOCKET_FRONTEND_IMPLEMENTATION.md")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
    
    return all_passed

if __name__ == "__main__":
    asyncio.run(main())
