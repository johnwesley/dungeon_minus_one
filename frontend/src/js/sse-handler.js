// SSE Handler for Chat Streaming with Reconnection Support

import { getCsrfToken, clearSession } from './auth.js';

// Retry configuration
const RETRY_CONFIG = {
  maxRetries: 5,
  baseDelayMs: 1000,
  maxDelayMs: 30000,
  backoffMultiplier: 2,
};

export class SSEHandler {
  constructor(options = {}) {
    this.onStart = options.onStart || (() => {});
    this.onDelta = options.onDelta || (() => {});
    this.onProgress = options.onProgress || (() => {});
    this.onDone = options.onDone || (() => {});
    this.onError = options.onError || (() => {});
    this.onRestart = options.onRestart || (() => {});
    this.onConnectionStatus = options.onConnectionStatus || (() => {});

    // State for reconnection
    this._currentRequest = null;
    this._retryCount = 0;
    this._receivedDone = false;
    this._serverShutdown = false;
  }

  /**
   * Calculate delay for exponential backoff
   */
  _getRetryDelay() {
    const delay = Math.min(
      RETRY_CONFIG.baseDelayMs * Math.pow(RETRY_CONFIG.backoffMultiplier, this._retryCount),
      RETRY_CONFIG.maxDelayMs
    );
    // Add jitter (10-20% random variation)
    return delay + (delay * 0.1 * Math.random());
  }

  /**
   * Sleep for a given duration
   */
  _sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  async sendMessage(message, conversationId = null) {
    // Reset state for new request
    this._retryCount = 0;
    this._receivedDone = false;
    this._serverShutdown = false;
    this._currentRequest = { message, conversationId };

    await this._sendWithRetry();
  }

  async _sendWithRetry() {
    const { message, conversationId } = this._currentRequest;

    while (this._retryCount <= RETRY_CONFIG.maxRetries) {
      try {
        this.onConnectionStatus('connecting');

        const headers = {
          'Content-Type': 'application/json',
        };
        const csrfToken = getCsrfToken();
        if (csrfToken) {
          headers['X-CSRF-Token'] = csrfToken;
        }

        const response = await fetch('/api/chat', {
          method: 'POST',
          headers,
          credentials: 'same-origin',
          body: JSON.stringify({
            message: message,
            conversation_id: conversationId,
          }),
        });

        if (response.status === 401) {
          clearSession();
          window.location.href = '/login.html';
          throw new Error('Session expired');
        }

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || 'Request failed');
        }

        this.onConnectionStatus('connected');
        await this.processStream(response);

        // Check if stream ended properly
        if (this._receivedDone || this._serverShutdown) {
          // Normal completion or graceful shutdown
          this.onConnectionStatus('idle');
          return;
        }

        // Stream ended unexpectedly without 'done' event - attempt reconnection
        throw new Error('Stream ended unexpectedly');

      } catch (error) {
        // Don't retry auth errors or server shutdowns
        if (error.message === 'Session expired' || this._serverShutdown) {
          this.onConnectionStatus('idle');
          throw error;
        }

        this._retryCount++;

        if (this._retryCount > RETRY_CONFIG.maxRetries) {
          this.onConnectionStatus('disconnected');
          this.onError(`Connection lost after ${RETRY_CONFIG.maxRetries} retries: ${error.message}`);
          throw error;
        }

        const delay = this._getRetryDelay();
        console.log(`Connection lost, retry ${this._retryCount}/${RETRY_CONFIG.maxRetries} in ${Math.round(delay)}ms`);
        this.onConnectionStatus('reconnecting', { attempt: this._retryCount, delay });

        await this._sleep(delay);
      }
    }
  }

  async processStream(response) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let currentEventType = '';

    try {
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
    } finally {
      reader.releaseLock();
    }
  }

  handleEvent(eventType, data) {
    switch (eventType) {
      case 'start':
        this.onStart(data.conversation_id);
        // Update conversation_id for potential reconnection
        if (this._currentRequest) {
          this._currentRequest.conversationId = data.conversation_id;
        }
        break;
      case 'delta':
        this.onDelta(data.content);
        break;
      case 'progress':
        this.onProgress(data.step, data.tool);
        break;
      case 'done':
        this._receivedDone = true;
        this.onDone();
        break;
      case 'restart':
        this.onRestart(data.conversation_id);
        break;
      case 'error':
        this.onError(data.error);
        break;
      case 'closing':
        // Server is shutting down gracefully
        this._serverShutdown = true;
        console.log('Server shutdown notification received:', data.reason);
        this.onConnectionStatus('server_shutdown');
        break;
    }
  }
}
