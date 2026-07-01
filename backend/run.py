"""Startup script for AI Interview System."""
import uvicorn
import sys
import os

if __name__ == "__main__":
    print("=" * 60)
    print("Starting AI Interview System")
    print("=" * 60)
    print("\nBackend API: http://localhost:8000")
    print("API Documentation: http://localhost:8000/docs")
    print("Frontend UI will open automatically in your browser")
    print("\nPress CTRL+C to stop the server")
    print("=" * 60)
    print()
    
    try:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n\nShutting down AI Interview System...")
        sys.exit(0)
