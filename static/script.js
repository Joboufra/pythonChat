async function checkAuth() {
    try {
        const response = await fetch('/api/auth/me', {
            credentials: 'same-origin'
        });
        if (!response.ok) {
            window.location.href = '/login';
            return null;
        }
        return await response.json();
    } catch (err) {
        window.location.href = '/login';
        return null;
    }
}

let socket = null;
let currentUser = null;
let reconnectAttempts = 0;
const maxReconnectAttempts = 10;

const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const onlineCount = document.getElementById('online-count');

function updateStatus(connected) {
    if (connected) {
        statusDot.classList.add('connected');
        statusText.textContent = 'Conectado';
        reconnectAttempts = 0;
    } else {
        statusDot.classList.remove('connected');
        statusText.textContent = 'Desconectado';
    }
}

async function updateOnlineCount() {
    try {
        const response = await fetch('/api/chat/online-count', {
            credentials: 'same-origin'
        });
        if (response.ok) {
            const data = await response.json();
            onlineCount.textContent = data.count;
        }
    } catch (err) {
        console.error('Error fetching online count:', err);
    }
}

async function init() {
    try {
        currentUser = await checkAuth();
        if (!currentUser) return;

        document.getElementById('user-nickname').textContent = currentUser.nickname;
        document.getElementById('user-nickname').style.color = currentUser.color;

        await loadMessages();
        connectWebSocket();
    } catch (err) {
        console.error('Error initializing:', err);
        window.location.href = '/login';
    }
}

async function loadMessages() {
    try {
        const response = await fetch('/api/chat/messages', {
            credentials: 'same-origin'
        });

        if (response.ok) {
            const messages = await response.json();
            const messagesDiv = document.getElementById('messages');
            messagesDiv.innerHTML = '';

            if (messages.length === 0) {
                showEmptyState();
            } else {
                messages.forEach(msg => {
                    addMessage(msg.message, msg.timestamp, msg.nickname, msg.color, false);
                });
            }

            scrollToBottom(false);
        }
    } catch (err) {
        console.error('Error loading messages:', err);
    }
}

function showEmptyState() {
    const messagesDiv = document.getElementById('messages');
    messagesDiv.innerHTML = `
        <div class="empty-state">
            <div class="empty-state-icon">💬</div>
            <div class="empty-state-text">No hay mensajes aún. ¡Sé el primero en escribir!</div>
        </div>
    `;
}

async function getWsToken() {
    try {
        const response = await fetch('/api/auth/ws-token', {
            credentials: 'same-origin'
        });
        if (response.ok) {
            const data = await response.json();
            return data.ws_token;
        }
    } catch (err) {
        console.error('Error getting WS token:', err);
    }
    return null;
}

