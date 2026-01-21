// Main App Entry Point

import { requireAuth, fetchWithAuth, logout } from './auth.js';
import { SSEHandler } from './sse-handler.js';

class DungeonApp {
  constructor() {
    this.session = null;

    this.currentConversationId = null;
    this.isStreaming = false;
    this.conversations = [];
    this.restartPending = false;
    this.pendingRestartConversationId = null;
    this.restartPromptEl = null;

    // DOM elements
    this.userHandleEl = document.getElementById('user-handle');
    this.chatMessages = document.getElementById('chat-messages');
    this.chatForm = document.getElementById('chat-form');
    this.messageInput = document.getElementById('message-input');
    this.sendBtn = document.getElementById('send-btn');
    this.logoutBtn = document.getElementById('logout-btn');
    this.restartBtn = document.getElementById('restart-btn');
    this.currentLocationEl = document.getElementById('current-location');
    this.inventoryListEl = document.getElementById('inventory-list');
    this.trophyCaseSectionEl = document.getElementById('trophy-case-section');
    this.trophyCaseListEl = document.getElementById('trophy-case-list');
    this.trophyCountEl = document.getElementById('trophy-count');
    this.notificationsPanelEl = document.getElementById('notifications-panel');
    this.adminLinkEl = document.getElementById('admin-link');

    this.init();
  }

  async init() {
    this.session = await requireAuth();
    if (!this.session) return;
    this.bindEvents();
    this.displayUserHandle();
    await this.loadNotifications();
    await this.loadConversations();

    // Auto-start if no conversations
    if (this.conversations.length === 0) {
      this.startNewGame();
    }
  }

  displayUserHandle() {
    const username = this.session?.username;
    if (this.userHandleEl) {
      this.userHandleEl.textContent = username || 'Unknown';
    }
    // Show admin link if user is admin
    if (this.adminLinkEl && this.session?.is_admin) {
      this.adminLinkEl.style.display = '';
    }
  }

  async loadNotifications() {
    if (!this.notificationsPanelEl) return;

    try {
      const response = await fetchWithAuth('/api/notifications');
      if (!response) return;

      const notifications = await response.json();
      this.renderNotifications(notifications);
    } catch (error) {
      console.error('Failed to load notifications:', error);
    }
  }

