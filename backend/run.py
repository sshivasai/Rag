"""
Simple script to run the FastAPI server with proper configuration
"""
import uvicorn
import os
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv()
    
    # Get configuration
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    
    print("=" * 60)
    print("🤖 RAG Chatbot API Server")
    print("=" * 60)
    print(f"🌐 Server: http://{host}:{port}")
    print(f"📚 API Docs: http://localhost:{port}/docs")
    print(f"🔍 Health Check: http://localhost:{port}/api/health")
    print("=" * 60)
    print("\n⌨️  Press CTRL+C to stop the server\n")
    
    # Run server with hot reload
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()