/**
 * JARVIS v5.0.0 - OS Integration Module
 * System-level control and awareness
 */

const JARVIS_OS = {
    initialized: false,
    status: null,
    pollInterval: null,

    async init() {
        try {
            const resp = await fetch('/api/os/status');
            if (resp.ok) {
                this.status = await resp.json();
                this.initialized = true;
                this.startPolling();
            }
        } catch (e) {
            console.warn('OS integration not available:', e);
        }
    },

    startPolling() {
        this.pollInterval = setInterval(() => this.refreshStatus(), 5000);
    },

    async refreshStatus() {
        try {
            const resp = await fetch('/api/os/status');
            if (resp.ok) {
                this.status = await resp.json();
                this.updateUI();
            }
        } catch (e) {
            // Silent fail
        }
    },

    updateUI() {
        // Update OS status indicators
        const statusEl = document.getElementById('os-status');
        if (statusEl && this.status) {
            statusEl.textContent = this.status.initialized ? 'Online' : 'Offline';
            statusEl.style.color = this.status.initialized ? 'var(--success)' : 'var(--text-tertiary)';
        }
    },

    // ── Notifications ──────────────────────────────────

    async notify(title, message, subtitle = null, sound = true) {
        const resp = await fetch('/api/os/notify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, message, subtitle, sound }),
        });
        return await resp.json();
    },

    // ── Clipboard ─────────────────────────────────────

    async readClipboard() {
        const resp = await fetch('/api/os/clipboard');
        return await resp.json();
    },

    async writeClipboard(text) {
        const resp = await fetch('/api/os/clipboard', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text }),
        });
        return await resp.json();
    },

    async clearClipboard() {
        const resp = await fetch('/api/os/clipboard', { method: 'DELETE' });
        return await resp.json();
    },

    async clipboardHistory() {
        const resp = await fetch('/api/os/clipboard/history');
        return await resp.json();
    },

    // ── Hotkeys ───────────────────────────────────────

    async listHotkeys() {
        const resp = await fetch('/api/os/hotkeys');
        return await resp.json();
    },

    async registerHotkey(shortcut, action, description = '') {
        const resp = await fetch('/api/os/hotkeys', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ shortcut, action, description }),
        });
        return await resp.json();
    },

    async unregisterHotkey(action) {
        const resp = await fetch(`/api/os/hotkeys/${action}`, { method: 'DELETE' });
        return await resp.json();
    },

    // ── File Watcher ──────────────────────────────────

    async listWatched() {
        const resp = await fetch('/api/os/watcher');
        return await resp.json();
    },

    async watchDirectory(path, key = null, recursive = true) {
        const resp = await fetch('/api/os/watcher', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path, key, recursive }),
        });
        return await resp.json();
    },

    async unwatchDirectory(key) {
        const resp = await fetch(`/api/os/watcher/${key}`, { method: 'DELETE' });
        return await resp.json();
    },

    async fileEvents() {
        const resp = await fetch('/api/os/watcher/events');
        return await resp.json();
    },

    // ── System Info ───────────────────────────────────

    async getSystemInfo() {
        const resp = await fetch('/api/os/info');
        return await resp.json();
    },
};

// Initialize on load
if (typeof JARVIS !== 'undefined') {
    JARVIS.os = JARVIS_OS;
}
