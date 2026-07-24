/**
 * WorkspaceManager — Persistent state per workspace.
 * Saves/restore scroll position, filters, selected items, and custom state.
 */
class WorkspaceManager {
    constructor() {
        this._state = {};
        this._current = null;
        this._onSwitch = null;
    }

    saveState(workspaceId, state) {
        this._state[workspaceId] = { ...this._state[workspaceId], ...state };
        this._persist();
    }

    getState(workspaceId) {
        return this._state[workspaceId] || {};
    }

    switchTo(workspaceId) {
        const prev = this._current;
        this._current = workspaceId;

        if (prev && prev !== workspaceId) {
            this._saveSnapshot(prev);
        }

        this._restoreSnapshot(workspaceId);

        if (this._onSwitch) {
            this._onSwitch(workspaceId, prev);
        }
    }

    getCurrent() {
        return this._current;
    }

    onSwitch(callback) {
        this._onSwitch = callback;
    }

    _saveSnapshot(workspaceId) {
        const el = document.getElementById(`${workspaceId}-container`);
        if (!el) return;

        const scrollable = el.querySelector('.workspace-content, .chat-messages, [class*="list"]');
        this.saveState(workspaceId, {
            scrollTop: scrollable ? scrollable.scrollTop : 0,
            timestamp: Date.now()
        });
    }

    _restoreSnapshot(workspaceId) {
        const state = this.getState(workspaceId);
        const el = document.getElementById(`${workspaceId}-container`);
        if (!el || !state.scrollTop) return;

        requestAnimationFrame(() => {
            const scrollable = el.querySelector('.workspace-content, .chat-messages, [class*="list"]');
            if (scrollable) {
                scrollable.scrollTop = state.scrollTop;
            }
        });
    }

    _persist() {
        try {
            const data = JSON.stringify(this._state);
            sessionStorage.setItem('jarvis_workspaces', data);
        } catch (_) {}
    }

    _hydrate() {
        try {
            const data = sessionStorage.getItem('jarvis_workspaces');
            if (data) {
                this._state = JSON.parse(data);
            }
        } catch (_) {}
    }
}

window.WorkspaceManager = WorkspaceManager;