function connectWebSocket() {
    if (reconnectAttempts >= maxReconnectAttempts) {
        statusText.textContent = 'Error de conexión. Recarga la página.';
        return;
    }

    getWsToken().then(wsToken => {
        if (!wsToken) {
            statusText.textContent = 'Error de autenticación. Recarga la página.';
            return;
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/chat/ws?token=${wsToken}`;

        socket = new WebSocket(wsUrl);

        socket.onopen = function() {
            updateStatus(true);
            updateOnlineCount();
            console.log('WebSocket connected');
        };

        socket.onmessage = function(event) {
            const data = JSON.parse(event.data);
            if (data.error) {
                console.error('Server error:', data.error);
                return;
            }
            if (data.type === 'online_update') {
                onlineCount.textContent = data.count;
                return;
            }
            if (data.type === 'user_color_update') {
                if (currentUser.nickname === data.nickname) {
                    currentUser.color = data.color;
                    document.getElementById('user-nickname').style.color = data.color;
                }
                return;
            }
            if (data.type === 'user_nickname_update') {
                if (currentUser.nickname === data.old_nickname) {
                    currentUser.nickname = data.nickname;
                    document.getElementById('user-nickname').textContent = data.nickname;
                    document.getElementById('user-nickname').style.color = data.color;
                }
                updateMessagesNickname(data.old_nickname, data.nickname);
                return;
            }
            if (data.message) {
                addMessage(data.message, data.timestamp, data.nickname, data.color, true);
            }
        };

        socket.onclose = function() {
            updateStatus(false);
            reconnectAttempts++;
            console.log(`WebSocket disconnected. Reconnecting... (${reconnectAttempts}/${maxReconnectAttempts})`);
            setTimeout(connectWebSocket, Math.min(3000 * reconnectAttempts, 10000));
        };

        socket.onerror = function(err) {
            console.error('WebSocket error:', err);
            socket.close();
        };
    });
}

function sendMessage() {
    const input = document.getElementById('message-input');
    const message = input.value.trim();

    if (message && socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ message: message }));
        input.value = '';
        input.focus();
    }
}

document.getElementById('message-input').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        e.preventDefault();
        sendMessage();
    }
});

function addMessage(message, time, nickname, color, animate) {
    const messagesDiv = document.getElementById('messages');
    const emptyState = messagesDiv.querySelector('.empty-state');
    if (emptyState) {
        emptyState.remove();
    }

    const localTime = new Date(time).toLocaleString();
    const messageElement = document.createElement('div');
    messageElement.className = 'message';
    if (!animate) {
        messageElement.style.animation = 'none';
    }

    const isOwnMessage = nickname === currentUser.nickname;

    messageElement.innerHTML = `
        <div class="message-header">
            <span class="message-time">${localTime}</span>
            <span class="message-nickname" style="color: ${color}">${nickname}</span>
            ${isOwnMessage ? '<span class="message-own-badge">Tú</span>' : ''}
        </div>
        <div class="message-text">${escapeHtml(message)}</div>
    `;

    messagesDiv.appendChild(messageElement);
    scrollToBottom(animate);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function updateMessagesNickname(oldNickname, newNickname) {
    const messagesDiv = document.getElementById('messages');
    const messages = messagesDiv.querySelectorAll('.message');
    messages.forEach(msg => {
        const nickEl = msg.querySelector('.message-nickname');
        if (nickEl && nickEl.textContent === oldNickname) {
            nickEl.textContent = newNickname;
        }
    });
}

function scrollToBottom(smooth) {
    const messagesDiv = document.getElementById('messages');
    if (smooth) {
        messagesDiv.scrollTo({ top: messagesDiv.scrollHeight, behavior: 'smooth' });
    } else {
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
}

async function clearMessages() {
    if (!confirm('¿Borrar todo el historial de mensajes?')) return;

    try {
        const response = await fetch('/api/chat/clear', {
            method: 'POST',
            credentials: 'same-origin'
        });

        if (response.ok) {
            showEmptyState();
        } else {
            alert('Error al borrar mensajes');
        }
    } catch (err) {
        console.error('Error clearing messages:', err);
        alert('Error de conexión');
    }
}

function logout() {
    fetch('/api/auth/logout', {
        method: 'POST',
        credentials: 'same-origin'
    }).finally(() => {
        if (socket) socket.close();
        window.location.href = '/login';
    });
}

function openColorPicker() {
    const modal = document.getElementById('color-modal');
    const colorInput = document.getElementById('new-color');
    const colorPreview = document.getElementById('new-color-preview');
    const nicknameInput = document.getElementById('new-nickname');

    colorInput.value = currentUser.color;
    colorPreview.textContent = currentUser.color;
    colorPreview.style.color = currentUser.color;
    nicknameInput.value = currentUser.nickname;

    document.getElementById('profile-error').style.display = 'none';
    document.getElementById('profile-success').style.display = 'none';

    modal.style.display = 'flex';
}

function closeColorPicker() {
    document.getElementById('color-modal').style.display = 'none';
}

document.getElementById('new-color').addEventListener('input', function() {
    const preview = document.getElementById('new-color-preview');
    preview.textContent = this.value;
    preview.style.color = this.value;
});

function selectPresetColor(btn) {
    const color = btn.dataset.color;
    const colorInput = document.getElementById('new-color');
    const colorPreview = document.getElementById('new-color-preview');

    colorInput.value = color;
    colorPreview.textContent = color;
    colorPreview.style.color = color;
}

async function saveProfile() {
    const newColor = document.getElementById('new-color').value;
    const newNickname = document.getElementById('new-nickname').value.trim();
    const errorMsg = document.getElementById('profile-error');
    const successMsg = document.getElementById('profile-success');

    errorMsg.style.display = 'none';
    successMsg.style.display = 'none';

    if (!newNickname) {
        errorMsg.textContent = 'El nickname no puede estar vacío';
        errorMsg.style.display = 'block';
        return;
    }

    try {
        const nicknameResponse = await fetch('/api/auth/me/nickname', {
            method: 'PATCH',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ nickname: newNickname })
        });

        if (!nicknameResponse.ok) {
            const error = await nicknameResponse.json();
            errorMsg.textContent = error.detail || 'Error al actualizar el nickname';
            errorMsg.style.display = 'block';
            return;
        }

        const colorResponse = await fetch('/api/auth/me/color', {
            method: 'PATCH',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ color: newColor })
        });

        if (!colorResponse.ok) {
            const error = await colorResponse.json();
            errorMsg.textContent = error.detail || 'Error al actualizar el color';
            errorMsg.style.display = 'block';
            return;
        }

        const data = await colorResponse.json();
        currentUser.color = data.color;
        currentUser.nickname = newNickname;
        document.getElementById('user-nickname').style.color = data.color;
        document.getElementById('user-nickname').textContent = newNickname;
        successMsg.textContent = 'Perfil actualizado';
        successMsg.style.display = 'block';
        setTimeout(() => {
            closeColorPicker();
        }, 1500);
    } catch (err) {
        errorMsg.textContent = 'Error de conexión. Intenta de nuevo.';
        errorMsg.style.display = 'block';
    }
}

function toggleEmojiPicker() {
    const picker = document.getElementById('emoji-picker');
    if (picker.style.display === 'none') {
        picker.style.display = 'block';
    } else {
        picker.style.display = 'none';
    }
}

function insertEmoji(emoji) {
    const input = document.getElementById('message-input');
    const start = input.selectionStart;
    const end = input.selectionEnd;
    const text = input.value;
    input.value = text.substring(0, start) + emoji + text.substring(end);
    input.selectionStart = input.selectionEnd = start + emoji.length;
    input.focus();
}

document.addEventListener('click', function(e) {
    const picker = document.getElementById('emoji-picker');
    if (picker.style.display === 'block' && !picker.contains(e.target) && !e.target.closest('.input-emoji-btn')) {
        picker.style.display = 'none';
    }
});

window.onclick = function(event) {
    const modal = document.getElementById('color-modal');
    if (event.target === modal) {
        closeColorPicker();
    }
};

window.onload = init;
