/**
 * LLM Chat Application - Frontend
 */

class ChatApp {
    constructor() {
        this.currentConversationId = null;
        this.isStreaming = false;

        // DOM elements
        this.conversationList = document.getElementById('conversation-list');
        this.chatMessages = document.getElementById('chat-messages');
        this.chatForm = document.getElementById('chat-form');
        this.messageInput = document.getElementById('message-input');
        this.sendBtn = document.getElementById('send-btn');
        this.newChatBtn = document.getElementById('new-chat-btn');

        this.init();
    }

    async init() {
        this.bindEvents();
        await this.loadConversations();
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

        // New chat button
        this.newChatBtn.addEventListener('click', () => {
            this.startNewChat();
        });
    }

    async loadConversations() {
        try {
            const response = await fetch('/api/conversations');
            const conversations = await response.json();

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

        // Update active state in sidebar
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

        // Load messages
        try {
            const response = await fetch(`/api/conversations/${conversationId}`);
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
            await fetch(`/api/conversations/${conversationId}`, {
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

        // Remove active state from sidebar
        document.querySelectorAll('.conversation-item').forEach(item => {
            item.classList.remove('active');
        });

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

        // Remove empty state if present
        const emptyState = this.chatMessages.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }

        // Append user message
        this.appendMessage('user', message);

        // Create assistant message placeholder
        const assistantMsgEl = this.appendMessage('assistant', '');
        const contentEl = assistantMsgEl.querySelector('.message-content');
        contentEl.innerHTML = '<span class="streaming-indicator"></span>';

        // Disable input during streaming
        this.setStreaming(true);

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    conversation_id: this.currentConversationId,
                }),
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let assistantContent = '';
            let buffer = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });

                // Process SSE events
                const lines = buffer.split('\n');
                buffer = lines.pop() || ''; // Keep incomplete line in buffer

                for (const line of lines) {
                    if (line.startsWith('event:')) {
                        // Store event type for next data line
                        this.currentEventType = line.substring(6).trim();
                    } else if (line.startsWith('data:')) {
                        const data = JSON.parse(line.substring(5).trim());

                        switch (this.currentEventType) {
                            case 'start':
                                this.currentConversationId = data.conversation_id;
                                break;
                            case 'delta':
                                assistantContent += data.content;
                                contentEl.textContent = assistantContent;
                                this.scrollToBottom();
                                break;
                            case 'progress':
                                if (data.step === 'using_tool') {
                                    this.showProgress(assistantMsgEl, `Using tool: ${data.tool}`);
                                } else if (data.step === 'tool_done') {
                                    this.hideProgress(assistantMsgEl);
                                }
                                break;
                            case 'done':
                                this.hideProgress(assistantMsgEl); // Ensure clean up
                                // Refresh conversation list
                                await this.loadConversations();
                                break;
                            case 'error':
                                contentEl.textContent = `Error: ${data.error}`;
                                break;
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Failed to send message:', error);
            contentEl.textContent = `Error: ${error.message}`;
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

    showProgress(messageEl, text) {
        let progressEl = messageEl.querySelector('.streaming-progress');
        if (!progressEl) {
            progressEl = document.createElement('div');
            progressEl.className = 'streaming-progress';
            // Insert before content
            const contentEl = messageEl.querySelector('.message-content');
            messageEl.insertBefore(progressEl, contentEl);
        }
        progressEl.textContent = text;
    }

    hideProgress(messageEl) {
        const progressEl = messageEl.querySelector('.streaming-progress');
        if (progressEl) {
            progressEl.remove();
        }
    }

    setStreaming(streaming) {
        this.isStreaming = streaming;
        this.sendBtn.disabled = streaming;
        this.messageInput.disabled = streaming;
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
document.addEventListener('DOMContentLoaded', () => {
    window.chatApp = new ChatApp();
});
