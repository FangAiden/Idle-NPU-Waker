// API Base URL
const API_BASE = '';

// State
let currentSessionId = null;
let sessions = [];
let isGenerating = false;
let modelLoaded = false;
let config = null;
let presetModels = [];
let localModels = [];
let availableDevices = [];
let supportedSettingKeys = null;
let settingGroups = null;
let pendingAttachments = [];
let maxFileBytes = 512 * 1024;
let markdownReady = false;
let mermaidReady = false;
let currentMessages = [];
let editingIndex = null;

// i18n State
let currentLang = localStorage.getItem('lang') || 'en_US';
let i18nData = {};
const LANG_LABELS = {
    'en_US': 'English',
    'zh_CN': '简体中文'
};

// DOM Elements
const sidebar = document.getElementById('sidebar');
const sidebarToggle = document.getElementById('sidebarToggle');
const sessionsList = document.getElementById('sessionsList');
const newChatBtn = document.getElementById('newChatBtn');
const chatContainer = document.getElementById('chatContainer');
const welcomeScreen = document.getElementById('welcomeScreen');
const messagesDiv = document.getElementById('messages');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const stopBtn = document.getElementById('stopBtn');
const attachBtn = document.getElementById('attachBtn');
const fileInput = document.getElementById('fileInput');
const attachmentsBar = document.getElementById('attachmentsBar');
const attachmentsList = document.getElementById('attachmentsList');
const modelStatus = document.getElementById('modelStatus');
const statusDot = document.getElementById('statusDot');
const loadModelBtn = document.getElementById('loadModelBtn');
const settingsModal = document.getElementById('settingsModal');
const openSettingsBtn = document.getElementById('openSettingsBtn');
const closeSettingsBtn = document.getElementById('closeSettingsBtn');
const renameModal = document.getElementById('renameModal');
const renameInput = document.getElementById('renameInput');
const closeRenameBtn = document.getElementById('closeRenameBtn');
const cancelRenameBtn = document.getElementById('cancelRenameBtn');
const confirmRenameBtn = document.getElementById('confirmRenameBtn');
const toast = document.getElementById('toast');

// Language Elements
const langBtn = document.getElementById('langBtn');
const langDropdown = document.getElementById('langDropdown');
const currentLangLabel = document.getElementById('currentLangLabel');

// Settings Elements
const modelSource = document.getElementById('modelSource');
const localModelGroup = document.getElementById('localModelGroup');
const presetModelGroup = document.getElementById('presetModelGroup');
const localModelSelect = document.getElementById('localModelSelect');
const presetModelSelect = document.getElementById('presetModelSelect');
const deviceSelect = document.getElementById('deviceSelect');
const refreshModelsBtn = document.getElementById('refreshModelsBtn');
const loadModelConfirmBtn = document.getElementById('loadModelConfirmBtn');
const maxPromptLenInput = document.getElementById('maxPromptLen');
const maxPromptLenValue = document.getElementById('maxPromptLenValue');
const downloadProgress = document.getElementById('downloadProgress');
const progressFill = document.getElementById('progressFill');
const downloadStatus = document.getElementById('downloadStatus');
const cancelDownloadBtn = document.getElementById('cancelDownloadBtn');

// Generation Settings
const maxTokensInput = document.getElementById('maxTokens');
const maxTokensValue = document.getElementById('maxTokensValue');
const temperatureInput = document.getElementById('temperature');
const temperatureValue = document.getElementById('temperatureValue');
const topPInput = document.getElementById('topP');
const topPValue = document.getElementById('topPValue');
const topKInput = document.getElementById('topK');
const topKValue = document.getElementById('topKValue');
const repPenaltyInput = document.getElementById('repPenalty');
const repPenaltyValue = document.getElementById('repPenaltyValue');
const doSampleInput = document.getElementById('doSample');
const historyTurnsInput = document.getElementById('historyTurns');
const historyTurnsValue = document.getElementById('historyTurnsValue');
const systemPromptInput = document.getElementById('systemPrompt');
const enableThinkingInput = document.getElementById('enableThinking');

let renameSessionId = null;

// ============== i18n Functions ==============

async function loadI18n(lang) {
    try {
        const response = await fetch(`${API_BASE}/api/i18n/${lang}`);
        if (!response.ok) throw new Error('Failed to load language');
        i18nData = await response.json();
        currentLang = lang;
        localStorage.setItem('lang', lang);
        applyI18n();
        currentLangLabel.textContent = LANG_LABELS[lang] || lang;
    } catch (error) {
        console.error('Failed to load i18n:', error);
        // Fallback to English
        if (lang !== 'en_US') {
            await loadI18n('en_US');
        }
    }
}

function t(key, ...args) {
    let text = i18nData[key] || key;
    // Replace {0}, {1}, etc. with arguments
    args.forEach((arg, i) => {
        text = text.replace(`{${i}}`, arg);
    });
    return text;
}

function applyI18n() {
    // Apply to elements with data-i18n attribute
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (i18nData[key]) {
            el.textContent = i18nData[key];
        }
    });

    // Apply to elements with data-i18n-placeholder attribute
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        if (i18nData[key]) {
            el.placeholder = i18nData[key];
        }
    });

    // Update document title
    document.title = t('app_title');
    if (attachBtn) {
        attachBtn.title = t('btn_attach', 'Attach File');
    }

    // Re-render sessions to update default names
    if (sessions.length > 0) {
        renderSessions();
    }
    renderAttachments();
}

function showToast(message, duration = 2000) {
    toast.textContent = message;
    toast.classList.remove('hidden');
    setTimeout(() => {
        toast.classList.add('hidden');
    }, duration);
}

function cacheSettingGroups() {
    settingGroups = {};
    document.querySelectorAll('[data-setting-key]').forEach(el => {
        const key = el.dataset.settingKey;
        if (key) settingGroups[key] = el;
    });
}

