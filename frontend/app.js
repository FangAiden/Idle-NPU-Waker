// API Base URL
const API_BASE = '';

// State
let currentSessionId = null;
let sessions = [];
let isGenerating = false;
let modelLoaded = false;
let config = null;
let presetModels = [];
let downloadCatalogModels = [];
let localModels = [];
let availableDevices = [];
let supportedSettingKeys = null;
let settingGroups = null;
let pendingAttachments = [];
let maxFileBytes = 512 * 1024;
let markdownReady = false;
let mermaidReady = false;
let codeHighlightReady = false;
let currentMessages = [];
let editingIndex = null;
let downloadRunning = false;
let downloadAbortController = null;
let loadedModelConfig = { path: '', device: 'AUTO', maxPromptLen: 16384 };
let modelReloadRequired = false;
const LAST_MODEL_KEY = 'last_model_config';
const USER_CONFIG_KEY = 'user_config';
const MAX_PROMPT_LEN_KEY = 'max_prompt_len_pref';
const UI_TRANSITION_MS = 180;
const NPU_POLL_INTERVAL_KEY = 'npu_poll_interval_ms';
const DEFAULT_NPU_POLL_MS = 1000;
const AUTO_LOAD_MODEL_KEY = 'auto_load_model';
const DEFAULT_AUTO_LOAD_MODEL = false;
const CLOSE_BEHAVIOR_KEY = 'close_behavior';
const DEFAULT_CLOSE_BEHAVIOR = 'ask';
let systemStatusInterval = null;
let autoScrollEnabled = true;
const SCROLL_BOTTOM_THRESHOLD = 80;
let codeBlockObserver = null;

// i18n State
let currentLang = localStorage.getItem('lang') || 'en_US';
let i18nData = {};
const LANG_LABELS = {
    'en_US': 'English',
    'zh_CN': '\u7b80\u4f53\u4e2d\u6587'
};

// DOM Elements
const sidebar = document.getElementById('sidebar');
const sidebarToggle = document.getElementById('sidebarToggle');
const sidebarCollapseBtn = document.getElementById('sidebarCollapseBtn');
const sessionsList = document.getElementById('sessionsList');
const newChatBtn = document.getElementById('newChatBtn');
const tempChatBtn = document.getElementById('tempChatBtn');
const chatContainer = document.getElementById('chatContainer');
const welcomeScreen = document.getElementById('welcomeScreen');
const messagesDiv = document.getElementById('messages');
const scrollBottomBtn = document.getElementById('scrollBottomBtn');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const stopBtn = document.getElementById('stopBtn');
const attachBtn = document.getElementById('attachBtn');
const fileInput = document.getElementById('fileInput');
const attachmentsBar = document.getElementById('attachmentsBar');
const attachmentsList = document.getElementById('attachmentsList');
const modelStatus = document.getElementById('modelStatus');
const statusDot = document.getElementById('statusDot');
const modelSwitcher = document.getElementById('modelSwitcher');
const modelSwitcherBtn = document.getElementById('modelSwitcherBtn');
const modelSwitcherMenu = document.getElementById('modelSwitcherMenu');
const modelSwitcherList = document.getElementById('modelSwitcherList');
const modelSwitcherName = document.getElementById('modelSwitcherName');
const modelSwitcherManage = document.getElementById('modelSwitcherManage');
const memoryStatus = document.getElementById('memoryStatus');
const downloadStatusBadge = document.getElementById('downloadStatusBadge');
const performancePanel = document.getElementById('performancePanel');
const performancePanelHandle = document.getElementById('performancePanelHandle');
const performancePanelToggleBtn = document.getElementById('performancePanelToggleBtn');
const performancePanelCloseBtn = document.getElementById('performancePanelCloseBtn');
const settingsModal = document.getElementById('settingsModal');
const openSettingsBtn = document.getElementById('openSettingsBtn');
const closeSettingsBtn = document.getElementById('closeSettingsBtn');
const renameModal = document.getElementById('renameModal');
const renameInput = document.getElementById('renameInput');
const closeRenameBtn = document.getElementById('closeRenameBtn');
const cancelRenameBtn = document.getElementById('cancelRenameBtn');
const confirmRenameBtn = document.getElementById('confirmRenameBtn');
const toast = document.getElementById('toast');
const appContainer = document.getElementById('appContainer');
const welcomeOverlay = document.getElementById('welcomeOverlay');
const welcomeLoadBtn = document.getElementById('welcomeLoadBtn');
const welcomeDownloadBtn = document.getElementById('welcomeDownloadBtn');
const welcomeLoading = document.getElementById('welcomeLoading');
const welcomeLoadingText = document.getElementById('welcomeLoadingText');
const welcomeAppMemory = document.getElementById('welcomeAppMemory');
const welcomeLocalModelSelect = document.getElementById('welcomeLocalModelSelect');
const welcomeDeviceSelect = document.getElementById('welcomeDeviceSelect');
const welcomeMaxPromptLenInput = document.getElementById('welcomeMaxPromptLen');
const welcomeMaxPromptLenValue = document.getElementById('welcomeMaxPromptLenValue');
const welcomeRefreshModelsBtn = document.getElementById('welcomeRefreshModelsBtn');
const openDownloadBtn = document.getElementById('openDownloadBtn');
const downloadModal = document.getElementById('downloadModal');
const closeDownloadBtn = document.getElementById('closeDownloadBtn');
const downloadModelInput = document.getElementById('downloadModelInput');
const downloadModelList = document.getElementById('downloadModelList');
const downloadModelBtn = document.getElementById('downloadModelBtn');
const downloadCards = document.getElementById('downloadCards');
const downloadCardsEmpty = document.getElementById('downloadCardsEmpty');
const downloadSearchInput = document.getElementById('downloadSearchInput');
const downloadCollectionLink = document.getElementById('downloadCollectionLink');

const closeBehaviorSelect = document.getElementById('closeBehaviorSelect');
const closeConfirmModal = document.getElementById('closeConfirmModal');
const closeConfirmCloseBtn = document.getElementById('closeConfirmCloseBtn');
const closeToTrayBtn = document.getElementById('closeToTrayBtn');
const closeExitBtn = document.getElementById('closeExitBtn');

// Language Elements
const langBtn = document.getElementById('langBtn');
const langDropdown = document.getElementById('langDropdown');
const currentLangLabel = document.getElementById('currentLangLabel');

// Settings Elements
const localModelSelect = document.getElementById('localModelSelect');
const deviceSelect = document.getElementById('deviceSelect');
const refreshModelsBtn = document.getElementById('refreshModelsBtn');
const loadModelConfirmBtn = document.getElementById('loadModelConfirmBtn');
const maxPromptLenInput = document.getElementById('maxPromptLen');
const maxPromptLenValue = document.getElementById('maxPromptLenValue');
const npuPollIntervalInput = document.getElementById('npuPollInterval');
const npuPollIntervalValue = document.getElementById('npuPollIntervalValue');
const autoLoadModelToggle = document.getElementById('autoLoadModelToggle');
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

function getTauriInvoke() {
    const tauri = window.__TAURI__;
    if (tauri && tauri.core && typeof tauri.core.invoke === 'function') {
        return tauri.core.invoke.bind(tauri.core);
    }
    if (tauri && typeof tauri.invoke === 'function') {
        return tauri.invoke.bind(tauri);
    }
    const internals = window.__TAURI_INTERNALS__;
    if (internals && typeof internals.invoke === 'function') {
        return internals.invoke.bind(internals);
    }
    return null;
}

let trayUpdateAttempts = 0;

function updateTrayMenuLabels() {
    const invoke = getTauriInvoke();
    if (!invoke) {
        if (trayUpdateAttempts < 5) {
            trayUpdateAttempts += 1;
            setTimeout(updateTrayMenuLabels, 500);
        }
        return;
    }
    invoke('update_tray_labels', {
        show_label: t('tray_show'),
        quit_label: t('tray_quit')
    }).then(() => {
        trayUpdateAttempts = 0;
    }).catch((err) => {
        console.warn('Failed to update tray menu:', err);
        if (trayUpdateAttempts < 5) {
            trayUpdateAttempts += 1;
            setTimeout(updateTrayMenuLabels, 500);
        }
    });
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
    updateWelcomeLoadingText();

    // Re-render sessions to update default names
    if (sessions.length > 0) {
        renderSessions();
    }
    renderAttachments();
    setModelReloadRequired(modelReloadRequired);
    updateModelSwitcherLabel();
    updateSystemStatus();
    renderDownloadCards(downloadSearchInput ? downloadSearchInput.value : '');
    updateTrayMenuLabels();
}

function showToast(message, duration = 2000) {
    toast.textContent = message;
    toast.classList.remove('hidden');
    setTimeout(() => {
        toast.classList.add('hidden');
    }, duration);
}

function clearUiTimer(el) {
    if (!el || !el.dataset.uiTimer) return;
    clearTimeout(Number(el.dataset.uiTimer));
    delete el.dataset.uiTimer;
}

function showAnimated(el) {
    if (!el) return;
    clearUiTimer(el);
    el.classList.remove('hidden');
    requestAnimationFrame(() => {
        el.classList.add('ui-open');
    });
}

function hideAnimated(el) {
    if (!el) return;
    clearUiTimer(el);
    if (el.classList.contains('hidden')) return;
    el.classList.remove('ui-open');
    const timer = window.setTimeout(() => {
        el.classList.add('hidden');
        clearUiTimer(el);
    }, UI_TRANSITION_MS);
    el.dataset.uiTimer = String(timer);
}

