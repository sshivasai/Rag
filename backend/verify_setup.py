"""
Verify that all dependencies and configurations are set up correctly
"""
import sys
import os
from dotenv import load_dotenv

def check_imports():
    """Check if all required packages are installed"""
    print("📦 Checking installed packages...")
    
    packages = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("anthropic", "Anthropic"),
        ("chromadb", "ChromaDB"),
        ("redis", "Redis"),
        ("sentence_transformers", "Sentence Transformers"),
        ("googleapiclient", "Google API Client"),
    ]
    
    all_installed = True
    for module, name in packages:
        try:
            __import__(module)
            print(f"  ✅ {name}")
        except ImportError:
            print(f"  ❌ {name} - NOT INSTALLED")
            all_installed = False
    
    return all_installed

def check_env_file():
    """Check if .env file exists and has required variables"""
    print("\n🔧 Checking environment configuration...")
    
    if not os.path.exists(".env"):
        print("  ❌ .env file not found!")
        print("  👉 Create .env file by copying .env.example")
        return False
    
    print("  ✅ .env file exists")
    
    # Load environment variables
    load_dotenv()
    
    # Required variables
    required_vars = [
        ("ANTHROPIC_API_KEY", "Claude API Key"),
        ("GOOGLE_API_KEY", "Google API Key"),
        ("GOOGLE_CSE_ID", "Google Search Engine ID"),
    ]
    
    all_set = True
    for var, name in required_vars:
        value = os.getenv(var)
        if value and len(value) > 10:
            # Mask the key for security
            masked = f"{value[:8]}...{value[-4:]}"
            print(f"  ✅ {name}: {masked}")
        else:
            print(f"  ❌ {name} - NOT SET or INVALID")
            all_set = False
    
    # Optional variables
    optional_vars = [
        ("REDIS_HOST", "Redis Host", "localhost"),
        ("REDIS_PORT", "Redis Port", "6379"),
    ]
    
    for var, name, default in optional_vars:
        value = os.getenv(var, default)
        print(f"  ℹ️  {name}: {value}")
    
    return all_set

def check_redis_connection():
    """Check if Redis is running and accessible"""
    print("\n🔴 Checking Redis connection...")
    
    try:
        import redis
        
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        
        r = redis.Redis(host=host, port=port, db=0)
        r.ping()
        print(f"  ✅ Redis is running at {host}:{port}")
        return True
    except Exception as e:
        print(f"  ⚠️  Redis connection failed: {str(e)}")
        print("  👉 Make sure Redis is installed and running")
        print("     - Windows: Download from https://github.com/microsoftarchive/redis/releases")
        print("     - Mac: brew install redis && brew services start redis")
        print("     - Linux: sudo apt-get install redis-server")
        return False

def main():
    print("=" * 60)
    print("🔍 RAG Chatbot Setup Verification")
    print("=" * 60)
    print()
    
    # Run all checks
    imports_ok = check_imports()
    env_ok = check_env_file()
    redis_ok = check_redis_connection()
    
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    if imports_ok and env_ok:
        print("✅ All required packages installed")
        print("✅ Environment variables configured")
        
        if redis_ok:
            print("✅ Redis is running")
            print("\n🎉 Setup is complete! You're ready to start the server.")
            print("\n🚀 Run the server with:")
            print("   python run.py")
            print("   or")
            print("   uvicorn main:app --reload")
        else:
            print("⚠️  Redis is not running (optional for now)")
            print("\n✅ You can still start the server, but session management won't work yet.")
            print("\n🚀 Run the server with:")
            print("   python run.py")
    else:
        print("\n❌ Setup incomplete. Please fix the issues above.")
        if not imports_ok:
            print("\n📦 Install missing packages:")
            print("   pip install -r requirements.txt")
        if not env_ok:
            print("\n🔧 Configure environment:")
            print("   1. Copy .env.example to .env")
            print("   2. Add your API keys to .env")
    
    print("=" * 60)
    
    return 0 if (imports_ok and env_ok) else 1

if __name__ == "__main__":
    sys.exit(main())