function applySupportedSettings(keys) {
    supportedSettingKeys = Array.isArray(keys) ? new Set(keys) : null;
    if (!settingGroups) cacheSettingGroups();
    Object.entries(settingGroups).forEach(([key, el]) => {
        const supported = !supportedSettingKeys || supportedSettingKeys.has(key);
        el.classList.toggle('hidden', !supported);
    });
}

function renderAttachments() {
    attachmentsList.innerHTML = '';
    if (pendingAttachments.length === 0) {
        attachmentsBar.classList.add('hidden');
        return;
    }
    attachmentsBar.classList.remove('hidden');
    pendingAttachments.forEach((att, index) => {
        const chip = document.createElement('div');
        chip.className = 'attachment-chip';
        chip.innerHTML = `
            <span class="attachment-name">${escapeHtml(att.name)}</span>
            <button class="attachment-remove" title="${t('btn_remove', 'Remove')}">&times;</button>
        `;
        chip.querySelector('.attachment-remove').addEventListener('click', () => {
            pendingAttachments.splice(index, 1);
            renderAttachments();
        });
        attachmentsList.appendChild(chip);
    });
}

function buildUserDisplayText(text, attachments) {
    if (!attachments || attachments.length === 0) return text;
    const label = t('label_attachments', 'Attachments');
    const names = attachments.map(att => att.name).join(', ');
    const note = names ? `[${label}: ${names}]` : `[${label}]`;
    return text ? `${text}\n\n${note}` : note;
}

async function handleFileSelection() {
    const files = Array.from(fileInput.files || []);
    fileInput.value = '';
    if (files.length === 0) return;

    for (const file of files) {
        try {
            const limit = maxFileBytes || 512 * 1024;
            const truncated = file.size > limit;
            const blob = truncated ? file.slice(0, limit) : file;
            const content = await blob.text();
            pendingAttachments.push({
                name: file.name,
                content,
                truncated
            });
            if (truncated) {
                showToast(t('msg_file_too_large', file.name));
            } else {
                showToast(t('msg_file_attached', file.name));
            }
        } catch (error) {
            showToast(t('msg_file_read_failed', file.name));
        }
    }
    renderAttachments();
}

async function updateSupportedSettingsForPath(modelPath) {
    if (!modelPath) {
        applySupportedSettings(null);
        return;
    }
    try {
        const response = await fetch(`${API_BASE}/api/models/config?path=${encodeURIComponent(modelPath)}`);
        if (!response.ok) throw new Error('Failed to load model settings');
        const data = await response.json();
        applySupportedSettings(data.supported_keys || null);
    } catch (error) {
        console.error('Failed to load model settings:', error);
        applySupportedSettings(null);
    }
}

// ============== Initialize ==============

document.addEventListener('DOMContentLoaded', init);

async function init() {
    await loadI18n(currentLang);
    await loadConfig();
    await loadSessions();
    setupEventListeners();
    setupSettingsListeners();
    setupLangSwitcher();
    cacheSettingGroups();
}

function setupLangSwitcher() {
    langBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        langDropdown.classList.toggle('hidden');
    });

    document.querySelectorAll('.lang-option').forEach(btn => {
        btn.addEventListener('click', async () => {
            const lang = btn.dataset.lang;
            await loadI18n(lang);
            langDropdown.classList.add('hidden');
        });
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!langBtn.contains(e.target) && !langDropdown.contains(e.target)) {
            langDropdown.classList.add('hidden');
        }
    });
}

async function loadConfig() {
    try {
        const response = await fetch(`${API_BASE}/api/config`);
        const data = await response.json();
        config = data.default_config;
        presetModels = data.preset_models || [];
        availableDevices = data.available_devices || ['AUTO'];
        maxFileBytes = data.max_file_bytes || maxFileBytes;

        // Populate preset models
        presetModelSelect.innerHTML = `<option value="" data-i18n="opt_select_model">${t('opt_select_model')}</option>`;
        presetModels.forEach(model => {
            const option = document.createElement('option');
            option.value = model.repo_id;
            option.textContent = model.name;
            presetModelSelect.appendChild(option);
        });

        // Populate devices
        deviceSelect.innerHTML = '';
        availableDevices.forEach(device => {
            const option = document.createElement('option');
            option.value = device;
            option.textContent = device;
            deviceSelect.appendChild(option);
        });

        // Set default values
        if (config) {
            maxTokensInput.value = config.max_new_tokens || 1024;
            maxTokensValue.textContent = maxTokensInput.value;
            temperatureInput.value = config.temperature || 0.7;
            temperatureValue.textContent = temperatureInput.value;
            topPInput.value = config.top_p || 0.9;
            topPValue.textContent = topPInput.value;
            topKInput.value = config.top_k || 40;
            topKValue.textContent = topKInput.value;
            repPenaltyInput.value = config.repetition_penalty || 1.1;
            repPenaltyValue.textContent = repPenaltyInput.value;
            doSampleInput.checked = config.do_sample !== false;
            historyTurnsInput.value = config.max_history_turns || 10;
            historyTurnsValue.textContent = historyTurnsInput.value;
            systemPromptInput.value = config.system_prompt || '';
            enableThinkingInput.checked = config.enable_thinking !== false;
        }

        await loadLocalModels();
    } catch (error) {
        console.error('Failed to load config:', error);
    }
}

async function loadLocalModels() {
    try {
        const response = await fetch(`${API_BASE}/api/models/local`);
        const data = await response.json();
        localModels = data.models || [];

        localModelSelect.innerHTML = `<option value="" data-i18n="opt_select_model">${t('opt_select_model')}</option>`;
        localModels.forEach(model => {
            const option = document.createElement('option');
            option.value = model.path;
            option.textContent = model.name;
            localModelSelect.appendChild(option);
        });

        if (modelSource.value === 'local' && localModelSelect.value) {
            await updateSupportedSettingsForPath(localModelSelect.value);
        }
    } catch (error) {
        console.error('Failed to load local models:', error);
    }
}

