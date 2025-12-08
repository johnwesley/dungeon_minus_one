// Main App Entry Point

import { requireAuth, fetchWithAuth, logout, setupHTMXAuth } from './auth.js';
import { SSEHandler } from './sse-handler.js';

class DungeonApp {
  constructor() {
    // Check auth first
    if (!requireAuth()) return;

    this.currentConversationId = null;
    this.isStreaming = false;
    this.conversations = [];

    // DOM elements
    this.conversationList = document.getElementById('conversation-list');
    this.chatMessages = document.getElementById('chat-messages');
    this.chatForm = document.getElementById('chat-form');
    this.messageInput = document.getElementById('message-input');
    this.sendBtn = document.getElementById('send-btn');
    this.logoutBtn = document.getElementById('logout-btn');
    this.currentLocationEl = document.getElementById('current-location');
    this.inventoryListEl = document.getElementById('inventory-list');
    this.treasuresSectionEl = document.getElementById('treasures-section');
    this.treasuresListEl = document.getElementById('treasures-list');
    this.treasureCountEl = document.getElementById('treasure-count');

    this.init();
  }

  async init() {
    setupHTMXAuth();
    this.bindEvents();
    await this.loadConversations();

    // Auto-start if no conversations
    if (this.conversations.length === 0) {
      this.startNewGame();
    }
  }

  bindEvents() {
    // Form submission
    this.chatForm.addEventListener('submit', (e) => {
      e.preventDefault();
      this.sendMessage();
    });

    // Auto-resize textarea
    this.messageInput.addEventListener('input', () => {
      this.messageInput.style.height = 'auto';
      this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 200) + 'px';
    });

