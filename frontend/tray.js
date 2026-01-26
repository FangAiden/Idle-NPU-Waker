const showBtn = document.getElementById('trayShow');
const quitBtn = document.getElementById('trayQuit');

let i18nData = {};

function getLang() {
    return localStorage.getItem('lang') || 'en_US';
}

function t(key) {
    return i18nData[key] || key;
}

async function loadI18n() {
    try {
        const lang = getLang();
        const response = await fetch(`/api/i18n/${lang}`);
        if (!response.ok) {
            throw new Error('i18n fetch failed');
        }
        i18nData = await response.json();
        applyI18n();
    } catch (error) {
        // Ignore, keep fallback labels
    }
}

function applyI18n() {
    if (showBtn) showBtn.textContent = t('tray_show');
    if (quitBtn) quitBtn.textContent = t('tray_quit');
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
        if (payload.show_label) showBtn.textContent = payload.show_label;
        if (payload.quit_label) quitBtn.textContent = payload.quit_label;
    });
}

loadI18n();