async function loadSessions() {
    try {
        const response = await fetch(`${API_BASE}/api/sessions`);
        const data = await response.json();
        sessions = data.sessions || [];
        currentSessionId = data.current_session_id;
        renderSessions();

        if (currentSessionId) {
            await loadMessages(currentSessionId);
        }
    } catch (error) {
        console.error('Failed to load sessions:', error);
    }
}

function renderSessions() {
    sessionsList.innerHTML = '';
    sessions.forEach(session => {
        const item = document.createElement('div');
        item.className = `session-item${session.id === currentSessionId ? ' active' : ''}`;
        const title = session.title || t('default_chat_name');
        item.innerHTML = `
            <span class="session-title">${escapeHtml(title)}</span>
            <div class="session-actions">
                <button class="session-action-btn rename-btn" title="${t('menu_rename_chat')}">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                    </svg>
                </button>
                <button class="session-action-btn delete-btn" title="${t('menu_delete_chat')}">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                </button>
            </div>
        `;

        item.querySelector('.session-title').addEventListener('click', () => selectSession(session.id));
        item.querySelector('.rename-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            openRenameModal(session.id, session.title);
        });
        item.querySelector('.delete-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            deleteSession(session.id);
        });

        sessionsList.appendChild(item);
    });
}

async function selectSession(sessionId) {
    if (sessionId === currentSessionId) return;

    try {
        await fetch(`${API_BASE}/api/sessions/${sessionId}/select`, { method: 'POST' });
        currentSessionId = sessionId;
        renderSessions();
        await loadMessages(sessionId);
        pendingAttachments = [];
        renderAttachments();
    } catch (error) {
        console.error('Failed to select session:', error);
    }
}

async function loadMessages(sessionId) {
    try {
        const response = await fetch(`${API_BASE}/api/sessions/${sessionId}/messages`);
        const data = await response.json();
        renderMessages(data.messages || []);
    } catch (error) {
        console.error('Failed to load messages:', error);
    }
}

function renderMessages(messages) {
    currentMessages = (messages || []).map(msg => ({
        ...msg,
        content: normalizeMessageContent(msg.content)
    }));
    if (messages.length === 0) {
        welcomeScreen.classList.remove('hidden');
        messagesDiv.innerHTML = '';
    } else {
        welcomeScreen.classList.add('hidden');
        messagesDiv.innerHTML = '';
        messages.forEach((msg, index) => {
            appendMessage(msg.role, msg.content, false, index);
        });
        scrollToBottom();
    }
}

function normalizeMessageContent(content) {
    if (content === null || content === undefined) return '';
    if (typeof content === 'string') return content;
    if (Array.isArray(content)) {
        return content.map((item) => {
            if (item === null || item === undefined) return '';
            if (typeof item === 'string') return item;
            if (typeof item === 'object') {
                if (typeof item.text === 'string') return item.text;
                if (typeof item.content === 'string') return item.content;
                if (typeof item.value === 'string') return item.value;
                try {
                    return JSON.stringify(item);
                } catch (err) {
                    return String(item);
                }
            }
            return String(item);
        }).join('');
    }
    if (typeof content === 'object') {
        if (typeof content.text === 'string') return content.text;
        if (typeof content.content === 'string') return content.content;
        if (typeof content.value === 'string') return content.value;
        try {
            return JSON.stringify(content);
        } catch (err) {
            return String(content);
        }
    }
    return String(content);
}