function loadLastModelConfig() {
    const raw = localStorage.getItem(LAST_MODEL_KEY);
    if (!raw) return null;
    try {
        const data = JSON.parse(raw);
        if (!data || !data.path) return null;
        return data;
    } catch (error) {
        return null;
    }
}

function saveLastModelConfig(path, device, maxPromptLen) {
    if (!path) return;
    const payload = {
        path,
        device: device || 'AUTO',
        max_prompt_len: maxPromptLen || 16384,
        ts: Date.now()
    };
    localStorage.setItem(LAST_MODEL_KEY, JSON.stringify(payload));
}

function getPreferredMaxPromptLen() {
    const raw = localStorage.getItem(MAX_PROMPT_LEN_KEY);
    const value = parseInt(raw, 10);
    return Number.isFinite(value) ? value : null;
}

function normalizeMaxPromptLen(value) {
    const min = welcomeMaxPromptLenInput
        ? parseInt(welcomeMaxPromptLenInput.min, 10)
        : (maxPromptLenInput ? parseInt(maxPromptLenInput.min, 10) : 1024);
    const max = welcomeMaxPromptLenInput
        ? parseInt(welcomeMaxPromptLenInput.max, 10)
        : (maxPromptLenInput ? parseInt(maxPromptLenInput.max, 10) : 32768);
    const parsed = parseInt(value, 10);
    if (!Number.isFinite(parsed)) return null;
    return clamp(parsed, Number.isFinite(min) ? min : 1024, Number.isFinite(max) ? max : 32768);
}

function applyMaxPromptLen(value, persist = false) {
    const normalized = normalizeMaxPromptLen(value);
    if (normalized === null) return;
    if (maxPromptLenInput && maxPromptLenValue) {
        maxPromptLenInput.value = normalized;
        maxPromptLenValue.textContent = normalized;
    }
    if (welcomeMaxPromptLenInput && welcomeMaxPromptLenValue) {
        welcomeMaxPromptLenInput.value = normalized;
        welcomeMaxPromptLenValue.textContent = normalized;
    }
    if (persist) {
        localStorage.setItem(MAX_PROMPT_LEN_KEY, String(normalized));
    }
    updateReloadRequirement();
}

function setModelReloadRequired(required) {
    modelReloadRequired = required;
    if (!modelLoaded) return;
    if (required) {
        statusDot.className = 'status-dot warning';
        modelStatus.textContent = t('status_reload_required', 'Reload required');
        if (loadModelConfirmBtn) {
            loadModelConfirmBtn.textContent = t('btn_reload_model', 'Reload Model');
        }
    } else {
        statusDot.className = 'status-dot ready';
        modelStatus.textContent = t('status_loaded', loadedModelConfig.device || 'AUTO');
        if (loadModelConfirmBtn) {
            loadModelConfirmBtn.textContent = t('btn_load_model', 'Load Model');
        }
    }
}

function updateReloadRequirement() {
    if (!modelLoaded) {
        setModelReloadRequired(false);
        return;
    }
    const path = localModelSelect ? localModelSelect.value : '';
    const device = deviceSelect ? deviceSelect.value : 'AUTO';
    const maxPromptLen = maxPromptLenInput ? parseInt(maxPromptLenInput.value) : loadedModelConfig.maxPromptLen;
    const needsReload = !!path && (
        path !== (loadedModelConfig.path || '') ||
        device !== (loadedModelConfig.device || 'AUTO') ||
        maxPromptLen !== (loadedModelConfig.maxPromptLen || 0)
    );
    setModelReloadRequired(needsReload);
}

function formatBytes(bytes) {
    if (!bytes || bytes <= 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let value = bytes;
    let index = 0;
    while (value >= 1024 && index < units.length - 1) {
        value /= 1024;
        index += 1;
    }
    return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[index]}`;
}

function updateModelMemoryStatus(model, appMem) {
    if (!memoryStatus) return;
    const modelLoaded = !!(model && model.loaded);
    const modelLoading = !!(model && model.loading);
    const appRss = appMem && typeof appMem.rss === 'number' ? appMem.rss : 0;
    const appPrivate = appMem && typeof appMem.private === 'number' ? appMem.private : 0;
    const label = modelLoaded
        ? t('status_model_memory', 'Model Mem')
        : t('status_app_memory', 'App Mem');

    if (!modelLoaded && !modelLoading && !appRss) {
        memoryStatus.textContent = `${label} --`;
        memoryStatus.title = '';
        memoryStatus.classList.remove('active');
        return;
    }

    if (modelLoaded) {
        const rss = model.memory && typeof model.memory.rss === 'number' ? model.memory.rss : 0;
        const privateBytes = model.memory && typeof model.memory.private === 'number' ? model.memory.private : 0;
        memoryStatus.textContent = `${label} ${formatBytes(rss)}`;
        const titleParts = [];
        if (privateBytes > 0 && privateBytes !== rss) {
            titleParts.push(`${t('status_memory_private', 'Private')} ${formatBytes(privateBytes)}`);
        }
        memoryStatus.title = titleParts.join(' | ');
        memoryStatus.classList.add('active');
        return;
    }

    memoryStatus.textContent = `${label} ${formatBytes(appRss)}`;
    const titleParts = [];
    if (appPrivate > 0 && appPrivate !== appRss) {
        titleParts.push(`${t('status_memory_private', 'Private')} ${formatBytes(appPrivate)}`);
    }
    memoryStatus.title = titleParts.join(' | ');
    memoryStatus.classList.add('active');
}

function updateWelcomeAppMemory(appMem, model) {
    if (!welcomeAppMemory) return;
    if (!model || !model.loading) {
        welcomeAppMemory.textContent = '';
        return;
    }
    const label = t('status_app_memory', 'App Mem');
    const rss = appMem && typeof appMem.rss === 'number' ? appMem.rss : 0;
    welcomeAppMemory.textContent = `${label} ${rss ? formatBytes(rss) : '--'}`;
}

function updateDownloadStatusBadge(status) {
    if (!downloadStatusBadge) return;
    const label = t('status_download', 'Download');
    if (!status || !status.running) {
        downloadStatusBadge.textContent = `${label}: ${t('status_download_idle', 'Idle')}`;
        downloadStatusBadge.title = '';
        downloadStatusBadge.classList.remove('active');
        return;
    }
    const percent = typeof status.percent === 'number' ? Math.round(status.percent) : 0;
    const suffix = percent > 0 ? `${percent}%` : t('status_download_running', 'Running');
    downloadStatusBadge.textContent = `${label} ${suffix}`;
    downloadStatusBadge.title = status.file || status.message || status.repo_id || '';
    downloadStatusBadge.classList.add('active');
}

function updateModelLoadStatus(model) {
    if (!model || !model.loading) return;
    if (modelReloadRequired) return;
    const rawStage = model.load_stage || '';
    let stage = rawStage;
    if (stage.startsWith('load_stage_')) {
        stage = stage.slice('load_stage_'.length);
    }
    stage = stage === 'starting' ? 'start' : stage;
    const stageKey = stage ? `load_stage_${stage}` : '';
    const stageLabel = stageKey ? t(stageKey, '') : '';
    const resolvedStage = stageLabel && stageLabel !== stageKey ? stageLabel : '';
    let message = '';
    const rawMessage = model.load_message || '';
    if (rawMessage.startsWith('load_stage_')) {
        const messageLabel = t(rawMessage, '');
        message = messageLabel && messageLabel !== rawMessage ? messageLabel : rawMessage;
    } else {
        message = rawMessage;
    }
    message = resolvedStage || message || stage || '';
    const display = message || t('status_loading_model', '...');
    statusDot.className = 'status-dot loading';
    modelStatus.textContent = t('status_loading_model', display);
    if (welcomeLoadingText) {
        welcomeLoadingText.textContent = t('status_loading_model', display);
    }
}

async function updateSystemStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/status`);
        if (!response.ok) return;
        const data = await response.json();
        updateModelLoadStatus(data.model);
        updateModelMemoryStatus(data.model, data.app);
        updateWelcomeAppMemory(data.app, data.model);
        updateDownloadStatusBadge(data.download);
    } catch (error) {
        // Ignore polling errors
    }
}

function initSystemStatus() {
    updateSystemStatus();
    if (systemStatusInterval) {
        clearInterval(systemStatusInterval);
    }
    systemStatusInterval = setInterval(updateSystemStatus, 2000);
}

function getModelDisplayName(path) {
    if (!path) return t('model_switcher_select', 'Select model');
    const match = localModels.find(model => model.path === path);
    if (match && match.name) return match.name;
    const parts = path.split(/[/\\\\]/);
    return parts[parts.length - 1] || path;
}

function updateModelSwitcherLabel() {
    if (!modelSwitcherName) return;
    if (modelLoaded && loadedModelConfig.path) {
        modelSwitcherName.textContent = getModelDisplayName(loadedModelConfig.path);
    } else {
        modelSwitcherName.textContent = t('model_switcher_select', 'Select model');
    }
}

function renderModelSwitcherList() {
    if (!modelSwitcherList) return;
    modelSwitcherList.innerHTML = '';
    if (!localModels || localModels.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'model-switcher-empty';
        empty.textContent = t('model_switcher_empty', 'No local models');
        modelSwitcherList.appendChild(empty);
        return;
    }

    localModels.forEach(model => {
        const item = document.createElement('button');
        item.type = 'button';
        item.className = 'model-switcher-item';
        item.textContent = model.name;
        item.dataset.path = model.path;
        if (loadedModelConfig.path && model.path === loadedModelConfig.path) {
            item.classList.add('active');
        }
        item.addEventListener('click', async () => {
            closeModelSwitcher();
            if (model.path === loadedModelConfig.path && modelLoaded && !modelReloadRequired) {
                return;
            }
            await loadModelFromDropdown(model.path);
        });
        modelSwitcherList.appendChild(item);
    });
}

