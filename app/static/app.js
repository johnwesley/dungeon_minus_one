/**
 * LLM Chat Application - Frontend (legacy static)
 */

class ChatApp {
    constructor() {
        this.currentConversationId = null;
        this.isStreaming = false;
        this.csrfToken = sessionStorage.getItem('csrf_token');

        // DOM elements
        this.conversationList = document.getElementById('conversation-list');
        this.chatMessages = document.getElementById('chat-messages');
        this.chatForm = document.getElementById('chat-form');
        this.messageInput = document.getElementById('message-input');
        this.sendBtn = document.getElementById('send-btn');
        this.newChatBtn = document.getElementById('new-chat-btn');
        this.logoutBtn = this.createLogoutButton();

        this.init();
    }

    async ensureSession() {
        try {
            const response = await fetch('/api/auth/session', { credentials: 'same-origin', cache: 'no-store' });
            if (!response.ok) {
                window.location.href = '/static/login.html';
                return false;
            }
            const data = await response.json();
            if (!data.authenticated) {
                window.location.href = '/static/login.html';
                return false;
            }
            if (data.csrf_token) {
                sessionStorage.setItem('csrf_token', data.csrf_token);
                this.csrfToken = data.csrf_token;
            }
            return true;
        } catch (error) {
            window.location.href = '/static/login.html';
            return false;
        }
    }

    createLogoutButton() {
        const btn = document.createElement('button');
        btn.textContent = 'Logout';
        btn.className = 'new-chat-btn';
        btn.style.marginTop = 'auto';
        btn.style.backgroundColor = '#4a4a4a';
        btn.addEventListener('click', async () => {
            try {
                await this.fetchWithAuth('/api/auth/logout', { method: 'POST' });
            } catch (error) {
                // ignore
            }
            sessionStorage.removeItem('csrf_token');
            window.location.href = '/static/login.html';
        });

        const sidebar = document.querySelector('.sidebar');
        if (sidebar) {
            sidebar.appendChild(btn);
        }
        return btn;
    }

    async init() {
        const ok = await this.ensureSession();
        if (!ok) return;
        this.bindEvents();
        await this.loadConversations();
    }

    bindEvents() {
        this.chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage();
        });

        this.messageInput.addEventListener('input', () => {
            this.messageInput.style.height = 'auto';
            this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 200) + 'px';
        });

        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        this.newChatBtn.addEventListener('click', () => {
            this.startNewChat();
        });
    }

    async fetchWithAuth(url, options = {}) {
        const headers = {
            ...options.headers,
        };

        if (options.method && options.method.toUpperCase() !== 'GET') {
            this.csrfToken = sessionStorage.getItem('csrf_token');
            if (this.csrfToken) {
                headers['X-CSRF-Token'] = this.csrfToken;
            }
        }

        const response = await fetch(url, { ...options, headers, credentials: 'same-origin' });

        if (response.status === 401) {
            sessionStorage.removeItem('csrf_token');
            window.location.href = '/static/login.html';
            return null;
        }

        return response;
    }

    async loadConversations() {
        try {
            const response = await this.fetchWithAuth('/api/conversations');
            if (!response) return;

            const conversations = await response.json();
            this.conversations = conversations;

            this.conversationList.innerHTML = '';

            if (conversations.length === 0) {
                this.conversationList.innerHTML = '<p class="empty-state" style="padding: 1rem; color: var(--text-secondary);">No conversations yet</p>';
                return;
            }

            conversations.forEach(conv => {
                const item = this.createConversationItem(conv);
                this.conversationList.appendChild(item);
            });
        } catch (error) {
            console.error('Failed to load conversations:', error);
        }
    }

    createConversationItem(conversation) {
        const item = document.createElement('div');
        item.className = 'conversation-item';
        if (this.currentConversationId === conversation.id) {
            item.classList.add('active');
        }

        item.innerHTML = `
            <span class="conversation-title">${this.escapeHtml(conversation.title || 'Untitled')}</span>
            <button class="conversation-delete" title="Delete">&times;</button>
        `;

        item.addEventListener('click', (e) => {
            if (!e.target.classList.contains('conversation-delete')) {
                this.selectConversation(conversation.id);
            }
        });

        const deleteBtn = item.querySelector('.conversation-delete');
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.deleteConversation(conversation.id);
        });

        return item;
    }

    async selectConversation(conversationId) {
        this.currentConversationId = conversationId;

        document.querySelectorAll('.conversation-item').forEach(item => {
            item.classList.remove('active');
        });
        const activeItem = [...document.querySelectorAll('.conversation-item')].find(
            item => item.querySelector('.conversation-title').textContent ===
                   (this.conversations?.find(c => c.id === conversationId)?.title || 'Untitled')
        );
        if (activeItem) {
            activeItem.classList.add('active');
        }

        try {
            const response = await this.fetchWithAuth(`/api/conversations/${conversationId}`);
            if (!response) return;
            const conversation = await response.json();

            this.chatMessages.innerHTML = '';

            conversation.messages.forEach(msg => {
                this.appendMessage(msg.role, msg.content);
            });

            this.scrollToBottom();
        } catch (error) {
            console.error('Failed to load conversation:', error);
        }
    }

    async deleteConversation(conversationId) {
        if (!confirm('Delete this conversation?')) return;

        try {
            await this.fetchWithAuth(`/api/conversations/${conversationId}`, {
                method: 'DELETE'
            });

            if (this.currentConversationId === conversationId) {
                this.startNewChat();
            }

            await this.loadConversations();
        } catch (error) {
            console.error('Failed to delete conversation:', error);
        }
    }

    startNewChat() {
        this.currentConversationId = null;
        this.chatMessages.innerHTML = '';
        this.sendMessage('Wake up');
    }

    async sendMessage(messageText = null) {
        const message = messageText || this.messageInput.value.trim();
        if (!message || this.isStreaming) return;

        if (!messageText) {
            this.messageInput.value = '';
            this.messageInput.style.height = 'auto';
        }

        this.appendMessage('user', message);

        this.setStreaming(true);

        try {
            const response = await this.fetchWithAuth('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message, conversation_id: this.currentConversationId }),
            });

            if (!response) return;

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let currentEventType = '';
            let assistantContent = '';
            const assistantMsgEl = this.appendMessage('assistant', '');
            const contentEl = assistantMsgEl.querySelector('.message-content');

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('event:')) {
                        currentEventType = line.substring(6).trim();
                    } else if (line.startsWith('data:')) {
                        const data = JSON.parse(line.substring(5).trim());
                        if (currentEventType === 'delta') {
                            assistantContent += data.content;
                            contentEl.textContent = assistantContent;
                            this.scrollToBottom();
                        } else if (currentEventType === 'start') {
                            this.currentConversationId = data.conversation_id;
                        } else if (currentEventType === 'done') {
                            await this.loadConversations();
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Failed to send message:', error);
        } finally {
            this.setStreaming(false);
        }
    }

    appendMessage(role, content) {
        const messageEl = document.createElement('div');
        messageEl.className = `message ${role}`;
        messageEl.innerHTML = `
            <div class="message-role">${role}</div>
            <div class="message-content">${this.escapeHtml(content)}</div>
        `;
        this.chatMessages.appendChild(messageEl);
        this.scrollToBottom();
        return messageEl;
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
}

// Initialize app
window.addEventListener('DOMContentLoaded', () => {
    new ChatApp();
});