function appendMessage(role, content, scroll = true, index = null) {
    welcomeScreen.classList.add('hidden');

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    if (index !== null) {
        messageDiv.dataset.index = index;
    }

    const avatar = role === 'user' ? 'U' : 'AI';

    messageDiv.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-body">
            <div class="message-content"></div>
            <div class="message-actions"></div>
        </div>
    `;

    const contentDiv = messageDiv.querySelector('.message-content');
    contentDiv.innerHTML = formatContent(content, role);
    if (role === 'assistant') {
        renderMermaid(contentDiv);
    }

    const actionsDiv = messageDiv.querySelector('.message-actions');
    attachMessageActions(actionsDiv, role, index);

    messagesDiv.appendChild(messageDiv);

    if (scroll) {
        scrollToBottom();
    }
}

function getMessageByIndex(index) {
    if (index === null || index === undefined) return null;
    if (index < 0 || index >= currentMessages.length) return null;
    return currentMessages[index] || null;
}

function createActionButton(label, title, onClick) {
    const btn = document.createElement('button');
    btn.className = 'message-action-btn';
    btn.textContent = label;
    btn.title = title || label;
    btn.addEventListener('click', onClick);
    return btn;
}

function attachMessageActions(container, role, index) {
    container.innerHTML = '';
    const safeIndex = index === null ? -1 : index;

    if (role === 'user') {
        const editBtn = createActionButton(
            t('btn_edit', 'Edit'),
            t('btn_edit', 'Edit'),
            () => handleEditMessage(safeIndex)
        );
        const copyBtn = createActionButton(
            t('btn_copy', 'Copy'),
            t('btn_copy', 'Copy'),
            () => handleCopyMessage(safeIndex)
        );
        container.appendChild(editBtn);
        container.appendChild(copyBtn);
    } else {
        const copyBtn = createActionButton(
            t('btn_copy', 'Copy'),
            t('btn_copy', 'Copy'),
            () => handleCopyMessage(safeIndex)
        );
        const retryBtn = createActionButton(
            t('btn_retry', 'Retry'),
            t('btn_retry', 'Retry'),
            () => handleRetryMessage(safeIndex)
        );
        container.appendChild(copyBtn);
        container.appendChild(retryBtn);
    }
}

function updateMessageContent(index, content) {
    const messageDiv = messagesDiv.querySelector(`.message[data-index="${index}"]`);
    if (!messageDiv) return;
    const role = messageDiv.classList.contains('user') ? 'user' : 'assistant';
    const contentDiv = messageDiv.querySelector('.message-content');
    contentDiv.innerHTML = formatContent(content, role);
    if (role === 'assistant') {
        renderMermaid(contentDiv);
    }
}

function truncateMessages(keepCount) {
    if (keepCount < 0) keepCount = 0;
    currentMessages = currentMessages.slice(0, keepCount);
    const nodes = Array.from(messagesDiv.querySelectorAll('.message'));
    nodes.forEach(node => {
        const idx = parseInt(node.dataset.index, 10);
        if (!Number.isNaN(idx) && idx >= keepCount) {
            node.remove();
        }
    });
}

async function handleCopyMessage(index) {
    const msg = getMessageByIndex(index);
    if (!msg) return;
    const text = normalizeMessageContent(msg.content);
    try {
        await navigator.clipboard.writeText(text);
        showToast(t('msg_copied', 'Copied successfully'));
    } catch (error) {
        const temp = document.createElement('textarea');
        temp.value = text;
        document.body.appendChild(temp);
        temp.select();
        try {
            document.execCommand('copy');
            showToast(t('msg_copied', 'Copied successfully'));
        } catch (err) {
            showToast(t('dialog_error', 'Error'));
        }
        document.body.removeChild(temp);
    }
}

function handleEditMessage(index) {
    if (isGenerating) return;
    const msg = getMessageByIndex(index);
    if (!msg || msg.role !== 'user') return;
    editingIndex = index;
    pendingAttachments = [];
    renderAttachments();
    messageInput.value = normalizeMessageContent(msg.content);
    autoResize(messageInput);
    messageInput.focus();
}

async function applyEditMessage(index, newText) {
    if (!currentSessionId) return false;
    const msg = getMessageByIndex(index);
    if (!msg || msg.role !== 'user') return false;
    const attachments = msg.attachments || [];
    const content = buildUserDisplayText(newText || '', attachments);

    try {
        const response = await fetch(`${API_BASE}/api/sessions/${currentSessionId}/messages/edit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ index, content })
        });
        if (!response.ok) {
            throw new Error('Edit failed');
        }
    } catch (error) {
        showToast(t('dialog_error', 'Error'));
        return false;
    }

    currentMessages[index].content = content;
    truncateMessages(index + 1);
    updateMessageContent(index, content);
    return true;
}

async function handleRetryMessage(index) {
    if (isGenerating) return;
    const msg = getMessageByIndex(index);
    if (!msg || msg.role !== 'assistant') return;
    if (!currentSessionId) return;
    if (index <= 0) return;

    try {
        const response = await fetch(`${API_BASE}/api/sessions/${currentSessionId}/messages/retry`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ index })
        });
        if (!response.ok) {
            throw new Error('Retry failed');
        }
    } catch (error) {
        showToast(t('dialog_error', 'Error'));
        return;
    }

    truncateMessages(index);
    await regenerateAssistant();
}