function closeModelSwitcher() {
    if (modelSwitcherMenu) {
        hideAnimated(modelSwitcherMenu);
    }
    if (modelSwitcherBtn) {
        modelSwitcherBtn.setAttribute('aria-expanded', 'false');
    }
}

function toggleModelSwitcher() {
    if (!modelSwitcherMenu || !modelSwitcherBtn) return;
    const isOpen = modelSwitcherMenu.classList.contains('ui-open');
    if (isOpen) {
        closeModelSwitcher();
    } else {
        showAnimated(modelSwitcherMenu);
        modelSwitcherBtn.setAttribute('aria-expanded', 'true');
    }
}

async function loadModelFromDropdown(modelPath) {
    if (!modelPath) return;
    localModelSelect.value = modelPath;
    await updateSupportedSettingsForPath(modelPath);

    const device = deviceSelect ? deviceSelect.value : 'AUTO';
    const maxPromptLen = maxPromptLenInput ? parseInt(maxPromptLenInput.value) : 16384;

    statusDot.className = 'status-dot loading';
    modelStatus.textContent = t('status_loading_model', device);

    try {
        const response = await fetch(`${API_BASE}/api/models/load`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                source: 'local',
                model_id: '',
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
        applyLoadedModel(modelPath, data.device, maxPromptLen);
        showToast(t('dialog_loaded_msg', data.device));
    } catch (error) {
        statusDot.className = 'status-dot';
        modelStatus.textContent = t('dialog_error');
        showToast(error.message);
    }
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

function loadUserConfig() {
    try {
        const raw = localStorage.getItem(USER_CONFIG_KEY);
        if (!raw) return null;
        const data = JSON.parse(raw);
        if (!data || typeof data !== 'object') return null;
        return data;
    } catch (error) {
        return null;
    }
}

function saveUserConfig(configObj) {
    if (!configObj || typeof configObj !== 'object') return;
    localStorage.setItem(USER_CONFIG_KEY, JSON.stringify(configObj));
}

function normalizeNumber(value) {
    if (typeof value === 'number' && Number.isFinite(value)) return value;
    const parsed = parseFloat(value);
    return Number.isFinite(parsed) ? parsed : null;
}

function normalizeInt(value) {
    if (typeof value === 'number' && Number.isFinite(value)) return Math.trunc(value);
    const parsed = parseInt(value, 10);
    return Number.isFinite(parsed) ? parsed : null;
}

function applyConfigToInputs(cfg) {
    if (!cfg) return;
    const maxTokens = normalizeInt(cfg.max_new_tokens);
    if (maxTokens !== null && maxTokensInput) {
        maxTokensInput.value = maxTokens;
        maxTokensValue.textContent = maxTokens;
    }
    const temperature = normalizeNumber(cfg.temperature);
    if (temperature !== null && temperatureInput) {
        temperatureInput.value = temperature;
        temperatureValue.textContent = temperature;
    }
    const topP = normalizeNumber(cfg.top_p);
    if (topP !== null && topPInput) {
        topPInput.value = topP;
        topPValue.textContent = topP;
    }
    const topK = normalizeInt(cfg.top_k);
    if (topK !== null && topKInput) {
        topKInput.value = topK;
        topKValue.textContent = topK;
    }
    const repPenalty = normalizeNumber(cfg.repetition_penalty);
    if (repPenalty !== null && repPenaltyInput) {
        repPenaltyInput.value = repPenalty;
        repPenaltyValue.textContent = repPenalty;
    }
    if (typeof cfg.do_sample === 'boolean' && doSampleInput) {
        doSampleInput.checked = cfg.do_sample;
    }
    const historyTurns = normalizeInt(cfg.max_history_turns);
    if (historyTurns !== null && historyTurnsInput) {
        historyTurnsInput.value = historyTurns;
        historyTurnsValue.textContent = historyTurns;
    }
    if (typeof cfg.system_prompt === 'string' && systemPromptInput) {
        systemPromptInput.value = cfg.system_prompt;
    }
    if (typeof cfg.enable_thinking === 'boolean' && enableThinkingInput) {
        enableThinkingInput.checked = cfg.enable_thinking;
    }
}

let saveUserConfigTimer = null;

function scheduleUserConfigSave() {
    if (saveUserConfigTimer) {
        clearTimeout(saveUserConfigTimer);
    }
    saveUserConfigTimer = setTimeout(() => {
        saveUserConfig(getGenerationConfig());
        saveUserConfigTimer = null;
    }, 150);
}

function getNpuPollBounds() {
    const min = npuPollIntervalInput ? parseInt(npuPollIntervalInput.min, 10) : 200;
    const max = npuPollIntervalInput ? parseInt(npuPollIntervalInput.max, 10) : 5000;
    return {
        min: Number.isFinite(min) ? min : 200,
        max: Number.isFinite(max) ? max : 5000
    };
}

function setNpuPollInterval(value, persist = true) {
    const bounds = getNpuPollBounds();
    const safe = clamp(parseInt(value, 10) || DEFAULT_NPU_POLL_MS, bounds.min, bounds.max);
    npuPollIntervalMs = safe;
    if (npuPollIntervalInput) {
        npuPollIntervalInput.value = safe;
    }
    if (npuPollIntervalValue) {
        npuPollIntervalValue.textContent = safe;
    }
    if (persist) {
        localStorage.setItem(NPU_POLL_INTERVAL_KEY, String(safe));
    }
    if (npuMonitorActive && npuPollInterval) {
        clearInterval(npuPollInterval);
        npuPollInterval = setInterval(pollNpuStatus, npuPollIntervalMs);
    }
}

function initNpuPollInterval() {
    const stored = parseInt(localStorage.getItem(NPU_POLL_INTERVAL_KEY) || '', 10);
    const value = Number.isFinite(stored) ? stored : DEFAULT_NPU_POLL_MS;
    setNpuPollInterval(value, false);
}

function getAutoLoadEnabled() {
    const raw = localStorage.getItem(AUTO_LOAD_MODEL_KEY);
    if (raw === null) return DEFAULT_AUTO_LOAD_MODEL;
    return raw === '1' || raw === 'true';
}

function setAutoLoadEnabled(enabled, persist = true) {
    const next = !!enabled;
    if (autoLoadModelToggle) {
        autoLoadModelToggle.checked = next;
    }
    if (persist) {
        localStorage.setItem(AUTO_LOAD_MODEL_KEY, next ? '1' : '0');
    }
}

function initAutoLoadSetting() {
    setAutoLoadEnabled(getAutoLoadEnabled(), false);
}

function getCloseBehavior() {
    const raw = localStorage.getItem(CLOSE_BEHAVIOR_KEY);
    if (raw === 'background' || raw === 'exit' || raw === 'ask') {
        return raw;
    }
    return DEFAULT_CLOSE_BEHAVIOR;
}

function setCloseBehavior(value, persist = true) {
    const next = value === 'background' || value === 'exit' || value === 'ask'
        ? value
        : DEFAULT_CLOSE_BEHAVIOR;
    if (closeBehaviorSelect) {
        closeBehaviorSelect.value = next;
    }
    if (persist) {
        localStorage.setItem(CLOSE_BEHAVIOR_KEY, next);
    }
}

function initCloseBehavior() {
    setCloseBehavior(getCloseBehavior(), false);
}

function openCloseConfirmModal() {
    if (!closeConfirmModal) return;
    showAnimated(closeConfirmModal);
}

function closeCloseConfirmModal() {
    if (!closeConfirmModal) return;
    hideAnimated(closeConfirmModal);
}

function requestCloseToTray() {
    updateTrayMenuLabels();
    const invoke = getTauriInvoke();
    if (!invoke) return;
    invoke('hide_main_window').catch((err) => {
        console.warn('Failed to hide window:', err);
    });
}

function requestExitApp() {
    const invoke = getTauriInvoke();
    if (!invoke) return;
    invoke('exit_app').catch((err) => {
        console.warn('Failed to exit app:', err);
    });
}

function handleCloseChoice(choice) {
    setCloseBehavior(choice);
    closeCloseConfirmModal();
    if (choice === 'background') {
        requestCloseToTray();
    } else {
        requestExitApp();
    }
}

function handleCloseRequest() {
    const behavior = getCloseBehavior();
    if (behavior === 'background') {
        requestCloseToTray();
        return;
    }
    if (behavior === 'exit') {
        requestExitApp();
        return;
    }
    openCloseConfirmModal();
}

window.__idleNpuCloseRequested = () => {
    handleCloseRequest();
};

function normalizeDownloadModels(models) {
    const items = Array.isArray(models) ? models : [];
    return items.map((item) => {
        if (typeof item === 'string') {
            const repoId = item;
            const name = repoId.split('/').pop() || repoId;
            return { repo_id: repoId, name, libraries: [] };
        }
        if (item && typeof item === 'object') {
            const repoId = item.repo_id || item.id || item.repoId || '';
            if (!repoId) return null;
            const name = item.name || item.display_name || repoId.split('/').pop() || repoId;
            const downloads = Number.isFinite(item.downloads)
                ? item.downloads
                : parseInt(item.downloads, 10);
            return {
                repo_id: repoId,
                name,
                downloads: Number.isFinite(downloads) ? downloads : null,
                license: item.license || '',
                libraries: Array.isArray(item.libraries) ? item.libraries : [],
                model_id: item.model_id || null,
                url: item.url || ''
            };
        }
        return null;
    }).filter(Boolean);
}

function normalizePresetModels(models) {
    const items = Array.isArray(models) ? models : [];
    return items.map((item) => {
        if (typeof item === 'string') {
            return { id: item, label: item };
        }
        if (item && typeof item === 'object') {
            const id = item.repo_id || item.id || item.name || '';
            const label = item.name || item.repo_id || item.id || '';
            if (id) return { id, label };
        }
        return null;
    }).filter(Boolean);
}

function populateDownloadModelList() {
    if (!downloadModelList) return;
    downloadModelList.innerHTML = '';
    const list = downloadCatalogModels.length ? downloadCatalogModels : presetModels;
    list.forEach((model) => {
        const option = document.createElement('option');
        const value = model.repo_id || model.id || model;
        if (!value) return;
        option.value = value;
        option.textContent = model.name || model.label || value;
        downloadModelList.appendChild(option);
    });
}

function formatDownloadCount(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return '';
    if (number >= 1_000_000) {
        return `${(number / 1_000_000).toFixed(1).replace(/\\.0$/, '')}M`;
    }
    if (number >= 1_000) {
        return `${(number / 1_000).toFixed(1).replace(/\\.0$/, '')}k`;
    }
    return `${number}`;
}

function formatLibraryLabel(value) {
    const label = String(value || '').trim();
    if (!label) return '';
    if (label.toLowerCase() === 'openvino') return 'OpenVINO';
    if (label.toLowerCase() === 'pytorch') return 'PyTorch';
    return label;
}

function buildModelScopeUrl(repoId) {
    return `https://www.modelscope.cn/models/${repoId}`;
}

function setSelectedDownloadRepo(repoId) {
    if (!downloadCards) return;
    downloadCards.querySelectorAll('.download-card').forEach((card) => {
        card.classList.toggle('selected', repoId && card.dataset.repoId === repoId);
    });
}

function renderDownloadCards(filterText = '') {
    if (!downloadCards) return;
    const query = (filterText || '').trim().toLowerCase();
    downloadCards.innerHTML = '';
    let visible = 0;
    const useLabel = escapeHtml(t('download_card_action_use', 'Use ID'));
    const downloadLabel = escapeHtml(t('download_card_action_download', 'Download'));
    const viewLabel = escapeHtml(t('download_card_action_view', 'View'));
    const downloadsLabel = escapeHtml(t('download_card_downloads', 'Downloads'));
    const licenseLabel = escapeHtml(t('download_card_license', 'License'));

    downloadCatalogModels.forEach((model) => {
        const repoId = model.repo_id || '';
        if (!repoId) return;
        const name = model.name || repoId;
        const haystack = `${name} ${repoId}`.toLowerCase();
        if (query && !haystack.includes(query)) return;

        const downloads = formatDownloadCount(model.downloads);
        const metaParts = [];
        if (downloads) {
            metaParts.push(`<span class="download-meta-pill">${downloadsLabel}: ${downloads}</span>`);
        }
        if (model.license) {
            metaParts.push(`<span class="download-meta-pill">${licenseLabel}: ${escapeHtml(model.license)}</span>`);
        }
        (model.libraries || []).forEach((lib) => {
            const label = formatLibraryLabel(lib);
            if (label) {
                metaParts.push(`<span class="download-meta-pill">${escapeHtml(label)}</span>`);
            }
        });

        const url = model.url || buildModelScopeUrl(repoId);
        const card = document.createElement('div');
        card.className = 'download-card';
        card.dataset.repoId = repoId;
        card.innerHTML = `
            <div class="download-card-title">${escapeHtml(name)}</div>
            <div class="download-card-repo">${escapeHtml(repoId)}</div>
            <div class="download-card-meta">${metaParts.join('')}</div>
            <div class="download-card-actions">
                <button class="download-card-btn" type="button" data-action="use">${useLabel}</button>
                <button class="download-card-btn primary" type="button" data-action="download">${downloadLabel}</button>
                <a class="download-card-link" href="${escapeHtml(url)}" target="_blank" rel="noopener">${viewLabel}</a>
            </div>
        `;
        downloadCards.appendChild(card);
        visible += 1;
    });

    if (downloadCardsEmpty) {
        downloadCardsEmpty.classList.toggle('hidden', visible > 0);
    }
    if (downloadModelInput) {
        setSelectedDownloadRepo(downloadModelInput.value.trim());
    }
    if (downloadRunning && downloadCards) {
        downloadCards.querySelectorAll('button').forEach((btn) => {
            btn.disabled = true;
        });
    }
}

function handleDownloadCardClick(event) {
    const card = event.target.closest('.download-card');
    if (!card || !downloadCards || !downloadCards.contains(card)) return;
    const repoId = card.dataset.repoId;
    if (!repoId) return;

    const actionBtn = event.target.closest('[data-action]');
    if (actionBtn) {
        if (downloadModelInput) {
            downloadModelInput.value = repoId;
        }
        setSelectedDownloadRepo(repoId);
        if (actionBtn.dataset.action === 'download') {
            startDownload();
        } else if (actionBtn.dataset.action === 'use') {
            if (downloadModelInput) downloadModelInput.focus();
        }
        return;
    }
    if (event.target.closest('a')) return;
    if (downloadModelInput) {
        downloadModelInput.value = repoId;
        downloadModelInput.focus();
    }
    setSelectedDownloadRepo(repoId);
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

function applyLoadedModel(path, device, maxPromptLen) {
    const safePath = path || '';
    const safeDevice = device || 'AUTO';
    const safeMaxPromptLen = Number.isFinite(maxPromptLen)
        ? maxPromptLen
        : (maxPromptLenInput ? parseInt(maxPromptLenInput.value) : 16384);

    loadedModelConfig = {
        path: safePath,
        device: safeDevice,
        maxPromptLen: safeMaxPromptLen
    };
    modelLoaded = true;
    saveLastModelConfig(safePath, safeDevice, safeMaxPromptLen);
    localStorage.setItem(MAX_PROMPT_LEN_KEY, String(safeMaxPromptLen));

    if (localModelSelect) localModelSelect.value = safePath;
    if (welcomeLocalModelSelect) welcomeLocalModelSelect.value = safePath;
    if (deviceSelect && deviceSelect.querySelector(`option[value="${safeDevice}"]`)) {
        deviceSelect.value = safeDevice;
    }
    if (welcomeDeviceSelect && welcomeDeviceSelect.querySelector(`option[value="${safeDevice}"]`)) {
        welcomeDeviceSelect.value = safeDevice;
    }
    if (maxPromptLenInput && maxPromptLenValue) {
        maxPromptLenInput.value = safeMaxPromptLen;
        maxPromptLenValue.textContent = safeMaxPromptLen;
    }
    if (welcomeMaxPromptLenInput && welcomeMaxPromptLenValue) {
        welcomeMaxPromptLenInput.value = safeMaxPromptLen;
        welcomeMaxPromptLenValue.textContent = safeMaxPromptLen;
    }

    messageInput.disabled = false;
    sendBtn.disabled = false;
    updateWelcomeOverlay();
    setModelReloadRequired(false);
    updateModelSwitcherLabel();
    renderModelSwitcherList();
}

async function attemptAutoLoadLastModel() {
    if (modelLoaded) return;
    const lastConfig = loadLastModelConfig();
    if (!lastConfig || !lastConfig.path) return;

    const path = lastConfig.path;
    const device = lastConfig.device || 'AUTO';
    const maxPromptLen = parseInt(lastConfig.max_prompt_len, 10) || 16384;

    if (localModelSelect) localModelSelect.value = path;
    if (welcomeLocalModelSelect) welcomeLocalModelSelect.value = path;
    if (deviceSelect && deviceSelect.querySelector(`option[value="${device}"]`)) {
        deviceSelect.value = device;
    }
    if (welcomeDeviceSelect && welcomeDeviceSelect.querySelector(`option[value="${device}"]`)) {
        welcomeDeviceSelect.value = device;
    }
    if (maxPromptLenInput && maxPromptLenValue) {
        maxPromptLenInput.value = maxPromptLen;
        maxPromptLenValue.textContent = maxPromptLen;
    }
    if (welcomeMaxPromptLenInput && welcomeMaxPromptLenValue) {
        welcomeMaxPromptLenInput.value = maxPromptLen;
        welcomeMaxPromptLenValue.textContent = maxPromptLen;
    }

    await loadModelFromWelcome();
}

// ============== Initialize ==============

document.addEventListener('DOMContentLoaded', init);

async function init() {
    initNpuPollInterval();
    initAutoLoadSetting();
    initCloseBehavior();
    await loadI18n(currentLang);
    await loadConfig();
    await restoreModelStatus();
    if (!modelLoaded && getAutoLoadEnabled()) {
        attemptAutoLoadLastModel();
    }
    await loadSessions();
    setupEventListeners();
    setupSettingsListeners();
    setupLangSwitcher();
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) {
            updateTrayMenuLabels();
        }
    });
    window.addEventListener('focus', () => updateTrayMenuLabels());
    cacheSettingGroups();
    initWelcomeOverlay();
    initPerformancePanel();
    initSystemStatus();
    initCodeBlockObserver();
}

