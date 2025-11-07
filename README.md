# 🤖 RAG Chatbot with Document Search & Web Integration

A production-ready **Retrieval-Augmented Generation (RAG)** chatbot built with **FastAPI**, **React**, and **Claude AI**. Features include document management, vector search, web search, interactive citations (Perplexity-style), and session persistence.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![React](https://img.shields.io/badge/React-18+-61DAFB.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## ✨ Features

### 🎯 Core Capabilities
- **📚 Document Management**: Upload .txt, .pdf, .json files to build your knowledge base
- **🔍 Vector Search**: Semantic search using ChromaDB and sentence transformers
- **🌐 Web Search**: Real-time information from Google Custom Search
- **🤖 Multiple AI Models**: Choose from various Claude models (Sonnet 4, Opus, Haiku)
- **💬 Session Management**: Persistent conversations with Redis
- **📖 Interactive Citations**: Perplexity-style inline citations with hover tooltips
- **🎨 Modern UI**: Beautiful React interface with Tailwind CSS

### 🔥 Advanced Features
- Toggle document search on/off
- Toggle web search on/off
- Chat history sidebar
- Source relevance scores
- Model selection per message
- Conversation persistence
- Responsive design
- Real-time typing indicators

## 📸 Screenshots

### Chat Interface
```
┌─────────────────────────────────────────────────────────────┐
│ 🤖 RAG Chatbot                                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  User: Who created Python?                                  │
│                                                              │
│  🤖 Bot: Python was created by Guido van Rossum ①           │
│         and first released in 1991 ②.                       │
│                                                              │
│         Sources:                                            │
│         ① 📄 python_intro.txt (Relevance: 87%)             │
│         ② 🌐 Python.org - History                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 🏗️ Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   React     │─────▶│   FastAPI    │─────▶│  Claude AI  │
│  Frontend   │◀─────│   Backend    │◀─────│             │
└─────────────┘      └──────────────┘      └─────────────┘
                            │
                ┌───────────┼───────────┐
                │           │           │
         ┌──────▼────┐ ┌───▼────┐ ┌───▼──────┐
         │ ChromaDB  │ │ Redis  │ │  Google  │
         │ (Vector)  │ │(Cache) │ │ Search   │
         └───────────┘ └────────┘ └──────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+**
- **Node.js 16+**
- **Redis** (for session management)
- **API Keys**:
  - [Anthropic API Key](https://console.anthropic.com/)
  - [Google Custom Search API Key](https://console.cloud.google.com/)
  - [Google Search Engine ID](https://programmablesearchengine.google.com/)

### Installation

#### 1. Clone the repository
```bash
git clone https://github.com/yourusername/rag-chatbot.git
cd rag-chatbot
```

#### 2. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env and add your API keys
```

**Configure `.env`:**
```env
# Claude API
ANTHROPIC_API_KEY=sk-ant-xxxxx

# Google Search
GOOGLE_API_KEY=xxxxx
GOOGLE_CSE_ID=xxxxx

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Model Configuration
LLM_MODEL=claude-sonnet-4-20250514
```

#### 3. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

#### 4. Start Redis
```bash
# Mac
brew services start redis

# Linux
sudo systemctl start redis

# Windows
# Download and run Redis from https://github.com/microsoftarchive/redis/releases
```

#### 5. Run the Backend
```bash
cd backend
python run.py
```

#### 6. Access the Application
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health

## 📁 Project Structure

```
rag-chatbot/
├── backend/
│   ├── main.py                    # FastAPI application
│   ├── llm_service.py             # Claude AI integration
│   ├── vector_service.py          # ChromaDB & embeddings
│   ├── document_processor.py      # Document processing
│   ├── web_search_service.py      # Google Search integration
│   ├── redis_service.py           # Session management
│   ├── models.py                  # Pydantic models
│   ├── requirements.txt           # Python dependencies
│   ├── .env                       # Environment variables
│   ├── run.py                     # Server startup script
│   └── tests/                     # Test scripts
│       ├── test_document_rag.py
│       ├── test_chat_endpoint.py
│       └── test_model_selection.py
├── frontend/
│   ├── src/
│   │   ├── App.jsx               # Main React component
│   │   ├── api.js                # API client
│   │   ├── main.jsx              # Entry point
│   │   └── index.css             # Tailwind styles
│   ├── vite.config.js            # Vite configuration
│   ├── package.json              # Node dependencies
│   └── index.html                # HTML template
└── README.md
```

## 🎮 Usage

### 1. Upload Documents
1. Click **"Documents"** tab
2. Click **"Upload"** button
3. Select a `.txt`, `.pdf`, or `.json` file
4. Wait for processing

### 2. Ask Questions
1. Type your question in the chat input
2. Toggle **"Documents"** to search your uploaded files
3. Toggle **"Web"** to search the internet
4. Press Enter or click Send

### 3. View Sources
- Hover over citation numbers `①` `②` `③` in responses
- See source details in tooltip
- Click links to open web sources

### 4. Change AI Model
1. Go to **"Settings"** tab
2. Select your preferred Claude model
3. Next messages will use that model

### 5. Browse Chat History
- View recent conversations in sidebar
- Click to load previous chat
- Click **"+ New Chat"** to start fresh

## 🧪 Testing

### Run All Tests
```bash
cd backend

# Test document RAG pipeline
python test_document_rag.py

# Test complete chat system
python test_chat_endpoint.py

# Test model selection
python test_model_selection.py
```

### Manual Testing

**Test Document Search:**
```bash
# Upload a document
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@test.txt"

# Ask about the document
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What does the document say?",
    "use_web_search": false
  }'
```

**Test Web Search:**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the latest AI developments?",
    "use_web_search": true
  }'
