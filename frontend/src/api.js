import axios from 'axios';

const API_BASE = '/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Chat APIs
export const sendChatMessage = async (message, sessionId = null, useWebSearch = false, model = null, useDocumentSearch = true) => {
  const response = await api.post('/chat', {
    message,
    session_id: sessionId,
    use_web_search: useWebSearch,
    model: model,
    use_document_search: useDocumentSearch,
  });
  return response.data;
};

// Model APIs
export const getAvailableModels = async () => {
  const response = await api.get('/models');
  return response.data;
};

// Document APIs
export const uploadDocument = async (file, onProgress = null) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await api.post('/documents/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent) => {
      if (onProgress) {
        const percentCompleted = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total
        );
        onProgress(percentCompleted);
      }
    },
  });
  return response.data;
};

export const getDocuments = async () => {
  const response = await api.get('/documents');
  return response.data;
};

export const deleteDocument = async (documentId) => {
  const response = await api.delete(`/documents/${documentId}`);
  return response.data;
};

// Session APIs
export const createSession = async () => {
  const response = await api.post('/sessions/create');
  return response.data;
};

export const getSession = async (sessionId) => {
  const response = await api.get(`/sessions/${sessionId}`);
  return response.data;
};

export const deleteSession = async (sessionId) => {
  const response = await api.delete(`/sessions/${sessionId}`);
  return response.data;
};

export const getSessions = async () => {
  const response = await api.get('/sessions');
  return response.data;
};

// Health check
export const checkHealth = async () => {
  const response = await api.get('/health');
  return response.data;
};

export default api;