function setupLangSwitcher() {
    langBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        if (langDropdown.classList.contains('ui-open')) {
            hideAnimated(langDropdown);
        } else {
            showAnimated(langDropdown);
        }
    });

    document.querySelectorAll('.lang-option').forEach(btn => {
        btn.addEventListener('click', async () => {
            const lang = btn.dataset.lang;
            await loadI18n(lang);
            hideAnimated(langDropdown);
        });
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!langBtn.contains(e.target) && !langDropdown.contains(e.target)) {
            hideAnimated(langDropdown);
        }
    });
}

function setWelcomeOverlayVisible(visible) {
    if (!welcomeOverlay || !appContainer) return;
    welcomeOverlay.classList.toggle('hidden', !visible);
    appContainer.classList.toggle('welcome-locked', visible);
}

function updateWelcomeOverlay() {
    setWelcomeOverlayVisible(!modelLoaded);
}

function initWelcomeOverlay() {
    if (!welcomeOverlay) return;
    updateWelcomeOverlay();
    if (welcomeLocalModelSelect) {
        welcomeLocalModelSelect.addEventListener('change', () => {
            updateSupportedSettingsForPath(welcomeLocalModelSelect.value);
        });
    }
    if (welcomeRefreshModelsBtn) {
        welcomeRefreshModelsBtn.addEventListener('click', loadLocalModels);
    }
    if (welcomeMaxPromptLenInput && welcomeMaxPromptLenValue) {
        welcomeMaxPromptLenInput.addEventListener('input', () => {
            applyMaxPromptLen(welcomeMaxPromptLenInput.value, true);
        });
    }
    if (welcomeLoadBtn) {
        welcomeLoadBtn.addEventListener('click', (event) => {
            event.preventDefault();
            loadModelFromWelcome();
        });
    }
    updateWelcomeLoadingText();
}

