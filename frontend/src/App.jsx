import { useState, useEffect, useRef } from 'react';
import { 
  Send, 
  Upload, 
  FileText, 
  X, 
  Search, 
  MessageSquare, 
  Loader2, 
  ExternalLink,
  Bot,
  User,
  Trash2,
  Settings,
  Globe,
  Database,
  Clock
} from 'lucide-react';
import {
  sendChatMessage,
  uploadDocument,
  getDocuments,
  deleteDocument,
  getAvailableModels,
  getSessions,
  getSession
} from './api';

// Component to render message with inline citations
function MessageWithCitations({ content, sources }) {
  const [hoveredSource, setHoveredSource] = useState(null);
  
  if (!sources || sources.length === 0) {
    return (
      <div className="prose prose-sm max-w-none">
        <p className="whitespace-pre-wrap m-0">{content}</p>
      </div>
    );
  }
  
  // Parse content to identify [Source N] citations
  const parts = [];
  let lastIndex = 0;
  const citationRegex = /\[Source (\d+)\]/g;
  let match;
  
  while ((match = citationRegex.exec(content)) !== null) {
    // Add text before citation
    if (match.index > lastIndex) {
      parts.push({
        type: 'text',
        content: content.substring(lastIndex, match.index)
      });
    }
    
    // Add citation
    const sourceNum = parseInt(match[1]);
    parts.push({
      type: 'citation',
      sourceNum: sourceNum,
      fullMatch: match[0]
    });
    
    lastIndex = match.index + match[0].length;
  }
  
  // Add remaining text
  if (lastIndex < content.length) {
    parts.push({
      type: 'text',
      content: content.substring(lastIndex)
    });
  }
  
  return (
    <div className="prose prose-sm max-w-none relative">
      <div className="whitespace-pre-wrap">
        {parts.map((part, idx) => {
          if (part.type === 'text') {
            return <span key={idx}>{part.content}</span>;
          } else {
            const source = sources.find(s => s.source_number === part.sourceNum);
            
            return (
              <span
                key={idx}
                className="relative inline-block"
                onMouseEnter={() => setHoveredSource(part.sourceNum)}
                onMouseLeave={() => setHoveredSource(null)}
              >
                <span className="inline-flex items-center justify-center w-5 h-5 text-xs font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded cursor-pointer hover:bg-blue-100 transition-colors">
                  {part.sourceNum}
                </span>
                
                {/* Tooltip */}
                {hoveredSource === part.sourceNum && source && (
                  <div className="absolute z-50 bottom-full left-0 mb-2 w-72 bg-white border border-slate-300 rounded-lg shadow-lg p-3 text-xs">
                    <div className="font-semibold text-slate-800 mb-1 flex items-center justify-between">
                      <span>
                        {source.type === 'document' ? (
                          <span className="flex items-center gap-1">
                            <FileText className="w-3 h-3" />
                            {source.filename}
                          </span>
                        ) : (
                          <span className="flex items-center gap-1">
                            <Globe className="w-3 h-3" />
                            {source.title}
                          </span>
                        )}
                      </span>
                      {source.url && (
                        <a
                          href={source.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:text-blue-800"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                    </div>
                    <p className="text-slate-600 line-clamp-3 mb-1">{source.preview}</p>
                    {source.similarity && (
                      <div className="text-slate-500 text-xs">
                        Relevance: {(source.similarity * 100).toFixed(0)}%
                      </div>
                    )}
                    <div className="absolute bottom-0 left-4 transform translate-y-1/2 rotate-45 w-2 h-2 bg-white border-r border-b border-slate-300"></div>
                  </div>
                )}
              </span>
            );
          }
        })}
      </div>
    </div>
  );
}

function App() {
  // State
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState(null);
  const [useWebSearch, setUseWebSearch] = useState(false);
  const [useDocumentSearch, setUseDocumentSearch] = useState(true);
  const [activeTab, setActiveTab] = useState('chat');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [chatSessions, setChatSessions] = useState([]);
  
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  
  // Load session from localStorage
  useEffect(() => {
    const savedSessionId = localStorage.getItem('rag_session_id');
    if (savedSessionId) {
      setSessionId(savedSessionId);
      loadSessionMessages(savedSessionId);
    }
    loadChatSessions();
  }, []);
  
  // Scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages]);
  
  // Load documents and models on mount
  useEffect(() => {
    fetchDocuments();
    fetchModels();
  }, []);
  
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };
  
  const loadSessionMessages = async (sid) => {
    try {
      const sessionData = await getSession(sid);
      if (sessionData.messages) {
        setMessages(sessionData.messages);
      }
    } catch (error) {
      console.error('Failed to load session:', error);
    }
  };
  
  const loadChatSessions = async () => {
    try {
      const data = await getSessions();
      setChatSessions(data.sessions || []);
    } catch (error) {
      console.error('Failed to load sessions:', error);
    }
  };
  
  const fetchDocuments = async () => {
    try {
      const docs = await getDocuments();
      setDocuments(docs);
    } catch (error) {
      console.error('Failed to fetch documents:', error);
    }
  };
  
  const fetchModels = async () => {
    try {
      const data = await getAvailableModels();
      setModels(data.models);
      setSelectedModel(data.default_model);
    } catch (error) {
      console.error('Failed to fetch models:', error);
    }
  };
  
  const handleSendMessage = async (e) => {
    e?.preventDefault();
    
    if (!input.trim() || loading) return;
    
    const userMessage = {
      role: 'user',
      content: input,
      timestamp: new Date().toISOString()
    };
    
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);
    
    try {
      const response = await sendChatMessage(
        input,
        sessionId,
        useWebSearch,
        selectedModel
      );
      
      // Save session ID
      if (!sessionId) {
        setSessionId(response.session_id);
        localStorage.setItem('rag_session_id', response.session_id);
        loadChatSessions();
      }
      
      const assistantMessage = {
        role: 'assistant',
        content: response.response,
        sources: response.sources,
        model_used: response.model_used,
        timestamp: response.timestamp
      };
      
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Failed to send message:', error);
      const errorMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString(),
        error: true
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };
  
  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    setUploading(true);
    setUploadProgress(0);
    
    try {
      await uploadDocument(file, (progress) => {
        setUploadProgress(progress);
      });
      
      await fetchDocuments();
      alert('Document uploaded successfully!');
    } catch (error) {
      console.error('Upload failed:', error);
      alert('Failed to upload document. Please try again.');
    } finally {
      setUploading(false);
      setUploadProgress(0);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };
  
  const handleDeleteDocument = async (docId) => {
    if (!confirm('Are you sure you want to delete this document?')) return;
    
    try {
      await deleteDocument(docId);
      await fetchDocuments();
    } catch (error) {
      console.error('Delete failed:', error);
      alert('Failed to delete document.');
    }
  };
  
  const handleNewChat = () => {
    setMessages([]);
    setSessionId(null);
    localStorage.removeItem('rag_session_id');
    loadChatSessions();
  };
  
  const handleLoadSession = async (sid) => {
    setSessionId(sid);
    localStorage.setItem('rag_session_id', sid);
    await loadSessionMessages(sid);
    setActiveTab('chat');
  };
  
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Sidebar */}
      <div className="w-72 bg-white border-r border-slate-200 flex flex-col shadow-sm">
        {/* Header */}
        <div className="p-4 border-b border-slate-200">
          <h1 className="text-xl font-bold text-slate-800 flex items-center gap-2">
            <Bot className="w-6 h-6 text-blue-600" />
            RAG Chatbot
          </h1>
          <p className="text-xs text-slate-500 mt-1">Powered by Claude AI</p>
        </div>
        
        {/* New Chat Button */}
        <div className="p-4 border-b border-slate-200">
          <button
            onClick={handleNewChat}
            className="w-full bg-blue-600 text-white px-4 py-3 rounded-lg hover:bg-blue-700 transition-colors font-medium shadow-sm"
          >
            + New Chat
          </button>
        </div>
        
        {/* Chat History */}
        {chatSessions.length > 0 && (
          <div className="px-4 py-2 border-b border-slate-200">
            <h3 className="text-xs font-semibold text-slate-500 uppercase mb-2 flex items-center gap-2">
              <Clock className="w-3 h-3" />
              Recent Chats
            </h3>
            <div className="space-y-1 max-h-32 overflow-y-auto">
              {chatSessions.slice(0, 5).map((session) => (
                <button
                  key={session.session_id}
                  onClick={() => handleLoadSession(session.session_id)}
                  className={`w-full text-left px-3 py-2 rounded text-xs hover:bg-slate-50 transition-colors ${
                    session.session_id === sessionId ? 'bg-blue-50 text-blue-700' : 'text-slate-600'
                  }`}
                >
                  <div className="truncate">
                    {session.message_count} messages
                  </div>
                  <div className="text-xs text-slate-400 mt-0.5">
                    {new Date(session.last_activity).toLocaleDateString()}
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
        
        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
          <button
            onClick={() => setActiveTab('chat')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
              activeTab === 'chat' 
                ? 'bg-blue-50 text-blue-700 font-medium shadow-sm' 
                : 'text-slate-600 hover:bg-slate-50'
            }`}
          >
            <MessageSquare className="w-5 h-5" />
            Chat
          </button>
          
          <button
            onClick={() => setActiveTab('documents')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
              activeTab === 'documents' 
                ? 'bg-blue-50 text-blue-700 font-medium shadow-sm' 
                : 'text-slate-600 hover:bg-slate-50'
            }`}
          >
            <FileText className="w-5 h-5" />
            Documents
            <span className="ml-auto text-xs bg-slate-200 px-2 py-1 rounded-full">
              {documents.length}
            </span>
          </button>
          
          <button
            onClick={() => setActiveTab('settings')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
              activeTab === 'settings' 
                ? 'bg-blue-50 text-blue-700 font-medium shadow-sm' 
                : 'text-slate-600 hover:bg-slate-50'
            }`}
          >
            <Settings className="w-5 h-5" />
            Settings
          </button>
        </nav>
      </div>
      
      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {activeTab === 'chat' && (
          <>
            {/* Chat Header */}
            <div className="bg-white border-b border-slate-200 px-6 py-4 shadow-sm">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-slate-800">Chat</h2>
                  <p className="text-sm text-slate-500">
                    Ask questions about your documents
                  </p>
                </div>
                <div className="flex items-center gap-4">
                  {/* Document Search Toggle */}
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={useDocumentSearch}
                      onChange={(e) => setUseDocumentSearch(e.target.checked)}
                      className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                    />
                    <Database className="w-4 h-4 text-slate-600" />
                    <span className="text-sm text-slate-700">Documents</span>
                  </label>
                  
                  {/* Web Search Toggle */}
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={useWebSearch}
                      onChange={(e) => setUseWebSearch(e.target.checked)}
                      className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                    />
                    <Globe className="w-4 h-4 text-slate-600" />
                    <span className="text-sm text-slate-700">Web</span>
                  </label>
                </div>
              </div>
              
              {/* Search Status Indicators */}
              <div className="flex gap-2 mt-2">
                {useDocumentSearch && (
                  <span className="inline-flex items-center gap-1 text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded">
                    <Database className="w-3 h-3" />
                    {documents.length} docs indexed
                  </span>
                )}
                {useWebSearch && (
                  <span className="inline-flex items-center gap-1 text-xs bg-green-50 text-green-700 px-2 py-1 rounded">
                    <Globe className="w-3 h-3" />
                    Web search enabled
                  </span>
                )}
                {!useDocumentSearch && !useWebSearch && (
                  <span className="inline-flex items-center gap-1 text-xs bg-amber-50 text-amber-700 px-2 py-1 rounded">
                    ⚠️ No search sources enabled
                  </span>
                )}
              </div>
            </div>
            
            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
              {messages.length === 0 && (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center max-w-md">
                    <Bot className="w-16 h-16 text-slate-300 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-slate-700 mb-2">
                      Start a conversation
                    </h3>
                    <p className="text-sm text-slate-500 mb-4">
                      Upload documents to your knowledge base and ask questions.
                      Enable web search for real-time information.
                    </p>
                    <div className="text-xs text-slate-400 space-y-1">
                      <div>💡 Toggle "Documents" to search your uploaded files</div>
                      <div>🌐 Toggle "Web" to search the internet</div>
                    </div>
                  </div>
                </div>
              )}
              
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex gap-4 message-enter ${
                    msg.role === 'user' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  {msg.role === 'assistant' && (
                    <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0">
                      <Bot className="w-5 h-5 text-white" />
                    </div>
                  )}
                  
                  <div
                    className={`max-w-3xl rounded-2xl px-5 py-3 ${
                      msg.role === 'user'
                        ? 'bg-blue-600 text-white'
                        : 'bg-white border border-slate-200 text-slate-800 shadow-sm'
                    }`}
                  >
                    {msg.role === 'assistant' ? (
                      <MessageWithCitations content={msg.content} sources={msg.sources} />
                    ) : (
                      <div className="prose prose-sm max-w-none">
                        <p className="whitespace-pre-wrap m-0">{msg.content}</p>
                      </div>
                    )}
                    
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="mt-4 pt-4 border-t border-slate-200">
                        <p className="text-xs font-semibold text-slate-600 mb-3">
                          Sources ({msg.sources.length}):
                        </p>
                        <div className="space-y-2">
                          {msg.sources.map((source, i) => (
                            <div
                              key={i}
                              className="text-xs bg-slate-50 rounded-lg p-3 border border-slate-200"
                            >
                              <div className="flex items-start justify-between gap-2 mb-1">
                                <span className="font-medium text-slate-700">
                                  [{source.source_number}] {source.type === 'document' 
                                    ? source.filename 
                                    : source.title}
                                </span>
                                {source.url && (
                                  <a
                                    href={source.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-blue-600 hover:text-blue-800"
                                  >
                                    <ExternalLink className="w-3 h-3" />
                                  </a>
                                )}
                              </div>
                              <p className="text-slate-600 line-clamp-2">{source.preview}</p>
                              {source.similarity && (
                                <span className="text-slate-500 mt-1 inline-block">
                                  Relevance: {(source.similarity * 100).toFixed(0)}%
                                </span>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {msg.model_used && (
                      <p className="text-xs text-slate-500 mt-3">
                        Model: {msg.model_used.split('-').slice(0, 3).join(' ').toUpperCase()}
                      </p>
                    )}
                    
                    <p className="text-xs opacity-60 mt-2">
                      {new Date(msg.timestamp).toLocaleTimeString()}
                    </p>
                  </div>
                  
                  {msg.role === 'user' && (
                    <div className="w-8 h-8 rounded-full bg-slate-600 flex items-center justify-center flex-shrink-0">
                      <User className="w-5 h-5 text-white" />
                    </div>
                  )}
                </div>
              ))}
              
              {loading && (
                <div className="flex gap-4 message-enter">
                  <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0">
                    <Bot className="w-5 h-5 text-white" />
                  </div>
                  <div className="bg-white border border-slate-200 rounded-2xl px-5 py-4 shadow-sm">
                    <div className="flex gap-2">
                      <div className="w-2 h-2 bg-slate-400 rounded-full dot-pulse"></div>
                      <div className="w-2 h-2 bg-slate-400 rounded-full dot-pulse"></div>
                      <div className="w-2 h-2 bg-slate-400 rounded-full dot-pulse"></div>
                    </div>
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>
            
            {/* Input */}
            <div className="bg-white border-t border-slate-200 px-6 py-4 shadow-lg">
              <form onSubmit={handleSendMessage} className="flex gap-3">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask a question..."
                  className="flex-1 resize-none border border-slate-300 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  rows="1"
                  disabled={loading}
                />
                <button
                  type="submit"
                  disabled={loading || !input.trim()}
                  className="bg-blue-600 text-white rounded-xl px-6 py-3 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2 shadow-sm"
                >
                  {loading ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <Send className="w-5 h-5" />
                  )}
                </button>
              </form>
            </div>
          </>
        )}
        
        {activeTab === 'documents' && (
          <DocumentsTab
            documents={documents}
            uploading={uploading}
            uploadProgress={uploadProgress}
            onFileUpload={handleFileUpload}
            onDeleteDocument={handleDeleteDocument}
            fileInputRef={fileInputRef}
          />
        )}
        
        {activeTab === 'settings' && (
          <SettingsTab
            models={models}
            selectedModel={selectedModel}
            setSelectedModel={setSelectedModel}
            useDocumentSearch={useDocumentSearch}
            setUseDocumentSearch={setUseDocumentSearch}
            useWebSearch={useWebSearch}
            setUseWebSearch={setUseWebSearch}
          />
        )}
      </div>
    </div>
  );
}

// Documents Tab Component
function DocumentsTab({ documents, uploading, uploadProgress, onFileUpload, onDeleteDocument, fileInputRef }) {
  return (
    <>
      <div className="bg-white border-b border-slate-200 px-6 py-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-800">Knowledge Base</h2>
            <p className="text-sm text-slate-500">{documents.length} documents indexed</p>
          </div>
          <div>
            <input
              ref={fileInputRef}
              type="file"
              onChange={onFileUpload}
              className="hidden"
              accept=".txt,.pdf,.json"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2 shadow-sm"
            >
              {uploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {uploadProgress}%
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  Upload
                </>
              )}
            </button>
          </div>
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {documents.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md">
              <FileText className="w-16 h-16 text-slate-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-700 mb-2">No documents yet</h3>
              <p className="text-sm text-slate-500 mb-4">
                Upload documents to build your knowledge base
              </p>
              <button
                onClick={() => fileInputRef.current?.click()}
                className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700"
              >
                Upload Your First Document
              </button>
            </div>
          </div>
        ) : (
          <div className="grid gap-4">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="bg-white border border-slate-200 rounded-lg p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3 flex-1">
                    <FileText className="w-5 h-5 text-blue-600 mt-1 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-slate-800 truncate">{doc.filename}</h3>
                      <p className="text-sm text-slate-500 mt-1">
                        {doc.chunks_count} chunks • {doc.word_count} words • 
                        Uploaded {new Date(doc.uploaded_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => onDeleteDocument(doc.id)}
                    className="text-red-600 hover:text-red-800 p-2 rounded hover:bg-red-50 transition-colors flex-shrink-0"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}

// Settings Tab Component
function SettingsTab({ models, selectedModel, setSelectedModel, useDocumentSearch, setUseDocumentSearch, useWebSearch, setUseWebSearch }) {
  return (
    <>
      <div className="bg-white border-b border-slate-200 px-6 py-4 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-800">Settings</h2>
        <p className="text-sm text-slate-500">Configure your chatbot preferences</p>
      </div>
      
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
        <div className="max-w-2xl">
          {/* Search Settings */}
          <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-sm">
            <h3 className="text-md font-semibold text-slate-800 mb-4">Search Settings</h3>
            
            <div className="space-y-4">
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useDocumentSearch}
                  onChange={(e) => setUseDocumentSearch(e.target.checked)}
                  className="mt-1"
                />
                <div>
                  <div className="font-medium text-slate-800">Document Search</div>
                  <div className="text-sm text-slate-500 mt-1">
                    Search your uploaded documents for relevant information
                  </div>
                </div>
              </label>
              
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useWebSearch}
                  onChange={(e) => setUseWebSearch(e.target.checked)}
                  className="mt-1"
                />
                <div>
                  <div className="font-medium text-slate-800">Web Search</div>
                  <div className="text-sm text-slate-500 mt-1">
                    Search the web for real-time information
                  </div>
                </div>
              </label>
            </div>
          </div>
          
          {/* AI Model */}
          <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-sm">
            <h3 className="text-md font-semibold text-slate-800 mb-4">AI Model</h3>
            <p className="text-sm text-slate-600 mb-4">
              Select which Claude model to use for generating responses
            </p>
            
            <div className="space-y-3">
              {models.map((model) => (
                <label
                  key={model.id}
                  className="flex items-start gap-3 p-4 border border-slate-200 rounded-lg hover:bg-slate-50 cursor-pointer transition-colors"
                >
                  <input
                    type="radio"
                    name="model"
                    value={model.id}
                    checked={selectedModel === model.id}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="mt-1"
                  />
                  <div className="flex-1">
                    <div className="font-medium text-slate-800">{model.display_name}</div>
                    <div className="text-xs text-slate-500 mt-1">{model.id}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

export default App;