#!/usr/bin/env python3
"""
HR AI Assistant - Main Entry Point
Run this file to start the application
"""

import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    """Main function to run the HR AI Assistant"""
    print("=" * 50)
    print("🤖 HR AI Assistant Starting...")
    print("=" * 50)
    
    # Configuration
    host = "127.0.0.1"
    port = 8000
    
    print(f"🌐 Server will start at: http://{host}:{port}")
    print("📝 Login with: john.doe@company.com / password123")
    print("💡 Press Ctrl+C to stop the server")
    print("=" * 50)
    
    # Start the server
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True,
        reload_dirs=["app", "static"],
        log_level="info"
    )

if __name__ == "__main__":
    main()