function updateWelcomeLoadingText() {
    if (!welcomeLoadingText) return;
    welcomeLoadingText.textContent = t('status_loading_model', '...');
}

function setWelcomeLoading(isLoading) {
    if (welcomeLoading) {
        welcomeLoading.classList.toggle('hidden', !isLoading);
    }
    if (welcomeLoadBtn) welcomeLoadBtn.disabled = isLoading;
    if (welcomeDownloadBtn) welcomeDownloadBtn.disabled = isLoading;
    if (welcomeLocalModelSelect) welcomeLocalModelSelect.disabled = isLoading;
    if (welcomeDeviceSelect) welcomeDeviceSelect.disabled = isLoading;
    if (welcomeMaxPromptLenInput) welcomeMaxPromptLenInput.disabled = isLoading;
    if (welcomeRefreshModelsBtn) welcomeRefreshModelsBtn.disabled = isLoading;
    if (isLoading) {
        updateWelcomeLoadingText();
    }
}

async function loadConfig() {
    try {
        const response = await fetch(`${API_BASE}/api/config`);
        const data = await response.json();
        const defaultConfig = data.default_config || {};
        const storedConfig = loadUserConfig();
        config = storedConfig ? { ...defaultConfig, ...storedConfig } : defaultConfig;
        presetModels = normalizePresetModels(data.preset_models || []);
        downloadCatalogModels = normalizeDownloadModels(
            data.download_models || data.preset_models || []
        );
        availableDevices = data.available_devices || ['AUTO'];
        maxFileBytes = data.max_file_bytes || maxFileBytes;

        populateDownloadModelList();
        renderDownloadCards(downloadSearchInput ? downloadSearchInput.value : '');
        if (downloadCollectionLink && data.download_collection_url) {
            downloadCollectionLink.href = data.download_collection_url;
        }

        // Populate devices
        if (deviceSelect) deviceSelect.innerHTML = '';
        if (welcomeDeviceSelect) welcomeDeviceSelect.innerHTML = '';
        availableDevices.forEach(device => {
            const option = document.createElement('option');
            option.value = device;
            option.textContent = device;
            if (deviceSelect) deviceSelect.appendChild(option);
            if (welcomeDeviceSelect) {
                const welcomeOption = document.createElement('option');
                welcomeOption.value = device;
                welcomeOption.textContent = device;
                welcomeDeviceSelect.appendChild(welcomeOption);
            }
        });

        // Set default values
    if (config) {
        applyConfigToInputs(config);
    }
    const preferredMaxPromptLen = getPreferredMaxPromptLen();
    if (preferredMaxPromptLen !== null) {
        applyMaxPromptLen(preferredMaxPromptLen);
    } else if (config && config.max_prompt_len) {
        applyMaxPromptLen(config.max_prompt_len);
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
        if (welcomeLocalModelSelect) {
            welcomeLocalModelSelect.innerHTML = `<option value="">${t('opt_select_model')}</option>`;
        }
        localModels.forEach(model => {
            const option = document.createElement('option');
            option.value = model.path;
            option.textContent = model.name;
            localModelSelect.appendChild(option);
            if (welcomeLocalModelSelect) {
                const welcomeOption = document.createElement('option');
                welcomeOption.value = model.path;
                welcomeOption.textContent = model.name;
                welcomeLocalModelSelect.appendChild(welcomeOption);
            }
        });

        renderModelSwitcherList();
        updateModelSwitcherLabel();

        if (localModelSelect && localModelSelect.value) {
            await updateSupportedSettingsForPath(localModelSelect.value);
        }
        if (welcomeLocalModelSelect && welcomeLocalModelSelect.value) {
            await updateSupportedSettingsForPath(welcomeLocalModelSelect.value);
        }
        updateReloadRequirement();
    } catch (error) {
        console.error('Failed to load local models:', error);
    }
}

async function restoreModelStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/models/status`);
        if (!response.ok) return;
        const data = await response.json();
        if (!data || !data.loaded) return;

        const lastConfig = loadLastModelConfig();
        const path = data.path || (lastConfig ? lastConfig.path : '');
        const device = data.device || (lastConfig ? lastConfig.device : 'AUTO');
        const maxPromptLen = lastConfig && lastConfig.max_prompt_len
            ? parseInt(lastConfig.max_prompt_len, 10)
            : (maxPromptLenInput ? parseInt(maxPromptLenInput.value) : 16384);

        applyLoadedModel(path, device, maxPromptLen);
        if (path) {
            await updateSupportedSettingsForPath(path);
        }
    } catch (error) {
        console.warn('Failed to restore model status:', error);
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
        let className = 'session-item';
        if (session.id === currentSessionId) className += ' active';
        if (session.is_temporary) className += ' temporary';
        item.className = className;
        const title = session.is_temporary
            ? (session.title || t('temp_chat_name', 'Temp Chat'))
            : (session.title || t('default_chat_name'));
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
        scrollToBottom(true);
    }
    updateScrollState();
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
    if (role === 'assistant') {
        contentDiv.innerHTML = formatAssistantContent(content);
        renderMermaid(contentDiv);
        renderMath(contentDiv);
        renderCodeHighlight(contentDiv);
    } else {
        contentDiv.innerHTML = formatContent(content, role);
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
    if (role === 'assistant') {
        contentDiv.innerHTML = formatAssistantContent(content);
        renderMermaid(contentDiv);
        renderMath(contentDiv);
        renderCodeHighlight(contentDiv);
    } else {
        contentDiv.innerHTML = formatContent(content, role);
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

async function copyTextToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        return true;
    } catch (error) {
        const temp = document.createElement('textarea');
        temp.value = text;
        document.body.appendChild(temp);
        temp.select();
        try {
            document.execCommand('copy');
            return true;
        } catch (err) {
            return false;
        } finally {
            document.body.removeChild(temp);
        }
    }
}

async function handleCopyMessage(index) {
    const msg = getMessageByIndex(index);
    if (!msg) return;
    const text = normalizeMessageContent(msg.content);
    const ok = await copyTextToClipboard(text);
    showToast(ok ? t('msg_copied', 'Copied successfully') : t('dialog_error', 'Error'));
}

async function handleCopyCode(btn) {
    const block = btn.closest('.code-block');
    const codeEl = block ? block.querySelector('code') : null;
    if (!codeEl) return;
    const text = codeEl.textContent || '';
    const ok = await copyTextToClipboard(text);
    showToast(ok ? t('msg_copied', 'Copied successfully') : t('dialog_error', 'Error'));
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
    if (modelReloadRequired) {
        showToast(t('status_reload_required', 'Reload required'));
        return;
    }

    // Create assistant placeholder
    const assistantIndex = currentMessages.length;
    currentMessages.push({ role: 'assistant', content: '' });
    appendMessage('assistant', '', true, assistantIndex);

    // Show generating state
    isGenerating = true;
    sendBtn.classList.add('hidden');
    stopBtn.classList.remove('hidden');

    const contentDiv = messagesDiv.querySelector(`.message[data-index="${assistantIndex}"] .message-content`);
    setAssistantPlaceholder(contentDiv);
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
                                contentDiv.innerHTML = formatAssistantContent(fullResponse);
                                renderMermaid(contentDiv);
                                renderMath(contentDiv);
                                renderCodeHighlight(contentDiv);
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
                                    <span class="stat-separator"> · </span>
                                    <span class="stat-item"><strong>${data.stats.speed}</strong> t/s</span>
                                    <span class="stat-separator"> · </span>
                                    <span class="stat-item"><strong>${data.stats.time}</strong>s</span>
                                `;
                                contentDiv.appendChild(statsDiv);
                                updateGenStats(data.stats);
                            }
                            if (contentDiv) {
                                renderMermaid(contentDiv);
                                renderMath(contentDiv);
                                renderCodeHighlight(contentDiv);
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
        const copyLabel = escapeHtml(t('btn_copy', 'Copy'));
        return `
            <div class="code-block">
                <pre><code class="${langClass}">${escaped}</code></pre>
                <button class="code-copy-btn" type="button" title="${copyLabel}">${copyLabel}</button>
            </div>
        `;
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
    text = normalizeStrongLineBreaks(text);
    const extracted = extractMathBlocks(text);
    const processed = extracted.text;
    if (typeof marked !== 'undefined') {
        setupMarkdown();
        const html = marked.parse(processed);
        const withStrong = applyFallbackStrong(html);
        return restoreMathBlocks(withStrong, extracted.blocks);
    }
    const escaped = escapeHtml(processed).replace(/\n/g, '<br>');
    return restoreMathBlocks(escaped, extracted.blocks);
}