async function regenerateAssistant() {
    if (isGenerating || !currentSessionId) return;

    // Create assistant placeholder
    const assistantIndex = currentMessages.length;
    currentMessages.push({ role: 'assistant', content: '' });
    appendMessage('assistant', '', true, assistantIndex);

    // Show generating state
    isGenerating = true;
    sendBtn.classList.add('hidden');
    stopBtn.classList.remove('hidden');

    const contentDiv = messagesDiv.querySelector(`.message[data-index="${assistantIndex}"] .message-content`);
    let fullResponse = '';

    try {
        const response = await fetch(`${API_BASE}/api/chat/regenerate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: currentSessionId,
                config: getGenerationConfig()
            })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        startGenStats();

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));

                        if (data.type === 'token') {
                            fullResponse += data.token;
                            incrementGenTokens();
                            if (contentDiv) {
                                contentDiv.innerHTML = formatContent(fullResponse, 'assistant');
                                renderMermaid(contentDiv);
                            }
                            currentMessages[assistantIndex].content = fullResponse;
                            scrollToBottom();
                        } else if (data.type === 'error') {
                            if (contentDiv) {
                                contentDiv.innerHTML = `<span style="color: var(--error-color)">${t('dialog_error')}: ${escapeHtml(data.message)}</span>`;
                            }
                        } else if (data.type === 'done') {
                            if (data.stats && data.stats.tokens > 0 && contentDiv) {
                                const statsDiv = document.createElement('div');
                                statsDiv.className = 'message-stats';
                                statsDiv.innerHTML = `
                                    <span class="stat-item"><strong>${data.stats.tokens}</strong> tokens</span>
                                    <span class="stat-separator">路</span>
                                    <span class="stat-item"><strong>${data.stats.speed}</strong> t/s</span>
                                    <span class="stat-separator">路</span>
                                    <span class="stat-item"><strong>${data.stats.time}</strong>s</span>
                                `;
                                contentDiv.appendChild(statsDiv);
                                updateGenStats(data.stats);
                            }
                        }
                    } catch (e) {
                        // Ignore parse errors
                    }
                }
            }
        }
    } catch (error) {
        if (contentDiv) {
            contentDiv.innerHTML = `<span style="color: var(--error-color)">${t('dialog_error')}: ${escapeHtml(error.message)}</span>`;
        }
    } finally {
        stopGenStats();
        isGenerating = false;
        sendBtn.classList.remove('hidden');
        stopBtn.classList.add('hidden');
    }
}

function setupMarkdown() {
    if (markdownReady || typeof marked === 'undefined') return;
    const renderer = new marked.Renderer();
    renderer.html = (html) => {
        const text = html && typeof html === 'object' ? html.text : html;
        return escapeHtml(text || '');
    };
    renderer.code = (code, infostring) => {
        let text = code;
        let lang = infostring;
        if (code && typeof code === 'object') {
            text = code.text;
            lang = code.lang || code.language;
        }
        const safeText = text == null ? '' : String(text);
        const safeLang = lang == null ? '' : String(lang);
        const langLabel = safeLang.trim().toLowerCase();
        const escaped = escapeHtml(safeText);
        if (langLabel === 'mermaid') {
            return `<div class="mermaid">${escaped}</div>`;
        }
        const langClass = langLabel ? `language-${langLabel}` : '';
        return `<pre><code class="${langClass}">${escaped}</code></pre>`;
    };
    renderer.link = (href, title, text) => {
        let url = href;
        let linkTitle = title;
        let labelHtml = '';
        if (href && typeof href === 'object') {
            url = href.href;
            linkTitle = href.title;
            if (href.tokens && this.parser) {
                labelHtml = this.parser.parseInline(href.tokens);
            } else {
                labelHtml = escapeHtml(href.text || '');
            }
        } else {
            labelHtml = escapeHtml(text || '');
        }
        const safeHref = escapeHtml(url || '');
        const safeTitle = linkTitle ? ` title="${escapeHtml(linkTitle)}"` : '';
        return `<a href="${safeHref}"${safeTitle} target="_blank" rel="noopener noreferrer">${labelHtml}</a>`;
    };
    marked.setOptions({
        gfm: true,
        breaks: true,
        renderer
    });
    markdownReady = true;
}

function renderMarkdown(text) {
    if (!text) return '';
    if (typeof marked !== 'undefined') {
        setupMarkdown();
        return marked.parse(text);
    }
    return escapeHtml(text).replace(/\n/g, '<br>');
}

function setupMermaid() {
    if (mermaidReady || typeof mermaid === 'undefined') return;
    mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', theme: 'dark' });
    mermaidReady = true;
}

function renderMermaid(container) {
    if (typeof mermaid === 'undefined') return;
    setupMermaid();
    const nodes = container.querySelectorAll('.mermaid');
    if (nodes.length === 0) return;
    try {
        mermaid.run({ nodes });
    } catch (error) {
        console.warn('Mermaid render failed:', error);
    }
}

function extractThink(content) {
    const openRegex = /<\s*think\s*>/i;
    const closeRegex = /<\s*\/\s*think\s*>/i;
    const openMatch = openRegex.exec(content);
    if (!openMatch) {
        return { think: '', main: content, thinkingOpen: false };
    }
    const start = openMatch.index + openMatch[0].length;
    const afterOpen = content.slice(start);
    const closeMatch = closeRegex.exec(afterOpen);
    if (closeMatch) {
        const think = afterOpen.slice(0, closeMatch.index);
        const main = content.slice(0, openMatch.index) + afterOpen.slice(closeMatch.index + closeMatch[0].length);
        return { think, main, thinkingOpen: false };
    }
    return { think: afterOpen, main: content.slice(0, openMatch.index), thinkingOpen: true };
}

function formatContent(content, role = 'assistant') {
    const normalized = normalizeMessageContent(content);
    if (!normalized) return '';
    // User messages: plain text, no markdown
    if (role === 'user') {
        return escapeHtml(normalized).replace(/\n/g, '<br>');
    }
    // Assistant messages: render markdown
    const { think, main, thinkingOpen } = extractThink(normalized);
    let html = '';
    if (think) {
        const statusKey = thinkingOpen ? 'think_status_running' : 'think_status_done';
        const summary = t(statusKey);
        const thinkHtml = renderMarkdown(think.trim());
        const openAttr = ' open';
        html += `
            <details class="think-box"${openAttr}>
                <summary>${escapeHtml(summary)}</summary>
                <div class="think-content">${thinkHtml}</div>
            </details>
        `;
    }
    if (main) {
        html += renderMarkdown(main.trim());
    }
    return html || '';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

async function createNewChat() {
    try {
        const response = await fetch(`${API_BASE}/api/sessions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
        const data = await response.json();
        sessions.unshift({ id: data.id, title: data.title });
        currentSessionId = data.id;
        renderSessions();
        renderMessages([]);
        pendingAttachments = [];
        renderAttachments();

        // Select the new session
        await fetch(`${API_BASE}/api/sessions/${data.id}/select`, { method: 'POST' });
    } catch (error) {
        console.error('Failed to create chat:', error);
    }
}

async function deleteSession(sessionId) {
    if (!confirm(t('dialog_delete_msg', sessions.find(s => s.id === sessionId)?.title || ''))) return;

    try {
        const response = await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
            method: 'DELETE'
        });
        const data = await response.json();

        sessions = sessions.filter(s => s.id !== sessionId);

        if (data.current_session_id) {
            currentSessionId = data.current_session_id;
            await loadMessages(currentSessionId);
        } else if (sessions.length > 0) {
            currentSessionId = sessions[0].id;
            await selectSession(currentSessionId);
        } else {
            currentSessionId = null;
            renderMessages([]);
        }

        renderSessions();
    } catch (error) {
        console.error('Failed to delete session:', error);
    }
}

function openRenameModal(sessionId, currentTitle) {
    renameSessionId = sessionId;
    renameInput.value = currentTitle || '';
    renameModal.classList.remove('hidden');
    renameInput.focus();
}

function closeRenameModal() {
    renameModal.classList.add('hidden');
    renameSessionId = null;
}

