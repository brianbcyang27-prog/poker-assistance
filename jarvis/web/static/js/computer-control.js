/**
 * JARVIS Computer Control Panel
 * Full computer control via /api/computer/action + system APIs
 */
const CC = {
    _lastScreenshot: null,
    _termHistory: [],
    _termHistIdx: -1,

    /* ---- Core Action Dispatcher ---- */
    async action(name, params = {}) {
        const status = document.getElementById('cc-status');
        if (status) status.textContent = 'Running...';
        this.console(`> ${name} ${JSON.stringify(params)}`);
        try {
            const res = await fetch('/api/computer/action', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: name, params })
            });
            const data = await res.json();
            if (status) status.textContent = res.ok ? 'Ready' : 'Error';
            if (!res.ok) {
                this.console(`ERROR: ${data.detail || data.error || 'Action failed'}`, 'error');
            }
            return data;
        } catch (e) {
            if (status) status.textContent = 'Error';
            this.console(`ERROR: ${e.message}`, 'error');
            return null;
        }
    },

    /* ---- Console ---- */
    console(text, type = 'info') {
        const body = document.getElementById('cc-console-body');
        if (!body) return;
        const line = document.createElement('div');
        line.className = `cc-console-line ${type}`;
        const time = new Date().toLocaleTimeString('en-US', { hour12: false });
        line.innerHTML = `<span class="cc-console-time">${time}</span><span class="cc-console-text">${this._esc(text)}</span>`;
        body.appendChild(line);
        body.scrollTop = body.scrollHeight;
        while (body.children.length > 200) body.removeChild(body.firstChild);
    },
    clearConsole() {
        const body = document.getElementById('cc-console-body');
        if (body) body.innerHTML = '';
    },
    _esc(s) {
        const d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    },

    /* ---- Output Panel ---- */
    output(panel, data) {
        const el = document.getElementById(`cc-output-${panel}`);
        if (!el) return;
        if (typeof data === 'object') {
            el.innerHTML = `<pre>${this._esc(JSON.stringify(data, null, 2))}</pre>`;
        } else {
            el.innerHTML = `<pre>${this._esc(String(data))}</pre>`;
        }
    },

    /* ======== SCREENSHOT ======== */
    async captureScreen() {
        const data = await this.action('screen_capture');
        if (data && data.screenshot) {
            const vp = document.getElementById('cc-screenshot-viewport');
            if (vp) vp.innerHTML = `<img src="data:image/png;base64,${data.screenshot}" style="max-width:100%;border-radius:8px;">`;
            this._lastScreenshot = data.screenshot;
        }
        this.output('screenshot', data);
    },

    async analyzeScreen() {
        const data = await this.action('vision_analyze');
        if (data && data.analysis) {
            this.console(`Analysis: ${data.analysis}`);
        }
        this.output('screenshot', data);
    },

    async screenState() {
        const data = await this.action('screen_get_active_window');
        this.output('screenshot', data);
    },

    async listWindows() {
        const data = await this.action('screen_list_windows');
        if (data && data.windows) {
            const vp = document.getElementById('cc-screenshot-viewport');
            if (vp) {
                vp.innerHTML = data.windows.map(w =>
                    `<div class="cc-window-item" onclick="CC.openApp('${this._esc(w.name || w.title || '')}')">
                        <span class="cc-window-title">${this._esc(w.title || w.name || 'Unknown')}</span>
                        <span class="cc-window-app">${this._esc(w.app || '')}</span>
                    </div>`
                ).join('');
            }
        }
        this.output('screenshot', data);
    },

    /* ======== TERMINAL ======== */
    async runCommand() {
        const input = document.getElementById('cc-terminal-input');
        if (!input || !input.value.trim()) return;
        const cmd = input.value.trim();
        this._termHistory.push(cmd);
        this._termHistIdx = this._termHistory.length;
        input.value = '';

        const term = document.getElementById('cc-terminal-output');
        if (term) {
            term.innerHTML += `<div class="cc-term-line cc-term-cmd">$ ${this._esc(cmd)}</div>`;
        }

        const data = await this.action('shell_execute', { command: cmd });
        if (term && data) {
            const output = data.output || data.stdout || data.error || JSON.stringify(data);
            const cls = data.ok !== false ? 'cc-term-out' : 'cc-term-err';
            term.innerHTML += `<div class="cc-term-line ${cls}">${this._esc(output)}</div>`;
            term.scrollTop = term.scrollHeight;
        }
    },

    async runPython() {
        const code = prompt('Enter Python code to execute:');
        if (!code) return;
        const data = await this.action('run_python', { code });
        this.console(JSON.stringify(data));
    },

    /* ======== FILES ======== */
    async listFiles(path) {
        const p = path || document.getElementById('cc-file-path')?.value || '/';
        const data = await this.action('list_files', { path: p });
        const list = document.getElementById('cc-file-list');
        if (!list || !data) return;
        if (data.files) {
            list.innerHTML = data.files.map(f => {
                const isDir = f.is_dir || f.type === 'directory';
                const icon = isDir ? '📁' : '📄';
                const click = isDir ? `CC.listFiles('${this._esc(p + '/' + f.name)}')` : `CC.readAndShow('${this._esc(p + '/' + f.name)}')`;
                return `<div class="cc-file-item" onclick="${click}">
                    <span class="cc-file-icon">${icon}</span>
                    <span class="cc-file-name">${this._esc(f.name)}</span>
                    <span class="cc-file-size">${f.size || ''}</span>
                </div>`;
            }).join('');
        }
        this.output('screenshot', data);
    },

    async readAndShow(path) {
        const data = await this.action('read_file', { path });
        if (data && data.content) {
            document.getElementById('cc-file-content').value = data.content;
            document.getElementById('cc-file-path').value = path;
        }
        this.console(JSON.stringify(data));
    },

    async writeFile() {
        const path = document.getElementById('cc-file-path')?.value;
        const content = document.getElementById('cc-file-content')?.value;
        if (!path || content === undefined) return;
        const data = await this.action('write_file', { path, content });
        this.console(JSON.stringify(data));
    },

    async createFile() {
        const path = prompt('File path to create:');
        if (!path) return;
        const content = document.getElementById('cc-file-content')?.value || '';
        const data = await this.action('create_file', { path, content });
        this.console(JSON.stringify(data));
    },

    /* ======== KEYBOARD ======== */
    async typeText() {
        const text = document.getElementById('cc-type-text')?.value;
        if (!text) return;
        await this.action('type_text', { text });
    },

    async hotkey(keys) {
        await this.action('hotkey', { keys });
    },

    async pressKey(key) {
        await this.action('press_key', { key });
    },

    async customHotkey() {
        const keys = document.getElementById('cc-custom-hotkey')?.value;
        if (!keys) return;
        await this.hotkey(keys);
    },

    /* ======== MOUSE ======== */
    async mouseClick() {
        const x = parseInt(document.getElementById('cc-mouse-x')?.value);
        const y = parseInt(document.getElementById('cc-mouse-y')?.value);
        if (isNaN(x) || isNaN(y)) return;
        await this.action('mouse_click', { x, y });
    },

    async mouseMove() {
        const x = parseInt(document.getElementById('cc-mouse-x')?.value);
        const y = parseInt(document.getElementById('cc-mouse-y')?.value);
        if (isNaN(x) || isNaN(y)) return;
        await this.action('mouse_move', { x, y });
    },

    async scroll(direction) {
        const amount = parseInt(document.getElementById('cc-scroll-amount')?.value) || 3;
        await this.action('mouse_scroll', { direction, amount });
    },

    /* ======== BROWSER ======== */
    async browserNavigate() {
        const url = document.getElementById('cc-browser-url')?.value;
        if (!url) return;
        await this.action('browser_navigate', { url });
    },

    async browserBack() { await this.action('browser_navigate', { url: 'back' }); },
    async browserForward() { await this.action('browser_navigate', { url: 'forward' }); },
    async browserReload() { await this.action('browser_navigate', { url: 'reload' }); },

    async browserScreenshot() {
        const data = await this.action('browser_screenshot');
        if (data && data.screenshot) {
            const vp = document.getElementById('cc-browser-viewport');
            if (vp) vp.innerHTML = `<img src="data:image/png;base64,${data.screenshot}" style="max-width:100%;border-radius:8px;">`;
        }
    },

    async browserGetText() {
        const data = await this.action('browser_get_text');
        this.console(data?.text || JSON.stringify(data));
    },

    async browserClick() {
        const selector = prompt('CSS selector or text to click:');
        if (!selector) return;
        await this.action('browser_click', { selector });
    },

    async browserScroll() {
        const dir = prompt('Direction (up/down):', 'down');
        if (!dir) return;
        await this.action('browser_scroll', { direction: dir });
    },

    async browserEvaluate() {
        const code = prompt('JavaScript to evaluate:');
        if (!code) return;
        const data = await this.action('browser_evaluate', { code });
        this.console(JSON.stringify(data));
    },

    async webSearch() {
        const query = document.getElementById('cc-browser-search')?.value;
        if (!query) return;
        const data = await this.action('web_search', { query });
        this.console(JSON.stringify(data));
    },

    /* ======== ACCESSIBILITY ======== */
    async a11yTree() {
        const data = await this.action('accessibility_tree');
        const tree = document.getElementById('cc-a11y-tree');
        if (!tree || !data) return;
        if (data.elements) {
            tree.innerHTML = data.elements.slice(0, 100).map(e =>
                `<div class="cc-a11y-node" data-role="${this._esc(e.role || '')}" data-name="${this._esc(e.name || '')}">
                    <span class="cc-a11y-role">${this._esc(e.role || '?')}</span>
                    <span class="cc-a11y-name">${this._esc(e.name || e.title || '')}</span>
                    ${e.app ? `<span class="cc-a11y-app">${this._esc(e.app)}</span>` : ''}
                </div>`
            ).join('');
        }
        this.output('screenshot', data);
    },

    async a11ySummary() {
        const data = await this.action('accessibility_summary');
        this.console(JSON.stringify(data));
    },

    async a11yApps() {
        const data = await this.action('accessibility_apps');
        this.console(JSON.stringify(data));
    },

    async a11yFind() {
        const query = document.getElementById('cc-a11y-query')?.value;
        if (!query) return;
        const data = await this.action('accessibility_find', { query });
        this.console(JSON.stringify(data));
    },

    async a11yClick() {
        const query = document.getElementById('cc-a11y-query')?.value;
        if (!query) return;
        await this.action('accessibility_click', { query });
    },

    async a11yTypeInto() {
        const query = document.getElementById('cc-a11y-query')?.value;
        if (!query) return;
        const text = prompt('Text to type:');
        if (text === null) return;
        await this.action('accessibility_type_into', { query, text });
    },

    /* ======== APPS ======== */
    async openApp(name) {
        const appName = name || document.getElementById('cc-app-name')?.value;
        if (!appName) return;
        await this.action('open_app', { app_name: appName });
    },

    async closeApp() {
        const appName = document.getElementById('cc-app-name')?.value;
        if (!appName) return;
        await this.action('close_app', { app_name: appName });
    },

    /* ======== CLIPBOARD ======== */
    async clipboardRead() {
        const data = await this.action('clipboard_read');
        const el = document.getElementById('cc-clipboard-content');
        if (el && data) {
            el.innerHTML = `<pre style="white-space:pre-wrap;word-break:break-all;">${this._esc(data.content || data.text || JSON.stringify(data))}</pre>`;
        }
        this.console(JSON.stringify(data));
    },

    async clipboardWrite() {
        const text = document.getElementById('cc-clipboard-write')?.value;
        if (!text) return;
        await this.action('clipboard_write', { text });
    },

    async clipboardClear() {
        await this.action('clipboard_clear');
    },

    /* ======== OS ======== */
    async notify() {
        const text = document.getElementById('cc-notify-text')?.value;
        if (!text) return;
        await this.action('os_notify', { text, title: 'JARVIS' });
    },

    async systemInfo() {
        const data = await this.action('system_info');
        this.output('os', data);
    },

    /* ======== VISION ======== */
    async visionFind() {
        const query = document.getElementById('cc-vision-query')?.value;
        if (!query) return;
        const data = await this.action('vision_find', { query });
        this.output('vision', data);
    },

    async visionDescribe() {
        const data = await this.action('vision_describe');
        this.output('vision', data);
    },

    /* ======== AGENTS ======== */
    async refreshAgents() {
        const list = document.getElementById('cc-agents-list');
        if (!list) return;
        try {
            const res = await fetch('/api/agents');
            const data = await res.json();
            if (!data.kings) { list.innerHTML = '<p>No agents found</p>'; return; }

            let html = '';
            for (const [kingId, king] of Object.entries(data.kings)) {
                html += `<div class="cc-agent-card cc-agent-king">
                    <div class="cc-agent-header">
                        <span class="cc-agent-icon">${king.emoji || '👑'}</span>
                        <span class="cc-agent-name">${this._esc(king.title || kingId)}</span>
                        <span class="cc-agent-state">${king.state || 'idle'}</span>
                    </div>`;
                if (king.workers) {
                    html += '<div class="cc-agent-workers">';
                    for (const [workerId, worker] of Object.entries(king.workers)) {
                        html += `<div class="cc-agent-card cc-agent-worker">
                            <span class="cc-agent-icon">${worker.emoji || '⚡'}</span>
                            <span class="cc-agent-name">${this._esc(worker.title || workerId)}</span>
                            <span class="cc-agent-state">${worker.state || 'idle'}</span>
                            <span class="cc-agent-task">${this._esc(worker.current_task || '')}</span>
                        </div>`;
                    }
                    html += '</div>';
                }
                html += '</div>';
            }
            list.innerHTML = html;
        } catch (e) {
            list.innerHTML = `<p class="cc-error">Failed to load agents: ${e.message}</p>`;
        }
    },
};

/* ---- Panel Navigation ---- */
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.cc-nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.cc-nav-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const panel = btn.dataset.panel;
            document.querySelectorAll('.cc-panel').forEach(p => p.classList.remove('active'));
            const target = document.getElementById(`cc-panel-${panel}`);
            if (target) target.classList.add('active');
        });
    });

    /* ---- Terminal keyboard shortcuts ---- */
    const termInput = document.getElementById('cc-terminal-input');
    if (termInput) {
        termInput.addEventListener('keydown', e => {
            if (e.key === 'Enter') {
                e.preventDefault();
                CC.runCommand();
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                if (CC._termHistIdx > 0) {
                    CC._termHistIdx--;
                    termInput.value = CC._termHistory[CC._termHistIdx] || '';
                }
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                if (CC._termHistIdx < CC._termHistory.length - 1) {
                    CC._termHistIdx++;
                    termInput.value = CC._termHistory[CC._termHistIdx] || '';
                } else {
                    CC._termHistIdx = CC._termHistory.length;
                    termInput.value = '';
                }
            }
        });
    }
});
