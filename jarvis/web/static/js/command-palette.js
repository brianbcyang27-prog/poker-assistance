/**
 * CommandPalette — ⌘K Raycast-style command palette.
 * Fuzzy search across commands, workspaces, agents, and recent actions.
 */
class CommandPalette {
    constructor() {
        this.isOpen = false;
        this.query = '';
        this.selectedIndex = 0;
        this.commands = this._buildCommands();
        this.filtered = [...this.commands];
        this._overlay = null;
        this._input = null;
        this._results = null;
    }

    _buildCommands() {
        return [
            { id: 'home', label: 'Go to Home', category: 'Navigate', icon: '🏠', action: () => switchWorkspace('home') },
            { id: 'chat', label: 'Go to Chat', category: 'Navigate', icon: '💬', action: () => switchWorkspace('chat') },
            { id: 'memory', label: 'Go to Memory', category: 'Navigate', icon: '🧠', action: () => switchWorkspace('memory') },
            { id: 'projects', label: 'Go to Projects', category: 'Navigate', icon: '📂', action: () => switchWorkspace('projects') },
            { id: 'computer', label: 'Go to Vision', category: 'Navigate', icon: '👁', action: () => switchWorkspace('computer') },
            { id: 'metrics', label: 'Go to Metrics', category: 'Navigate', icon: '📊', action: () => switchWorkspace('metrics') },
            { id: 'logs', label: 'Go to Logs', category: 'Navigate', icon: '📋', action: () => switchWorkspace('logs') },
            { id: 'settings', label: 'Open Settings', category: 'Navigate', icon: '⚙️', action: () => toggleSettings() },
            { id: 'new-chat', label: 'New Conversation', category: 'Chat', icon: '✨', action: () => { switchWorkspace('chat'); startNewChat(); } },
            { id: 'clear-chat', label: 'Clear Chat', category: 'Chat', icon: '🗑', action: () => { const el = document.getElementById('chat-messages'); if (el) el.innerHTML = ''; } },
            { id: 'voice-toggle', label: 'Toggle Voice', category: 'Tools', icon: '🎙', action: () => { const el = document.getElementById('voice-btn'); if (el) el.click(); } },
            { id: 'screen-capture', label: 'Screen Capture', category: 'Tools', icon: '🖥', action: () => { switchWorkspace('computer'); startVision('screen'); } },
            { id: 'camera', label: 'Camera Capture', category: 'Tools', icon: '📷', action: () => { switchWorkspace('computer'); startVision('camera'); } },
            { id: 'refresh-core', label: 'Refresh Neural Core', category: 'Tools', icon: '🔄', action: () => { if (goldenCore) { goldenCore.loadData(); goldenCore.start(); } } },
            { id: 'system-status', label: 'System Status', category: 'Info', icon: '💓', action: () => fetch('/api/health').then(r => r.json()).then(d => console.log('Health:', d)) },
            { id: 'keyboard', label: 'Keyboard Shortcuts', category: 'Info', icon: '⌨️', action: () => alert('⌘K: Command Palette\n⌘⇧D: Developer Mode\n⌘,: Settings\nEsc: Close overlay') },
        ];
    }

    open() {
        if (this.isOpen) return;
        this.isOpen = true;
        this.query = '';
        this.selectedIndex = 0;
        this.filtered = [...this.commands];
        this._render();
        if (this._input) this._input.focus();
    }

    close() {
        this.isOpen = false;
        if (this._overlay) {
            this._overlay.style.display = 'none';
        }
    }

    toggle() {
        this.isOpen ? this.close() : this.open();
    }

    _render() {
        if (!this._overlay) {
            this._overlay = document.getElementById('command-palette');
        }
        if (!this._overlay) return;

        this._overlay.style.display = 'flex';
        this._input = this._overlay.querySelector('#cmd-input');
        this._results = this._overlay.querySelector('#cmd-results');

        if (this._input) {
            this._input.value = this.query;
            this._input.oninput = (e) => {
                this.query = e.target.value;
                this._filter();
                this._renderResults();
            };
            this._input.onkeydown = (e) => this._handleKey(e);
        }

        this._renderResults();
    }

    _filter() {
        const q = this.query.toLowerCase().trim();
        if (!q) {
            this.filtered = [...this.commands];
        } else {
            this.filtered = this.commands.filter(cmd => {
                const text = `${cmd.label} ${cmd.category}`.toLowerCase();
                return text.includes(q);
            });
        }
        this.selectedIndex = 0;
    }

    _renderResults() {
        if (!this._results) return;

        if (this.filtered.length === 0) {
            this._results.innerHTML = `<div class="cmd-empty">No commands found</div>`;
            return;
        }

        const grouped = {};
        for (const cmd of this.filtered) {
            if (!grouped[cmd.category]) grouped[cmd.category] = [];
            grouped[cmd.category].push(cmd);
        }

        let html = '';
        let idx = 0;
        for (const [category, cmds] of Object.entries(grouped)) {
            html += `<div class="cmd-category">${category}</div>`;
            for (const cmd of cmds) {
                const selected = idx === this.selectedIndex ? ' selected' : '';
                html += `<div class="cmd-item${selected}" data-idx="${idx}" onclick="window._cmdPalette._select(${idx})">
                    <span class="cmd-icon">${cmd.icon}</span>
                    <span class="cmd-label">${cmd.label}</span>
                    <span class="cmd-shortcut">${cmd.category}</span>
                </div>`;
                idx++;
            }
        }

        this._results.innerHTML = html;
    }

    _handleKey(e) {
        if (e.key === 'Escape') {
            e.preventDefault();
            this.close();
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            this.selectedIndex = Math.min(this.selectedIndex + 1, this.filtered.length - 1);
            this._renderResults();
            this._scrollToSelected();
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            this.selectedIndex = Math.max(this.selectedIndex - 1, 0);
            this._renderResults();
            this._scrollToSelected();
        } else if (e.key === 'Enter') {
            e.preventDefault();
            this._select(this.selectedIndex);
        }
    }

    _select(idx) {
        const cmd = this.filtered[idx];
        if (!cmd) return;
        this.close();
        setTimeout(() => cmd.action(), 50);
    }

    _scrollToSelected() {
        const el = this._results?.querySelector('.cmd-item.selected');
        if (el) el.scrollIntoView({ block: 'nearest' });
    }
}

window.CommandPalette = CommandPalette;