async function renameSession() {
    if (!renameSessionId) return;

    const newTitle = renameInput.value.trim();
    if (!newTitle) return;

    try {
        await fetch(`${API_BASE}/api/sessions/${renameSessionId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: newTitle })
        });

        const session = sessions.find(s => s.id === renameSessionId);
        if (session) {
            session.title = newTitle;
            renderSessions();
        }

        closeRenameModal();
    } catch (error) {
        console.error('Failed to rename session:', error);
    }
}

async function sendMessage() {
    const text = messageInput.value.trim();
    const hasAttachments = pendingAttachments.length > 0;
    if ((!text && !hasAttachments) || isGenerating || !modelLoaded) return;

    // Create session if needed
    if (!currentSessionId) {
        await createNewChat();
    }

    if (editingIndex !== null) {
        const targetIndex = editingIndex;
        editingIndex = null;
        messageInput.value = '';
        autoResize(messageInput);
        const updated = await applyEditMessage(targetIndex, text);
        if (updated) {
            await regenerateAssistant();
        }
        return;
    }

    const attachments = pendingAttachments.slice();
    pendingAttachments = [];
    renderAttachments();

    const displayText = buildUserDisplayText(text, attachments);

    // Add user message
    const userIndex = currentMessages.length;
    currentMessages.push({ role: 'user', content: displayText, attachments });
    appendMessage('user', displayText, true, userIndex);
    messageInput.value = '';
    autoResize(messageInput);

    // Show generating state
    isGenerating = true;
    sendBtn.classList.add('hidden');
    stopBtn.classList.remove('hidden');

    // Create assistant message placeholder
    const assistantIndex = currentMessages.length;
    currentMessages.push({ role: 'assistant', content: '' });
    appendMessage('assistant', '', true, assistantIndex);
    const contentDiv = messagesDiv.querySelector(`.message[data-index="${assistantIndex}"] .message-content`);

    let fullResponse = '';

    try {
        const response = await fetch(`${API_BASE}/api/chat/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: currentSessionId,
                text: displayText,
                config: getGenerationConfig(),
                attachments: attachments
            })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        startGenStats();

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));

                        if (data.type === 'token') {
                            fullResponse += data.token;
                            incrementGenTokens();
                            if (contentDiv) {
                                contentDiv.innerHTML = formatContent(fullResponse, 'assistant');
                                renderMermaid(contentDiv);
                            }
                            currentMessages[assistantIndex].content = fullResponse;
                            scrollToBottom();
                        } else if (data.type === 'error') {
                            contentDiv.innerHTML = `<span style="color: var(--error-color)">${t('dialog_error')}: ${escapeHtml(data.message)}</span>`;
                        } else if (data.type === 'done') {
                            // Show stats if available
                            if (data.stats && data.stats.tokens > 0) {
                                const statsDiv = document.createElement('div');
                                statsDiv.className = 'message-stats';
                                statsDiv.innerHTML = `
                                    <span class="stat-item"><strong>${data.stats.tokens}</strong> tokens</span>
                                    <span class="stat-separator">·</span>
                                    <span class="stat-item"><strong>${data.stats.speed}</strong> t/s</span>
                                    <span class="stat-separator">·</span>
                                    <span class="stat-item"><strong>${data.stats.time}</strong>s</span>
                                `;
                                contentDiv.appendChild(statsDiv);
                                // Update status bar stats
                                updateGenStats(data.stats);
                            }
                            // Update session title if it's new
                            await loadSessions();
                        }
                    } catch (e) {
                        // Ignore parse errors
                    }
                }
            }
        }
    } catch (error) {
        contentDiv.innerHTML = `<span style="color: var(--error-color)">${t('dialog_error')}: ${escapeHtml(error.message)}</span>`;
        pendingAttachments = attachments;
        renderAttachments();
    } finally {
        stopGenStats();
        isGenerating = false;
        sendBtn.classList.remove('hidden');
        stopBtn.classList.add('hidden');
    }
}

async function stopGeneration() {
    try {
        await fetch(`${API_BASE}/api/chat/stop`, { method: 'POST' });
    } catch (error) {
        console.error('Failed to stop generation:', error);
    }
}

function addConfigValue(configObj, key, value) {
    if (!supportedSettingKeys || supportedSettingKeys.has(key)) {
        configObj[key] = value;
    }
}

function getGenerationConfig() {
    const config = {};
    addConfigValue(config, 'max_new_tokens', parseInt(maxTokensInput.value));
    addConfigValue(config, 'temperature', parseFloat(temperatureInput.value));
    addConfigValue(config, 'top_p', parseFloat(topPInput.value));
    addConfigValue(config, 'top_k', parseInt(topKInput.value));
    addConfigValue(config, 'repetition_penalty', parseFloat(repPenaltyInput.value));
    addConfigValue(config, 'do_sample', doSampleInput.checked);
    addConfigValue(config, 'max_history_turns', parseInt(historyTurnsInput.value));
    addConfigValue(config, 'system_prompt', systemPromptInput.value);
    addConfigValue(config, 'enable_thinking', enableThinkingInput.checked);
    return config;
}

async function loadModel() {
    const source = modelSource.value;
    let modelPath = '';
    let modelId = '';

    if (source === 'local') {
        modelPath = localModelSelect.value;
        if (!modelPath) {
            showToast(t('opt_select_model'));
            return;
        }
        await updateSupportedSettingsForPath(modelPath);
    } else {
        modelId = presetModelSelect.value;
        if (!modelId) {
            showToast(t('opt_select_model'));
            return;
        }
        // For preset models, we need to download first
        await downloadModel(modelId);
        return;
    }

    const device = deviceSelect.value;
    const maxPromptLen = parseInt(maxPromptLenInput.value);

    loadModelConfirmBtn.disabled = true;
    loadModelConfirmBtn.textContent = t('status_loading_model', '...');
    statusDot.className = 'status-dot loading';
    modelStatus.textContent = t('status_loading_model', '...');

    try {
        const response = await fetch(`${API_BASE}/api/models/load`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                source: source,
                model_id: modelId,
                path: modelPath,
                device: device,
                max_prompt_len: maxPromptLen
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to load model');
        }

        const data = await response.json();

        modelLoaded = true;
        statusDot.className = 'status-dot ready';
        modelStatus.textContent = t('status_loaded', data.device);
        messageInput.disabled = false;
        sendBtn.disabled = false;

        showToast(t('dialog_loaded_msg', data.device));
        closeSettingsModal();
    } catch (error) {
        statusDot.className = 'status-dot';
        modelStatus.textContent = t('dialog_error');
        showToast(error.message);
    } finally {
        loadModelConfirmBtn.disabled = false;
        loadModelConfirmBtn.textContent = t('btn_load_model');
    }
}