function extractMathBlocks(text) {
    if (!text || (text.indexOf('$$') === -1 && text.indexOf('\\[') === -1)) {
        return { text, blocks: [] };
    }
    const blocks = [];
    const blockPattern = /\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\]/g;

    const replaceBlocks = (chunk) => chunk.replace(blockPattern, (match) => {
        const id = blocks.length;
        blocks.push(match);
        return `@@MATHBLOCK_${id}@@`;
    });

    const fenceParts = text.split(/(```[\s\S]*?```)/g);
    const processed = fenceParts.map((part, idx) => {
        if (idx % 2) return part;
        const inlineParts = part.split(/(`[^`]*`)/g);
        return inlineParts.map((chunk, cidx) => {
            if (cidx % 2) return chunk;
            return replaceBlocks(chunk);
        }).join('');
    }).join('');

    return { text: processed, blocks };
}

function restoreMathBlocks(html, blocks) {
    if (!blocks || blocks.length === 0) return html;
    return html.replace(/@@MATHBLOCK_(\d+)@@/g, (match, id) => {
        const idx = Number(id);
        const raw = blocks[idx];
        if (!raw) return match;
        const safe = escapeHtml(raw.trim());
        return `<div class="math-block">${safe}</div>`;
    });
}

function applyFallbackStrong(html) {
    if (!html || html.indexOf('**') === -1 || typeof document === 'undefined') return html;
    const container = document.createElement('div');
    container.innerHTML = html;

    const shouldSkipNode = (node) => {
        let el = node.parentElement;
        while (el) {
            const tag = el.tagName ? el.tagName.toLowerCase() : '';
            if (tag === 'code' || tag === 'pre' || tag === 'script' || tag === 'style') return true;
            if (el.classList && el.classList.contains('mermaid')) return true;
            el = el.parentElement;
        }
        return false;
    };

    const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, {
        acceptNode(node) {
            if (!node.nodeValue || node.nodeValue.indexOf('**') === -1) return NodeFilter.FILTER_REJECT;
            if (shouldSkipNode(node)) return NodeFilter.FILTER_REJECT;
            return NodeFilter.FILTER_ACCEPT;
        }
    });

    const nodes = [];
    while (walker.nextNode()) {
        nodes.push(walker.currentNode);
    }

    nodes.forEach((node) => {
        const text = node.nodeValue;
        if (!text || text.indexOf('**') === -1) return;
        const frag = document.createDocumentFragment();
        let cursor = 0;
        while (true) {
            const start = text.indexOf('**', cursor);
            if (start === -1) {
                frag.appendChild(document.createTextNode(text.slice(cursor)));
                break;
            }
            const end = text.indexOf('**', start + 2);
            if (end === -1) {
                frag.appendChild(document.createTextNode(text.slice(cursor)));
                break;
            }
            if (start > cursor) {
                frag.appendChild(document.createTextNode(text.slice(cursor, start)));
            }
            const inner = text.slice(start + 2, end);
            const strongEl = document.createElement('strong');
            strongEl.textContent = inner;
            frag.appendChild(strongEl);
            cursor = end + 2;
        }
        node.parentNode.replaceChild(frag, node);
    });

    return container.innerHTML;
}

function normalizeStrongLineBreaks(text) {
    if (!text || text.indexOf('**') === -1) return text;
    const fenceParts = text.split(/(```[\s\S]*?```)/g);
    return fenceParts.map((part, idx) => {
        if (idx % 2) return part;
        const inlineParts = part.split(/(`[^`]*`)/g);
        return inlineParts.map((chunk, cidx) => {
            if (cidx % 2) return chunk;
            return chunk.replace(/\*\*([\s\S]*?)\*\*/g, (match, inner) => {
                if (!/[\r\n\u2028\u2029]/.test(inner)) return match;
                const flattened = inner.replace(/[\r\n\u2028\u2029]+/g, ' ');
                return `**${flattened}**`;
            });
        }).join('');
    }).join('');
}

function setupCodeHighlight() {
    if (codeHighlightReady || typeof hljs === 'undefined') return;
    codeHighlightReady = true;
}

function createCodeCopyButton() {
    const copyLabel = t('btn_copy', 'Copy');
    const btn = document.createElement('button');
    btn.className = 'code-copy-btn';
    btn.type = 'button';
    btn.title = copyLabel;
    btn.textContent = copyLabel;
    return btn;
}

function decorateCodeBlocks(container) {
    if (!container) return;
    const codeNodes = Array.from(container.querySelectorAll('pre code'));
    codeNodes.forEach((codeEl) => {
        const pre = codeEl.parentElement;
        if (!pre) return;
        const existingWrapper = pre.parentElement;
        if (existingWrapper && existingWrapper.classList.contains('code-block')) {
            if (!existingWrapper.querySelector('.code-copy-btn')) {
                existingWrapper.appendChild(createCodeCopyButton());
            }
            return;
        }
        const wrapper = document.createElement('div');
        wrapper.className = 'code-block';
        pre.parentNode.insertBefore(wrapper, pre);
        wrapper.appendChild(pre);
        wrapper.appendChild(createCodeCopyButton());
    });
}

function renderCodeHighlight(container) {
    if (!container) return;
    decorateCodeBlocks(container);
    if (typeof hljs === 'undefined') return;
    setupCodeHighlight();
    const blocks = container.querySelectorAll('pre code');
    blocks.forEach((block) => {
        if (block.classList.contains('hljs')) return;
        try {
            hljs.highlightElement(block);
        } catch (error) {
            console.warn('Highlight failed:', error);
        }
    });
}

function initCodeBlockObserver() {
    if (!messagesDiv || codeBlockObserver) return;
    codeBlockObserver = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            mutation.addedNodes.forEach((node) => {
                if (node.nodeType !== 1) return;
                renderCodeHighlight(node);
            });
        }
    });
    codeBlockObserver.observe(messagesDiv, { childList: true, subtree: true });
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

