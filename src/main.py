#!/usr/bin/env python3
"""
KeyCL - Keyboard Sound Manager
Main entry point for the application
"""

import threading
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui import KeyCLApp
from tray import TrayManager

def main():
    """Main entry point"""
    try:
        # Create the main application
        app = KeyCLApp()
        
        # Create tray manager
        tray_manager = TrayManager(app)
        
        # Start tray icon in separate thread
        tray_thread = threading.Thread(target=tray_manager.run, daemon=True)
        tray_thread.start()
        
        # Start the GUI (this will block)
        app.setup_gui()
        app.run()
        
    except KeyboardInterrupt:
        print("Application interrupted by user")
    except Exception as e:
        print(f"Application error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()