async function downloadModel(repoId) {
    downloadProgress.classList.remove('hidden');
    loadModelConfirmBtn.disabled = true;
    progressFill.style.width = '0%';
    downloadStatus.textContent = t('dl_init_process');

    try {
        const response = await fetch(`${API_BASE}/api/download/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ repo_id: repoId })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));

                        if (data.type === 'progress') {
                            const percent = data.percent || 0;
                            progressFill.style.width = `${percent}%`;
                            downloadStatus.textContent = data.message || t('status_downloading', `${percent.toFixed(1)}%`);
                        } else if (data.type === 'done') {
                            downloadProgress.classList.add('hidden');
                            // Refresh local models and load
                            await loadLocalModels();
                            // Find and select the downloaded model
                            const modelOption = Array.from(localModelSelect.options).find(opt =>
                                opt.value.includes(repoId.split('/').pop())
                            );
                            if (modelOption) {
                                localModelSelect.value = modelOption.value;
                                modelSource.value = 'local';
                                localModelGroup.classList.remove('hidden');
                                presetModelGroup.classList.add('hidden');
                                await updateSupportedSettingsForPath(localModelSelect.value);
                                await loadModel();
                            }
                        } else if (data.type === 'error') {
                            throw new Error(data.message || 'Download failed');
                        }
                    } catch (e) {
                        if (e.message !== 'Download failed') {
                            // Ignore parse errors
                        } else {
                            throw e;
                        }
                    }
                }
            }
        }
    } catch (error) {
        downloadStatus.textContent = `${t('dialog_error')}: ${error.message}`;
    } finally {
        loadModelConfirmBtn.disabled = false;
    }
}

async function cancelDownload() {
    try {
        await fetch(`${API_BASE}/api/download/stop`, { method: 'POST' });
        downloadProgress.classList.add('hidden');
        loadModelConfirmBtn.disabled = false;
        showToast(t('dl_cancelled'));
    } catch (error) {
        console.error('Failed to cancel download:', error);
    }
}

function openSettingsModal() {
    settingsModal.classList.remove('hidden');
}

function closeSettingsModal() {
    settingsModal.classList.add('hidden');
}

function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
}

function setupEventListeners() {
    // Sidebar toggle
    sidebarToggle.addEventListener('click', () => {
        sidebar.classList.toggle('open');
    });

    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', (e) => {
        if (window.innerWidth <= 768 &&
            !sidebar.contains(e.target) &&
            !sidebarToggle.contains(e.target)) {
            sidebar.classList.remove('open');
        }
    });

    // New chat
    newChatBtn.addEventListener('click', createNewChat);

    // Send message
    sendBtn.addEventListener('click', sendMessage);
    stopBtn.addEventListener('click', stopGeneration);
    attachBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFileSelection);

    // Message input
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    messageInput.addEventListener('input', () => autoResize(messageInput));

    // Settings modal
    openSettingsBtn.addEventListener('click', openSettingsModal);
    loadModelBtn.addEventListener('click', openSettingsModal);
    closeSettingsBtn.addEventListener('click', closeSettingsModal);
    settingsModal.addEventListener('click', (e) => {
        if (e.target === settingsModal) closeSettingsModal();
    });

    // Rename modal
    closeRenameBtn.addEventListener('click', closeRenameModal);
    cancelRenameBtn.addEventListener('click', closeRenameModal);
    confirmRenameBtn.addEventListener('click', renameSession);
    renameInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') renameSession();
        if (e.key === 'Escape') closeRenameModal();
    });
    renameModal.addEventListener('click', (e) => {
        if (e.target === renameModal) closeRenameModal();
    });

    // Load model
    loadModelConfirmBtn.addEventListener('click', loadModel);
    refreshModelsBtn.addEventListener('click', loadLocalModels);
    cancelDownloadBtn.addEventListener('click', cancelDownload);

    // Model source switch
    modelSource.addEventListener('change', () => {
        if (modelSource.value === 'local') {
            localModelGroup.classList.remove('hidden');
            presetModelGroup.classList.add('hidden');
            updateSupportedSettingsForPath(localModelSelect.value);
        } else {
            localModelGroup.classList.add('hidden');
            presetModelGroup.classList.remove('hidden');
            applySupportedSettings(null);
        }
    });

    localModelSelect.addEventListener('change', () => {
        if (modelSource.value === 'local') {
            updateSupportedSettingsForPath(localModelSelect.value);
        }
    });

    // Settings tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(`tab-${btn.dataset.tab}`).classList.add('active');
        });
    });
}

function setupSettingsListeners() {
    // Slider value displays
    maxTokensInput.addEventListener('input', () => {
        maxTokensValue.textContent = maxTokensInput.value;
    });

    temperatureInput.addEventListener('input', () => {
        temperatureValue.textContent = temperatureInput.value;
    });

    topPInput.addEventListener('input', () => {
        topPValue.textContent = topPInput.value;
    });

    topKInput.addEventListener('input', () => {
        topKValue.textContent = topKInput.value;
    });

    repPenaltyInput.addEventListener('input', () => {
        repPenaltyValue.textContent = repPenaltyInput.value;
    });

    historyTurnsInput.addEventListener('input', () => {
        historyTurnsValue.textContent = historyTurnsInput.value;
    });

    maxPromptLenInput.addEventListener('input', () => {
        maxPromptLenValue.textContent = maxPromptLenInput.value;
    });
}

// ============== Gen Stats ==============

const genStatsDiv = document.getElementById('genStats');
const genTokensSpan = document.getElementById('genTokens');
const genSpeedSpan = document.getElementById('genSpeed');
const genTimeSpan = document.getElementById('genTime');

let genStartTime = 0;
let genTokenCount = 0;
let genStatsInterval = null;

function startGenStats() {
    genStartTime = Date.now();
    genTokenCount = 0;
    if (genStatsDiv) genStatsDiv.classList.remove('hidden');
    updateGenStatsDisplay();
    // Update display every 100ms for smooth time updates
    genStatsInterval = setInterval(updateGenStatsDisplay, 100);
}

function incrementGenTokens() {
    genTokenCount++;
}

function updateGenStatsDisplay() {
    if (!genStatsDiv) return;
    const elapsed = (Date.now() - genStartTime) / 1000;
    const speed = elapsed > 0 ? genTokenCount / elapsed : 0;
    genTokensSpan.textContent = genTokenCount;
    genSpeedSpan.textContent = speed.toFixed(1);
    genTimeSpan.textContent = elapsed.toFixed(1);
}

function stopGenStats() {
    if (genStatsInterval) {
        clearInterval(genStatsInterval);
        genStatsInterval = null;
    }
    updateGenStatsDisplay();
}

function updateGenStats(stats) {
    stopGenStats();
    if (!genStatsDiv || !stats || stats.tokens <= 0) {
        return;
    }
    genTokensSpan.textContent = stats.tokens;
    genSpeedSpan.textContent = stats.speed;
    genTimeSpan.textContent = stats.time;
}

// ============== NPU Monitor ==============

const npuMonitorBtn = document.getElementById('npuMonitorBtn');
const npuMonitorPanel = document.getElementById('npuMonitorPanel');
const closeNpuMonitorBtn = document.getElementById('closeNpuMonitorBtn');
const npuUtilText = document.getElementById('npuUtilText');
const npuCurrentValue = document.getElementById('npuCurrentValue');
const npuChart = document.getElementById('npuChart');
const npuStatus = document.getElementById('npuStatus');

let npuMonitorActive = false;
let npuPollInterval = null;
let npuChartCtx = null;

function initNpuMonitor() {
    npuMonitorBtn.addEventListener('click', toggleNpuMonitor);
    closeNpuMonitorBtn.addEventListener('click', () => {
        npuMonitorPanel.classList.add('hidden');
    });

    if (npuChart) {
        npuChartCtx = npuChart.getContext('2d');
    }
}

async function toggleNpuMonitor() {
    if (npuMonitorPanel.classList.contains('hidden')) {
        npuMonitorPanel.classList.remove('hidden');
        await startNpuMonitor();
    } else {
        npuMonitorPanel.classList.add('hidden');
    }
}

async function startNpuMonitor() {
    if (npuMonitorActive) return;

    try {
        const response = await fetch(`${API_BASE}/api/npu/start`, { method: 'POST' });
        const data = await response.json();

        if (data.available) {
            npuMonitorActive = true;
            npuStatus.textContent = t('npu_monitor_active') || 'Monitoring active';
            npuPollInterval = setInterval(pollNpuStatus, 1000);
            pollNpuStatus();
        } else {
            npuStatus.textContent = t('npu_monitor_unavailable') || 'NPU monitoring not available on this system';
            npuUtilText.textContent = 'N/A';
        }
    } catch (error) {
        npuStatus.textContent = `Error: ${error.message}`;
    }
}

async function pollNpuStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/npu/status`);
        const data = await response.json();

        const current = Math.round(data.current);
        npuUtilText.textContent = `${current}%`;
        npuCurrentValue.textContent = current;

        drawNpuChart(data.history);
    } catch (error) {
        console.error('NPU poll error:', error);
    }
}