```

## 📚 API Documentation

### Endpoints

#### Chat
- `POST /api/chat` - Send message and get AI response
  ```json
  {
    "message": "Your question",
    "session_id": "optional-session-id",
    "use_web_search": false,
    "model": "claude-sonnet-4-20250514"
  }
  ```

#### Models
- `GET /api/models` - Get available Claude models

#### Documents
- `POST /api/documents/upload` - Upload document
- `GET /api/documents` - List all documents
- `GET /api/documents/{id}` - Get document details
- `DELETE /api/documents/{id}` - Delete document

#### Sessions
- `POST /api/sessions/create` - Create new session
- `GET /api/sessions/{id}` - Get session details
- `GET /api/sessions` - List all sessions
- `DELETE /api/sessions/{id}` - Delete session

#### Health
- `GET /api/health` - Check API health status

**Full API documentation:** http://localhost:8000/docs

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ANTHROPIC_API_KEY` | Claude API key | - | ✅ |
| `GOOGLE_API_KEY` | Google Search API key | - | ⚠️ Optional |
| `GOOGLE_CSE_ID` | Custom Search Engine ID | - | ⚠️ Optional |
| `REDIS_HOST` | Redis server host | localhost | ✅ |
| `REDIS_PORT` | Redis server port | 6379 | ✅ |
| `LLM_MODEL` | Default Claude model | claude-sonnet-4-20250514 | ⚠️ Optional |
| `CHUNK_SIZE` | Document chunk size | 512 | ⚠️ Optional |
| `TOP_K_RESULTS` | Number of search results | 5 | ⚠️ Optional |

### Chunking Strategies

Choose in `.env`:
```env
CHUNKING_STRATEGY=tokens  # or 'sentences', 'paragraphs', 'fixed'
CHUNK_SIZE=512
CHUNK_OVERLAP=50
```

## 🎨 Customization

### Change Theme Colors
Edit `frontend/src/App.jsx`:
```jsx
// Change from blue to purple
'bg-blue-600' → 'bg-purple-600'
'text-blue-700' → 'text-purple-700'
```

### Add New Document Types
Edit `backend/document_processor.py`:
```python
def _extract_from_docx(self, file_path: str) -> str:
    # Add your extraction logic
    pass
```

### Change AI Model
Edit `.env`:
```env
LLM_MODEL=claude-3-haiku-20240307  # Fast & economical
# or
LLM_MODEL=claude-3-opus-20240229   # Most capable
```

## 🐛 Troubleshooting

### Backend Issues

**"ANTHROPIC_API_KEY not found"**
```bash
# Add to backend/.env
ANTHROPIC_API_KEY=sk-ant-xxxxx
```

**"Redis connection failed"**
```bash
# Start Redis
redis-cli ping  # Should return PONG

# If not running:
# Mac: brew services start redis
# Linux: sudo systemctl start redis
```

**"ChromaDB initialization failed"**
```bash
# Remove old database
rm -rf backend/chroma_db
# Restart server
```

### Frontend Issues

**"Cannot connect to backend"**
```bash
# Check backend is running
curl http://localhost:8000/api/health

# Check CORS is configured
# main.py should have localhost:3000 in CORS origins
```

**"Module not found"**
```bash
cd frontend
npm install
```

**"Styles not working"**
```bash
# Make sure index.css has:
@import "tailwindcss";

# Restart dev server
npm run dev
```

## 📊 Performance

### Optimization Tips

1. **Use faster models**: `claude-3-haiku` for simple queries
2. **Adjust chunk size**: Smaller chunks = faster search
3. **Limit TOP_K**: Fewer results = faster responses
4. **Enable caching**: Redis caches responses
5. **Use hybrid search**: Combines vector + keyword for better results

### Benchmarks

| Operation | Time | Notes |
|-----------|------|-------|
| Document upload (1MB) | ~2s | Including chunking & indexing |
| Vector search | <100ms | ChromaDB similarity search |
| Web search | ~2s | Google API + content fetch |
| AI response | 3-10s | Depends on model & context |

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup
```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run tests before committing
cd backend
pytest tests/

cd frontend
npm test
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **[Anthropic](https://www.anthropic.com/)** for Claude AI
- **[ChromaDB](https://www.trychroma.com/)** for vector database
- **[FastAPI](https://fastapi.tiangolo.com/)** for the backend framework
- **[React](https://react.dev/)** for the frontend framework
- **[Tailwind CSS](https://tailwindcss.com/)** for styling



## 🔗 Related Projects

- [LangChain](https://github.com/langchain-ai/langchain) - LLM framework
- [LlamaIndex](https://github.com/run-llama/llama_index) - Data framework for LLMs
- [Perplexity AI](https://www.perplexity.ai/) - Inspiration for citation system

## 🗺️ Roadmap

- [ ] Add support for more document types (DOCX, PPTX)
- [ ] Implement user authentication
- [ ] Add conversation export (PDF/Markdown)
- [ ] Multi-language support
- [ ] Voice input/output
- [ ] Mobile app (React Native)
- [ ] Advanced analytics dashboard
- [ ] Team collaboration features
- [ ] API rate limiting
- [ ] Kubernetes deployment config


**Built with:** Python • FastAPI • React • Claude AI • ChromaDB • Redis