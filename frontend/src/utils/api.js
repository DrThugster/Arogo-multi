// src/utils/api.js
import axios from 'axios';

const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const consultationApi = {
  startConsultation: async (userData) => {
    const response = await api.post('/api/consultation/start', userData);
    return response.data;
  },

  getSummary: async (consultationId) => {
    const response = await api.get(`/api/diagnostic/summary/${consultationId}`);
    return response.data;
  },

  getReport: async (consultationId, language = 'en') => {
    const response = await api.get(`/api/report/${consultationId}`, {
      params: { language },
      responseType: 'blob'
    });
    return response.data;
  },

  submitFeedback: async (feedbackData) => {
    const response = await api.post('/api/feedback/submit', feedbackData);
    return response.data;
  }
};

export const speechApi = {
  speechToText: async (audioBlob, options = {}) => {
    const formData = new FormData();
    formData.append('audio', audioBlob);
    if (options.sourceLanguage) formData.append('source_language', options.sourceLanguage);
    if (options.enableAutoDetect) formData.append('enable_auto_detect', options.enableAutoDetect);
    
    const response = await api.post('/api/speech/speech-to-text', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
  },

  textToSpeech: async (text, options = {}) => {
    const response = await api.post('/api/speech/text-to-speech', {
      text,
      target_language: options.targetLanguage || 'en',
      voice_gender: options.voiceGender || 'female',
      voice_style: options.voiceStyle
    });
    return response.data;
  },

  translateSpeech: async (audioBlob, options = {}) => {
    const formData = new FormData();
    formData.append('audio', audioBlob);
    if (options.sourceLanguage) formData.append('source_language', options.sourceLanguage);
    formData.append('target_language', options.targetLanguage || 'en');
    formData.append('auto_detect', options.autoDetect || true);
    formData.append('voice_gender', options.voiceGender || 'female');

    const response = await api.post('/api/speech/translate-speech', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
  }
};

export const WebSocketService = {
  connect: (consultationId, options = {}) => {
    const ws = new WebSocket(`${process.env.REACT_APP_WS_URL || 'ws://localhost:8000'}/ws/${consultationId}`);
    
    // Add language preferences to initial connection
    ws.onopen = () => {
      ws.send(JSON.stringify({
        type: 'init',
        preferences: {
          language: options.language || 'en',
          autoDetect: options.autoDetect || true,
          voicePreferences: options.voicePreferences || {
            enabled: true,
            gender: 'female'
          }
        }
      }));
      if (options.onOpen) options.onOpen();
    };

    if (options.onMessage) ws.onmessage = options.onMessage;
    if (options.onError) ws.onerror = options.onError;
    if (options.onClose) ws.onclose = options.onClose;

    return ws;
  }
};

export default api;