  renderNotifications(notifications) {
    if (!this.notificationsPanelEl) return;

    if (!notifications || notifications.length === 0) {
      this.notificationsPanelEl.innerHTML = '';
      this.notificationsPanelEl.style.display = 'none';
      return;
    }

    this.notificationsPanelEl.style.display = '';
    this.notificationsPanelEl.innerHTML = notifications.map(notif => `
      <div class="notification notification-${this.escapeHtml(notif.notification_type)}" data-id="${this.escapeHtml(notif.id)}">
        <div class="notification-header">
          <span class="notification-title">${this.escapeHtml(notif.title)}</span>
          <button class="notification-dismiss" title="Dismiss">&times;</button>
        </div>
        <div class="notification-message">${this.escapeHtml(notif.message)}</div>
      </div>
    `).join('');

    // Bind dismiss buttons
    this.notificationsPanelEl.querySelectorAll('.notification-dismiss').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const notificationEl = e.target.closest('.notification');
        const notificationId = notificationEl.dataset.id;
        this.dismissNotification(notificationId);
      });
    });
  }

  async dismissNotification(notificationId) {
    try {
      await fetchWithAuth(`/api/notifications/${notificationId}/dismiss`, {
        method: 'POST',
      });
      await this.loadNotifications();
    } catch (error) {
      console.error('Failed to dismiss notification:', error);
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

    // Restart button
    if (this.restartBtn) {
      this.restartBtn.addEventListener('click', () => this.restartGame());
    }
  }

  async loadConversations() {
    try {
      const response = await fetchWithAuth('/api/conversations');
      if (!response) return;

      this.conversations = await response.json();

      // Auto-select most recent if we have conversations but none selected
      if (this.conversations.length > 0 && !this.currentConversationId) {
        await this.selectConversation(this.conversations[0].id);
      }
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  }

  async selectConversation(conversationId) {
    this.currentConversationId = conversationId;

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

  startNewGame() {
    this.currentConversationId = null;
    this.chatMessages.innerHTML = '';

    // Auto-send "Wake up" to start the game
    this.sendMessage('Wake up');
  }

  async restartGame() {
    if (this.restartPending) {
      await this.confirmRestart();
      return;
    }

    if (!this.currentConversationId) {
      // No conversation to restart, just start a new game
      this.startNewGame();
      return;
    }

    if (!confirm('Restart the game? All progress will be lost.')) return;

    // Send restart request to narrator - they'll generate a farewell and trigger the restart
    this.sendMessage('[RESTART]');
  }

  async sendMessage(messageText = null) {
    const message = messageText || this.messageInput.value.trim();
    if (!message || this.isStreaming || this.restartPending) return;

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
          const toolMessages = {
            'get_game_state': 'The world remembers...',
            'get_location_data': 'Somewhere, a map unfolds...',
            'update_game_state': 'The record adjusts itself...',
            'restart_game': 'Time rewinds reluctantly...'
          };
          const message = toolMessages[tool] || 'Something stirs...';
          this.showProgress(assistantMsgEl, message);
        } else if (step === 'tool_done') {
          this.hideProgress(assistantMsgEl);
        }
      },
      onDone: async () => {
        this.hideProgress(assistantMsgEl);
        await this.loadConversations();
        await this.loadGameState();
      },
      onRestart: async (conversationId) => {
        // Narrator triggered restart - wait for player confirmation
        this.setRestartPending(true, conversationId);
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
    const displayNames = { user: '>', assistant: 'System' };
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
    const shouldDisable = streaming || this.restartPending;
    this.sendBtn.disabled = shouldDisable;
    this.messageInput.disabled = shouldDisable;
    if (!shouldDisable) {
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

  setRestartPending(pending, conversationId = null) {
    this.restartPending = pending;
    this.pendingRestartConversationId = pending ? conversationId : null;

    if (pending) {
      this.showRestartPrompt();
    } else {
      this.clearRestartPrompt();
    }

    this.setStreaming(this.isStreaming);
  }

  showRestartPrompt() {
    if (this.restartPromptEl) return;

    const promptEl = document.createElement('div');
    promptEl.className = 'restart-prompt';
    promptEl.innerHTML = `
      <div class="restart-prompt__title">Restart ready</div>
      <div class="restart-prompt__text">Confirm to begin again.</div>
      <div class="restart-prompt__actions">
        <button type="button" class="bbs-btn bbs-btn-danger restart-confirm-btn">Restart now</button>
      </div>
    `;

    const confirmBtn = promptEl.querySelector('.restart-confirm-btn');
    if (confirmBtn) {
      confirmBtn.addEventListener('click', () => this.confirmRestart());
    }

    this.chatMessages.appendChild(promptEl);
    this.restartPromptEl = promptEl;
    this.scrollToBottom();
  }

  clearRestartPrompt() {
    if (this.restartPromptEl) {
      this.restartPromptEl.remove();
      this.restartPromptEl = null;
    }
  }

  async confirmRestart() {
    if (!this.pendingRestartConversationId) return;

    const conversationId = this.pendingRestartConversationId;

    try {
      await fetchWithAuth(`/api/conversations/${conversationId}`, {
        method: 'DELETE',
      });
      this.currentConversationId = null;
      this.chatMessages.innerHTML = '';
      this.setRestartPending(false);
      await this.loadConversations();
      this.startNewGame();
    } catch (error) {
      console.error('Failed to restart game:', error);
    }
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
          .map(item => {
            const displayName = typeof item === 'object' && item !== null ? item.name : item;
            return `<li>${this.escapeHtml(displayName)}</li>`;
          })
          .join('');
      }
    }

    // Update trophy case (show section only if treasures deposited)
    if (this.trophyCaseSectionEl && this.trophyCaseListEl) {
      const trophyCase = state.trophy_case || [];

      if (trophyCase.length === 0) {
        this.trophyCaseSectionEl.style.display = 'none';
      } else {
        this.trophyCaseSectionEl.style.display = '';
        this.trophyCountEl.textContent = trophyCase.length;
        this.trophyCaseListEl.innerHTML = trophyCase
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