    // Enter to send (Shift+Enter for newline)
    this.messageInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage();
      }
    });

    // Logout button
    if (this.logoutBtn) {
      this.logoutBtn.addEventListener('click', logout);
    }
  }

  async loadConversations() {
    try {
      const response = await fetchWithAuth('/api/conversations');
      if (!response) return;

      this.conversations = await response.json();
      this.renderConversationList();

      // Auto-select most recent if we have conversations but none selected
      if (this.conversations.length > 0 && !this.currentConversationId) {
        await this.selectConversation(this.conversations[0].id);
      }
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  }

  renderConversationList() {
    this.conversationList.innerHTML = '';

    if (this.conversations.length === 0) {
      this.conversationList.innerHTML = '<div class="empty-state">No adventures yet</div>';
      return;
    }

    this.conversations.forEach(conv => {
      const item = this.createConversationItem(conv);
      this.conversationList.appendChild(item);
    });
  }

  createConversationItem(conversation) {
    const item = document.createElement('div');
    item.className = 'conversation-item';
    item.dataset.id = conversation.id;

    if (this.currentConversationId === conversation.id) {
      item.classList.add('active');
    }

    item.innerHTML = `
      <span class="conversation-title">${this.escapeHtml(conversation.title || 'Untitled')}</span>
      <button class="conversation-delete" title="Delete">x</button>
    `;

    // Click to select
    item.addEventListener('click', (e) => {
      if (!e.target.classList.contains('conversation-delete')) {
        this.selectConversation(conversation.id);
      }
    });

    // Delete button
    const deleteBtn = item.querySelector('.conversation-delete');
    deleteBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      this.deleteConversation(conversation.id);
    });

    return item;
  }

  async selectConversation(conversationId) {
    this.currentConversationId = conversationId;
    this.updateActiveConversation();

    try {
      const response = await fetchWithAuth(`/api/conversations/${conversationId}`);
      if (!response) return;

      const conversation = await response.json();
      this.chatMessages.innerHTML = '';

      conversation.messages.forEach(msg => {
        this.appendMessage(msg.role, msg.content);
      });

      this.scrollToBottom();
      await this.loadGameState();
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  }

  updateActiveConversation() {
    document.querySelectorAll('.conversation-item').forEach(item => {
      item.classList.toggle('active', item.dataset.id === String(this.currentConversationId));
    });
  }

  async deleteConversation(conversationId) {
    if (!confirm('Delete this adventure?')) return;

    try {
      await fetchWithAuth(`/api/conversations/${conversationId}`, {
        method: 'DELETE',
      });

      if (this.currentConversationId === conversationId) {
        this.currentConversationId = null;
        this.chatMessages.innerHTML = '';
      }

      await this.loadConversations();

      // Start new game if no conversations left
      if (this.conversations.length === 0) {
        this.startNewGame();
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error);
    }
  }

  startNewGame() {
    this.currentConversationId = null;
    this.chatMessages.innerHTML = '';
    this.updateActiveConversation();

    // Auto-send "Wake up" to start the game
    this.sendMessage('Wake up');
  }

  async sendMessage(messageText = null) {
    const message = messageText || this.messageInput.value.trim();
    if (!message || this.isStreaming) return;

    // Clear input only if it was the source
    if (!messageText) {
      this.messageInput.value = '';
      this.messageInput.style.height = 'auto';
    }

    // Append user message
    this.appendMessage('user', message);

    // Create assistant message placeholder
    const assistantMsgEl = this.appendMessage('assistant', '');
    const contentEl = assistantMsgEl.querySelector('.message-content');
    contentEl.innerHTML = '<span class="streaming-indicator cursor"></span>';

    // Disable input during streaming
    this.setStreaming(true);

    let assistantContent = '';

    const sseHandler = new SSEHandler({
      onStart: (conversationId) => {
        this.currentConversationId = conversationId;
      },
      onDelta: (content) => {
        assistantContent += content;
        contentEl.textContent = assistantContent;
        this.scrollToBottom();
      },
      onProgress: (step, tool) => {
        if (step === 'using_tool') {
          this.showProgress(assistantMsgEl, `Using ${tool}...`);
        } else if (step === 'tool_done') {
          this.hideProgress(assistantMsgEl);
        }
      },
      onDone: async () => {
        this.hideProgress(assistantMsgEl);
        await this.loadConversations();
        await this.loadGameState();
      },
      onError: (error) => {
        contentEl.textContent = `Error: ${error}`;
      },
    });

    try {
      await sseHandler.sendMessage(message, this.currentConversationId);
    } catch (error) {
      console.error('Failed to send message:', error);
      if (!contentEl.textContent) {
        contentEl.textContent = `Error: ${error.message}`;
      }
    } finally {
      this.setStreaming(false);
    }
  }

  appendMessage(role, content) {
    const displayNames = { user: 'Burglar', assistant: 'Narrator' };
    const messageEl = document.createElement('div');
    messageEl.className = `message ${role}`;
    messageEl.innerHTML = `
      <div class="message-role">${displayNames[role] || role}</div>
      <div class="message-content">${this.escapeHtml(content)}</div>
    `;
    this.chatMessages.appendChild(messageEl);
    this.scrollToBottom();
    return messageEl;
  }

  showProgress(messageEl, text) {
    let progressEl = messageEl.querySelector('.progress-indicator');
    if (!progressEl) {
      progressEl = document.createElement('div');
      progressEl.className = 'progress-indicator streaming-indicator';
      const contentEl = messageEl.querySelector('.message-content');
      messageEl.insertBefore(progressEl, contentEl);
    }
    progressEl.textContent = text;
  }

  hideProgress(messageEl) {
    const progressEl = messageEl.querySelector('.progress-indicator');
    if (progressEl) {
      progressEl.remove();
    }
  }

  setStreaming(streaming) {
    this.isStreaming = streaming;
    this.sendBtn.disabled = streaming;
    this.messageInput.disabled = streaming;
    if (!streaming) {
      this.messageInput.focus();
    }
  }

  scrollToBottom() {
    this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  async loadGameState() {
    if (!this.currentConversationId) return;

    try {
      const response = await fetchWithAuth(`/api/conversations/${this.currentConversationId}/game-state`);
      if (!response) return;

      const state = await response.json();
      this.renderGameState(state);
    } catch (error) {
      console.error('Failed to load game state:', error);
    }
  }

  renderGameState(state) {
    // Update location
    if (this.currentLocationEl) {
      this.currentLocationEl.textContent = state.current_location || 'Unknown';
    }

    // Update inventory
    if (this.inventoryListEl) {
      if (!state.inventory || state.inventory.length === 0) {
        this.inventoryListEl.innerHTML = '<li class="empty-inventory">Empty</li>';
      } else {
        this.inventoryListEl.innerHTML = state.inventory
          .map(item => `<li>${this.escapeHtml(item)}</li>`)
          .join('');
      }
    }

    // Update treasures (show section only if treasures found)
    if (this.treasuresSectionEl && this.treasuresListEl) {
      const treasures = state.treasures_found || [];

      if (treasures.length === 0) {
        this.treasuresSectionEl.style.display = 'none';
      } else {
        this.treasuresSectionEl.style.display = '';
        this.treasureCountEl.textContent = treasures.length;
        this.treasuresListEl.innerHTML = treasures
          .map(item => `<li>${this.escapeHtml(item)}</li>`)
          .join('');
      }
    }
  }
}

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
  window.dungeonApp = new DungeonApp();
});
