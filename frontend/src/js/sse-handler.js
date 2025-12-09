// SSE Handler for Chat Streaming

import { getToken, clearToken } from './auth.js';

export class SSEHandler {
  constructor(options = {}) {
    this.onStart = options.onStart || (() => {});
    this.onDelta = options.onDelta || (() => {});
    this.onProgress = options.onProgress || (() => {});
    this.onDone = options.onDone || (() => {});
    this.onError = options.onError || (() => {});
    this.onRestart = options.onRestart || (() => {});
  }

  async sendMessage(message, conversationId = null) {
    const token = getToken();

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          message: message,
          conversation_id: conversationId,
        }),
      });

      if (response.status === 401) {
        clearToken();
        window.location.href = '/login.html';
        throw new Error('Session expired');
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Request failed');
      }

      await this.processStream(response);
    } catch (error) {
      this.onError(error.message);
      throw error;
    }
  }

  async processStream(response) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let currentEventType = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Process SSE events
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith('event:')) {
          currentEventType = line.substring(6).trim();
        } else if (line.startsWith('data:')) {
          try {
            const data = JSON.parse(line.substring(5).trim());
            this.handleEvent(currentEventType, data);
          } catch (e) {
            console.error('Failed to parse SSE data:', e);
          }
        }
      }
    }
  }

  handleEvent(eventType, data) {
    switch (eventType) {
      case 'start':
        this.onStart(data.conversation_id);
        break;
      case 'delta':
        this.onDelta(data.content);
        break;
      case 'progress':
        this.onProgress(data.step, data.tool);
        break;
      case 'done':
        this.onDone();
        break;
      case 'restart':
        this.onRestart(data.conversation_id);
        break;
      case 'error':
        this.onError(data.error);
        break;
    }
  }
}