const MATH_RENDER_OPTIONS = {
    delimiters: [
        { left: '$$', right: '$$', display: true },
        { left: '$', right: '$', display: false },
        { left: '\\(', right: '\\)', display: false },
        { left: '\\[', right: '\\]', display: true }
    ],
    throwOnError: false,
    ignoredTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code'],
    ignoredClasses: ['mermaid']
};
const MATH_DELIM_RE = /(\$\$|\\\[|\\\(|\$)/;

function renderMath(container) {
    if (!container || typeof renderMathInElement === 'undefined') return;
    try {
        renderMathInElement(container, MATH_RENDER_OPTIONS);
    } catch (error) {
        console.warn('Math render failed:', error);
    }
}

function renderMathHtml(html) {
    if (!html || typeof renderMathInElement === 'undefined') return html;
    if (!MATH_DELIM_RE.test(html)) return html;
    const wrapper = document.createElement('div');
    wrapper.innerHTML = html;
    try {
        renderMathInElement(wrapper, MATH_RENDER_OPTIONS);
    } catch (error) {
        console.warn('Math render failed:', error);
    }
    return wrapper.innerHTML;
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

function formatAssistantContent(content) {
    return formatContent(content, 'assistant');
}

function setAssistantPlaceholder(contentDiv) {
    if (!contentDiv) return;
    const label = escapeHtml(t('msg_thinking', 'Thinking...'));
    contentDiv.innerHTML = `
        <div class="assistant-placeholder">
            <span class="assistant-placeholder-text">${label}</span>
            <span class="typing-dots"><span></span><span></span><span></span></span>
        </div>
    `;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function isNearBottom() {
    if (!chatContainer) return true;
    const distance = chatContainer.scrollHeight - chatContainer.scrollTop - chatContainer.clientHeight;
    return distance <= SCROLL_BOTTOM_THRESHOLD;
}

function updateScrollState() {
    if (!chatContainer) return;
    const atBottom = isNearBottom();
    autoScrollEnabled = atBottom;
    if (scrollBottomBtn) {
        scrollBottomBtn.classList.toggle('visible', !atBottom);
    }
}

function scrollToBottom(force = false, behavior = 'auto') {
    if (!chatContainer) return;
    if (!force && !autoScrollEnabled) return;
    const top = chatContainer.scrollHeight;
    if (behavior === 'smooth') {
        chatContainer.scrollTo({ top, behavior: 'smooth' });
    } else {
        chatContainer.scrollTop = top;
    }
    if (force) {
        autoScrollEnabled = true;
    }
    if (scrollBottomBtn) {
        scrollBottomBtn.classList.remove('visible');
    }
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

// Toggle sidebar visibility
function toggleSidebar() {
    sidebar.classList.toggle('collapsed');
}

// Create temporary chat (not saved to history)
async function createTempChat() {
    try {
        const response = await fetch(`${API_BASE}/api/sessions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_temporary: true })
        });
        const data = await response.json();
        sessions.unshift({ id: data.id, title: data.title, is_temporary: true });
        currentSessionId = data.id;
        renderSessions();
        renderMessages([]);
        pendingAttachments = [];
        renderAttachments();

        // Select the new session
        await fetch(`${API_BASE}/api/sessions/${data.id}/select`, { method: 'POST' });
    } catch (error) {
        console.error('Failed to create temp chat:', error);
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
    showAnimated(renameModal);
    renameInput.focus();
}

function closeRenameModal() {
    hideAnimated(renameModal);
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
    if (modelReloadRequired) {
        showToast(t('status_reload_required', 'Reload required'));
        return;
    }

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
    setAssistantPlaceholder(contentDiv);

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
                                contentDiv.innerHTML = formatAssistantContent(fullResponse);
                                renderMermaid(contentDiv);
                                renderMath(contentDiv);
                                renderCodeHighlight(contentDiv);
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
                            if (contentDiv) {
                                renderMermaid(contentDiv);
                                renderMath(contentDiv);
                                renderCodeHighlight(contentDiv);
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

async function loadModelFromWelcome() {
    const modelPath = welcomeLocalModelSelect ? welcomeLocalModelSelect.value : '';
    if (!modelPath) {
        showToast(t('opt_select_model'));
        return;
    }
    await updateSupportedSettingsForPath(modelPath);

    const device = welcomeDeviceSelect ? welcomeDeviceSelect.value : (deviceSelect ? deviceSelect.value : 'AUTO');
    const maxPromptLen = welcomeMaxPromptLenInput
        ? parseInt(welcomeMaxPromptLenInput.value)
        : parseInt(maxPromptLenInput.value);

    setWelcomeLoading(true);
    statusDot.className = 'status-dot loading';
    modelStatus.textContent = t('status_loading_model', device);

    try {
        const response = await fetch(`${API_BASE}/api/models/load`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                source: 'local',
                model_id: '',
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

        applyLoadedModel(modelPath, data.device, maxPromptLen);

        showToast(t('dialog_loaded_msg', data.device));
    } catch (error) {
        statusDot.className = 'status-dot';
        modelStatus.textContent = t('dialog_error');
        showToast(error.message);
    } finally {
        setWelcomeLoading(false);
    }
}

async function loadModel() {
    const modelPath = localModelSelect ? localModelSelect.value : '';
    if (!modelPath) {
        showToast(t('opt_select_model'));
        return;
    }
    await updateSupportedSettingsForPath(modelPath);

    const device = deviceSelect ? deviceSelect.value : 'AUTO';
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
                source: 'local',
                model_id: '',
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

        applyLoadedModel(modelPath, data.device, maxPromptLen);

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

function setDownloadRunning(running) {
    downloadRunning = running;
    if (downloadProgress) {
        downloadProgress.classList.toggle('hidden', !running);
    }
    if (downloadModelBtn) downloadModelBtn.disabled = running;
    if (downloadModelInput) downloadModelInput.disabled = running;
    if (downloadSearchInput) downloadSearchInput.disabled = running;
    if (cancelDownloadBtn) cancelDownloadBtn.disabled = !running;
    if (downloadCards) {
        downloadCards.querySelectorAll('button').forEach((btn) => {
            btn.disabled = running;
        });
    }
    if (!running && progressFill) {
        progressFill.classList.remove('indeterminate');
        progressFill.style.width = '0%';
    }
}

function setDownloadIndeterminate(indeterminate) {
    if (!progressFill) return;
    progressFill.classList.toggle('indeterminate', indeterminate);
    if (indeterminate) {
        progressFill.style.width = '40%';
    }
}

async function startDownload() {
    if (downloadRunning) return;
    const repoId = downloadModelInput ? downloadModelInput.value.trim() : '';
    if (!repoId) {
        showToast(t('placeholder_repo'));
        return;
    }

    setDownloadRunning(true);
    setDownloadIndeterminate(true);
    if (downloadStatus) {
        downloadStatus.textContent = t('dl_init_process');
    }

    const abortController = new AbortController();
    downloadAbortController = abortController;
    let finishedPath = '';

    try {
        const response = await fetch(`${API_BASE}/api/download/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ repo_id: repoId }),
            signal: abortController.signal
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Download failed');
        }

        if (!response.body) {
            throw new Error('Download stream not available');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        let done = false;
        while (!done) {
            const { value, done: streamDone } = await reader.read();
            if (streamDone) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                try {
                    const data = JSON.parse(line.slice(6));
                    if (data.type === 'progress') {
                        const percent = Math.max(0, Math.min(100, data.percent || 0));
                        setDownloadIndeterminate(false);
                        if (progressFill) {
                            progressFill.style.width = `${percent}%`;
                        }
                        if (downloadStatus) {
                            const name = data.file || repoId;
                            downloadStatus.textContent = `${t('status_downloading', name)} ${percent}%`;
                        }
                    } else if (data.type === 'log') {
                        if (downloadStatus && data.message) {
                            downloadStatus.textContent = data.message;
                        }
                    } else if (data.type === 'finished') {
                        finishedPath = data.path || '';
                    } else if (data.type === 'error') {
                        throw new Error(data.message || 'Download failed');
                    } else if (data.type === 'done') {
                        done = true;
                        break;
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

        if (downloadStatus) {
            downloadStatus.textContent = t('status_ready');
        }
        if (progressFill) {
            progressFill.classList.remove('indeterminate');
            progressFill.style.width = '100%';
        }
        await loadLocalModels();
        const label = finishedPath
            ? finishedPath.split(/[/\\\\]/).pop()
            : repoId.split('/').pop();
        if (label) {
            showToast(t('dialog_model_ready', label));
        }
    } catch (error) {
        if (error && error.name === 'AbortError') {
            return;
        }
        if (downloadStatus) {
            downloadStatus.textContent = `${t('dialog_error')}: ${error.message}`;
        }
        showToast(error.message || t('dialog_error'));
    } finally {
        downloadAbortController = null;
        setDownloadRunning(false);
    }
}

async function cancelDownload() {
    try {
        await fetch(`${API_BASE}/api/download/stop`, { method: 'POST' });
        if (downloadAbortController) {
            downloadAbortController.abort();
            downloadAbortController = null;
        }
        if (downloadStatus) {
            downloadStatus.textContent = t('dl_cancelled');
        }
        setDownloadRunning(false);
        showToast(t('dl_cancelled'));
    } catch (error) {
        console.error('Failed to cancel download:', error);
    }
}

function openSettingsModal() {
    showAnimated(settingsModal);
}

function closeSettingsModal() {
    hideAnimated(settingsModal);
}

function openDownloadModal() {
    if (!downloadModal) return;
    showAnimated(downloadModal);
    if (downloadSearchInput) {
        downloadSearchInput.focus();
    } else if (downloadModelInput) {
        downloadModelInput.focus();
    }
}

function closeDownloadModal() {
    if (!downloadModal) return;
    hideAnimated(downloadModal);
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

    // Temporary chat
    if (tempChatBtn) {
        tempChatBtn.addEventListener('click', createTempChat);
    }

    // Sidebar collapse
    if (sidebarCollapseBtn) {
        sidebarCollapseBtn.addEventListener('click', (event) => {
            event.preventDefault();
            toggleSidebar();
        });
    }

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

    if (chatContainer) {
        chatContainer.addEventListener('scroll', updateScrollState, { passive: true });
    }
    if (messagesDiv) {
        messagesDiv.addEventListener('click', (e) => {
            const btn = e.target.closest('.code-copy-btn');
            if (!btn) return;
            e.preventDefault();
            handleCopyCode(btn);
        });
    }
    if (scrollBottomBtn) {
        scrollBottomBtn.addEventListener('click', () => scrollToBottom(true, 'smooth'));
    }
    updateScrollState();

    // Settings modal
    openSettingsBtn.addEventListener('click', openSettingsModal);
    closeSettingsBtn.addEventListener('click', closeSettingsModal);
    settingsModal.addEventListener('click', (e) => {
        if (e.target === settingsModal) closeSettingsModal();
    });

    // Close confirmation modal (Tauri only)
    if (closeConfirmCloseBtn) {
        closeConfirmCloseBtn.addEventListener('click', closeCloseConfirmModal);
    }
    if (closeConfirmModal) {
        closeConfirmModal.addEventListener('click', (e) => {
            if (e.target === closeConfirmModal) closeCloseConfirmModal();
        });
    }
    if (closeToTrayBtn) {
        closeToTrayBtn.addEventListener('click', () => handleCloseChoice('background'));
    }
    if (closeExitBtn) {
        closeExitBtn.addEventListener('click', () => handleCloseChoice('exit'));
    }

    // Download modal
    if (openDownloadBtn) {
        openDownloadBtn.addEventListener('click', openDownloadModal);
    }
    if (welcomeDownloadBtn) {
        welcomeDownloadBtn.addEventListener('click', openDownloadModal);
    }
    if (closeDownloadBtn) {
        closeDownloadBtn.addEventListener('click', closeDownloadModal);
    }
    if (downloadModal) {
        downloadModal.addEventListener('click', (e) => {
            if (e.target === downloadModal) closeDownloadModal();
        });
    }
    if (downloadModelBtn) {
        downloadModelBtn.addEventListener('click', startDownload);
    }
    if (downloadModelInput) {
        downloadModelInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                startDownload();
            }
        });
        downloadModelInput.addEventListener('input', () => {
            setSelectedDownloadRepo(downloadModelInput.value.trim());
        });
    }
    if (downloadSearchInput) {
        downloadSearchInput.addEventListener('input', () => {
            renderDownloadCards(downloadSearchInput.value);
        });
    }
    if (downloadCards) {
        downloadCards.addEventListener('click', handleDownloadCardClick);
    }

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
    if (cancelDownloadBtn) {
        cancelDownloadBtn.addEventListener('click', cancelDownload);
    }

    localModelSelect.addEventListener('change', () => {
        updateSupportedSettingsForPath(localModelSelect.value);
        updateReloadRequirement();
    });

    if (deviceSelect) {
        deviceSelect.addEventListener('change', updateReloadRequirement);
    }

    if (modelSwitcherBtn) {
        modelSwitcherBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            renderModelSwitcherList();
            toggleModelSwitcher();
        });
    }
    if (modelSwitcherManage) {
        modelSwitcherManage.addEventListener('click', () => {
            closeModelSwitcher();
            openSettingsModal();
        });
    }
    document.addEventListener('click', (e) => {
        if (!modelSwitcher || !modelSwitcherMenu) return;
        if (!modelSwitcher.contains(e.target)) {
            closeModelSwitcher();
        }
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeModelSwitcher();
        }
    });

    // Settings tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = `tab-${btn.dataset.tab}`;
            const target = document.getElementById(targetId);
            if (!target) return;
            if (btn.classList.contains('active')) return;

            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('hidden');
                const isActive = content === target;
                content.classList.toggle('active', isActive);
                content.setAttribute('aria-hidden', isActive ? 'false' : 'true');
            });
        });
    });
}

