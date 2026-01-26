const showBtn = document.getElementById('trayShow');
const quitBtn = document.getElementById('trayQuit');

let i18nData = {};
let currentLang = null;
let loadToken = 0;

async function fetchLang() {
    try {
        const response = await fetch('/api/lang');
        if (response.ok) {
            const data = await response.json();
            if (data && data.lang) {
                return data.lang;
            }
        }
    } catch (error) {
        // Ignore and fall back
    }
    return localStorage.getItem('lang') || 'en_US';
}

function t(key) {
    return i18nData[key] || key;
}

async function loadI18n() {
    const token = ++loadToken;
    try {
        const lang = await fetchLang();
        if (token !== loadToken) return;
        if (currentLang === lang && Object.keys(i18nData).length > 0) {
            applyI18n();
            syncTrayLabels();
            return;
        }
        const response = await fetch(`/api/i18n/${lang}`);
        if (!response.ok) {
            throw new Error('i18n fetch failed');
        }
        const data = await response.json();
        if (token !== loadToken) return;
        i18nData = data;
        currentLang = lang;
        applyI18n();
        syncTrayLabels();
    } catch (error) {
        // Ignore, keep fallback labels
    }
}

function applyI18n() {
    if (showBtn) showBtn.textContent = t('tray_show');
    if (quitBtn) quitBtn.textContent = t('tray_quit');
}

function applyPayloadLabels(payload) {
    if (showBtn && payload.show_label) showBtn.textContent = payload.show_label;
    if (quitBtn && payload.quit_label) quitBtn.textContent = payload.quit_label;
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

function getTauriEvent() {
    const tauri = window.__TAURI__;
    if (tauri && tauri.event && typeof tauri.event.listen === 'function') {
        return tauri.event;
    }
    const internals = window.__TAURI_INTERNALS__;
    if (internals && internals.event && typeof internals.event.listen === 'function') {
        return internals.event;
    }
    return null;
}

function syncTrayLabels() {
    const invoke = getTauriInvoke();
    if (!invoke) return;
    invoke('update_tray_labels', {
        show_label: t('tray_show'),
        quit_label: t('tray_quit')
    }).catch(() => {});
}

function hideTrayMenu() {
    const invoke = getTauriInvoke();
    if (!invoke) return;
    invoke('hide_tray_menu').catch(() => {});
}

function showMainWindow() {
    const invoke = getTauriInvoke();
    if (!invoke) return;
    invoke('show_main_window_cmd').catch(() => {});
}

function exitApp() {
    const invoke = getTauriInvoke();
    if (!invoke) return;
    invoke('exit_app').catch(() => {});
}

if (showBtn) {
    showBtn.addEventListener('click', () => {
        showMainWindow();
        hideTrayMenu();
    });
}

if (quitBtn) {
    quitBtn.addEventListener('click', () => {
        exitApp();
    });
}

window.addEventListener('blur', () => {
    hideTrayMenu();
});

window.addEventListener('focus', () => {
    loadI18n();
});

window.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
        hideTrayMenu();
    }
});

window.addEventListener('storage', (event) => {
    if (event.key === 'lang') {
        loadI18n();
    }
});

const eventApi = getTauriEvent();
if (eventApi) {
    eventApi.listen('tray-labels-updated', (event) => {
        const payload = event.payload || {};
        const expectedShow = i18nData.tray_show;
        const expectedQuit = i18nData.tray_quit;
        if (expectedShow || expectedQuit) {
            const showMatch = !expectedShow || payload.show_label === expectedShow;
            const quitMatch = !expectedQuit || payload.quit_label === expectedQuit;
            if (!showMatch || !quitMatch) {
                loadI18n();
                return;
            }
        }
        applyPayloadLabels(payload);
    });
}

loadI18n();