function drawNpuChart(history) {
    if (!npuChartCtx || !history || history.length === 0) return;

    const canvas = npuChart;
    const ctx = npuChartCtx;
    const width = canvas.width;
    const height = canvas.height;
    const padding = 10;

    // Clear canvas
    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--bg-tertiary').trim() || '#1a1a2e';
    ctx.fillRect(0, 0, width, height);

    // Draw grid lines
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
        const y = padding + (height - 2 * padding) * i / 4;
        ctx.beginPath();
        ctx.moveTo(padding, y);
        ctx.lineTo(width - padding, y);
        ctx.stroke();
    }

    // Draw chart line
    const values = history.map(h => h.value);
    const maxPoints = 60;
    const displayValues = values.slice(-maxPoints);

    if (displayValues.length < 2) return;

    const chartWidth = width - 2 * padding;
    const chartHeight = height - 2 * padding;
    const stepX = chartWidth / (maxPoints - 1);

    ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue('--accent-color').trim() || '#10b981';
    ctx.lineWidth = 2;
    ctx.beginPath();

    const startIndex = maxPoints - displayValues.length;
    for (let i = 0; i < displayValues.length; i++) {
        const x = padding + (startIndex + i) * stepX;
        const y = padding + chartHeight - (displayValues[i] / 100) * chartHeight;

        if (i === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    }
    ctx.stroke();

    // Fill area under curve
    ctx.lineTo(padding + (startIndex + displayValues.length - 1) * stepX, height - padding);
    ctx.lineTo(padding + startIndex * stepX, height - padding);
    ctx.closePath();
    ctx.fillStyle = 'rgba(16, 185, 129, 0.2)';
    ctx.fill();
}

function stopNpuMonitor() {
    if (npuPollInterval) {
        clearInterval(npuPollInterval);
        npuPollInterval = null;
    }
    npuMonitorActive = false;
    fetch(`${API_BASE}/api/npu/stop`, { method: 'POST' }).catch(() => {});
}

// Initialize NPU monitor when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(initNpuMonitor, 100);
});