function setupSettingsListeners() {
    // Slider value displays
    maxTokensInput.addEventListener('input', () => {
        maxTokensValue.textContent = maxTokensInput.value;
        scheduleUserConfigSave();
    });

    temperatureInput.addEventListener('input', () => {
        temperatureValue.textContent = temperatureInput.value;
        scheduleUserConfigSave();
    });

    topPInput.addEventListener('input', () => {
        topPValue.textContent = topPInput.value;
        scheduleUserConfigSave();
    });

    topKInput.addEventListener('input', () => {
        topKValue.textContent = topKInput.value;
        scheduleUserConfigSave();
    });

    repPenaltyInput.addEventListener('input', () => {
        repPenaltyValue.textContent = repPenaltyInput.value;
        scheduleUserConfigSave();
    });

    historyTurnsInput.addEventListener('input', () => {
        historyTurnsValue.textContent = historyTurnsInput.value;
        scheduleUserConfigSave();
    });

    maxPromptLenInput.addEventListener('input', () => {
        applyMaxPromptLen(maxPromptLenInput.value, true);
    });

    if (npuPollIntervalInput && npuPollIntervalValue) {
        npuPollIntervalInput.addEventListener('input', () => {
            setNpuPollInterval(npuPollIntervalInput.value);
        });
    }
    if (autoLoadModelToggle) {
        autoLoadModelToggle.addEventListener('change', () => {
            setAutoLoadEnabled(autoLoadModelToggle.checked);
        });
    }
    if (closeBehaviorSelect) {
        closeBehaviorSelect.addEventListener('change', () => {
            setCloseBehavior(closeBehaviorSelect.value);
        });
    }

    systemPromptInput.addEventListener('input', () => {
        scheduleUserConfigSave();
    });

    doSampleInput.addEventListener('change', () => {
        scheduleUserConfigSave();
    });

    enableThinkingInput.addEventListener('change', () => {
        scheduleUserConfigSave();
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

// ============== Floating Panels ==============

const PERF_PANEL_VISIBLE_KEY = 'perf_panel_visible';
const PERF_PANEL_POS_KEY = 'perf_panel_pos';
const NPU_PANEL_POS_KEY = 'npu_panel_pos';

function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
}

function loadPanelPosition(key) {
    try {
        const raw = localStorage.getItem(key);
        if (!raw) return null;
        const data = JSON.parse(raw);
        if (!data || !Number.isFinite(data.left) || !Number.isFinite(data.top)) return null;
        return data;
    } catch (error) {
        return null;
    }
}

function savePanelPosition(key, left, top) {
    localStorage.setItem(key, JSON.stringify({ left, top }));
}

function applyPanelPosition(panel, key) {
    if (!panel) return;
    const pos = loadPanelPosition(key);
    if (!pos) return;
    const parent = panel.offsetParent || panel.parentElement;
    if (!parent) return;
    const panelWidth = panel.offsetWidth;
    const panelHeight = panel.offsetHeight;
    if (panelWidth === 0 || panelHeight === 0) return;
    const parentRect = parent.getBoundingClientRect();
    const maxLeft = Math.max(0, parentRect.width - panelWidth);
    const maxTop = Math.max(0, parentRect.height - panelHeight);
    const left = clamp(pos.left, 0, maxLeft);
    const top = clamp(pos.top, 0, maxTop);
    panel.style.left = `${left}px`;
    panel.style.top = `${top}px`;
    panel.style.right = 'auto';
    panel.style.bottom = 'auto';
}

function initDraggablePanel(panel, handle, key) {
    if (!panel || !handle) return;
    const parent = panel.offsetParent || panel.parentElement || document.body;

    const refreshPosition = () => applyPanelPosition(panel, key);
    requestAnimationFrame(refreshPosition);
    window.addEventListener('resize', refreshPosition);

    handle.addEventListener('pointerdown', (event) => {
        if (event.button !== 0) return;
        if (event.target.closest('button, a, input, select, textarea')) return;

        const panelRect = panel.getBoundingClientRect();
        const parentRect = parent.getBoundingClientRect();
        const startX = event.clientX;
        const startY = event.clientY;
        const startLeft = panelRect.left - parentRect.left;
        const startTop = panelRect.top - parentRect.top;

        const onMove = (moveEvent) => {
            const panelWidth = panel.offsetWidth;
            const panelHeight = panel.offsetHeight;
            const maxLeft = Math.max(0, parentRect.width - panelWidth);
            const maxTop = Math.max(0, parentRect.height - panelHeight);
            const left = clamp(startLeft + (moveEvent.clientX - startX), 0, maxLeft);
            const top = clamp(startTop + (moveEvent.clientY - startY), 0, maxTop);
            panel.style.left = `${left}px`;
            panel.style.top = `${top}px`;
            panel.style.right = 'auto';
            panel.style.bottom = 'auto';
            savePanelPosition(key, left, top);
        };

        const onUp = () => {
            window.removeEventListener('pointermove', onMove);
            window.removeEventListener('pointerup', onUp);
        };

        window.addEventListener('pointermove', onMove);
        window.addEventListener('pointerup', onUp, { once: true });
    });
}

function setPerformancePanelVisible(visible) {
    if (!performancePanel) return;
    if (visible) {
        showAnimated(performancePanel);
    } else {
        hideAnimated(performancePanel);
    }
    if (performancePanelToggleBtn) {
        performancePanelToggleBtn.classList.toggle('active', visible);
    }
    localStorage.setItem(PERF_PANEL_VISIBLE_KEY, visible ? '1' : '0');
    if (visible) {
        requestAnimationFrame(() => applyPanelPosition(performancePanel, PERF_PANEL_POS_KEY));
    }
}

function initPerformancePanel() {
    if (!performancePanel) return;
    const stored = localStorage.getItem(PERF_PANEL_VISIBLE_KEY);
    const visible = stored !== '0';
    setPerformancePanelVisible(visible);
    initDraggablePanel(performancePanel, performancePanelHandle, PERF_PANEL_POS_KEY);
    if (performancePanelToggleBtn) {
        performancePanelToggleBtn.addEventListener('click', () => {
            const next = !performancePanel.classList.contains('ui-open');
            setPerformancePanelVisible(next);
        });
    }
    if (performancePanelCloseBtn) {
        performancePanelCloseBtn.addEventListener('click', () => setPerformancePanelVisible(false));
    }
}

// ============== NPU Monitor ==============

const npuMonitorBtn = document.getElementById('npuMonitorBtn');
const npuMonitorPanel = document.getElementById('npuMonitorPanel');
const closeNpuMonitorBtn = document.getElementById('closeNpuMonitorBtn');
const npuMonitorHeader = document.getElementById('npuMonitorHeader');
const npuUtilText = document.getElementById('npuUtilText');
const npuCurrentValue = document.getElementById('npuCurrentValue');
const npuChart = document.getElementById('npuChart');
const npuStatus = document.getElementById('npuStatus');

let npuMonitorActive = false;
let npuPollInterval = null;
let npuChartCtx = null;
let npuPollIntervalMs = DEFAULT_NPU_POLL_MS;

function initNpuMonitor() {
    npuMonitorBtn.addEventListener('click', toggleNpuMonitor);
    closeNpuMonitorBtn.addEventListener('click', () => {
        hideAnimated(npuMonitorPanel);
    });

    if (npuChart) {
        npuChartCtx = npuChart.getContext('2d');
    }

    initDraggablePanel(npuMonitorPanel, npuMonitorHeader, NPU_PANEL_POS_KEY);
    startNpuMonitor();
}

async function toggleNpuMonitor() {
    if (npuMonitorPanel.classList.contains('ui-open')) {
        hideAnimated(npuMonitorPanel);
    } else {
        showAnimated(npuMonitorPanel);
        requestAnimationFrame(() => applyPanelPosition(npuMonitorPanel, NPU_PANEL_POS_KEY));
        await startNpuMonitor();
    }
}

async function startNpuMonitor() {
    if (npuMonitorActive) return;

    try {
        const response = await fetch(`${API_BASE}/api/npu/start`, { method: 'POST' });
        const data = await response.json();
        const searching = !!data.searching;

        if (data.available || searching) {
            npuMonitorActive = true;
            npuStatus.textContent = searching
                ? (t('npu_monitor_searching') || 'Searching...')
                : (t('npu_monitor_active') || 'Monitoring active');
            npuPollInterval = setInterval(pollNpuStatus, npuPollIntervalMs);
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

        if (data.searching && !data.available) {
            npuStatus.textContent = t('npu_monitor_searching') || 'Searching...';
            npuUtilText.textContent = '--';
            npuCurrentValue.textContent = '--';
            return;
        }

        if (!data.available) {
            npuStatus.textContent = t('npu_monitor_unavailable') || 'NPU monitoring not available on this system';
            npuUtilText.textContent = 'N/A';
            npuCurrentValue.textContent = 'N/A';
            stopNpuMonitor();
            return;
        }

        npuStatus.textContent = t('npu_monitor_active') || 'Monitoring active';
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
