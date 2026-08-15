/* JARVIS — Integrations Hub + Know-Me UI */
(function () {
    'use strict';

    var CATEGORY_ORDER = ['apple', 'messaging', 'productivity', 'dev', 'social'];
    var CATEGORY_META = {
        apple: { label: 'Apple', icon: '', color: '#a2aaad' },
        messaging: { label: 'Messaging', icon: '', color: '#34d399' },
        productivity: { label: 'Productivity', icon: '', color: '#f5a623' },
        dev: { label: 'Developer', icon: '', color: '#00d4ff' },
        social: { label: 'Social', icon: '', color: '#e1306c' },
    };
    var STATUS_META = {
        connected: { label: 'Connected', color: '#00d4ff' },
        configured: { label: 'Configured', color: '#7c8aa5' },
        needs_config: { label: 'Needs setup', color: '#f5a623' },
        available: { label: 'Available', color: '#34d399' },
        error: { label: 'Error', color: '#ff5f57' },
        coming_soon: { label: 'Coming soon', color: '#7c8aa5' },
    };
    var CONNECTOR_ICONS = {
        apple: '', google: '', line: '', telegram: '', whatsapp: '', github: '', notion: '', instagram: '',
    };
    var MEMORY_CATEGORIES = {
        preference: 'Preference', tool: 'Tools', workflow: 'Workflow', style: 'Style',
        goal: 'Goals', project: 'Projects', rule: 'Rules', bio: 'Bio', context: 'Context',
    };
    var LEGACY_CATEGORY_MAP = {
        bio: 'fact', preference: 'preference', style: 'preference', workflow: 'learning',
        tool: 'tool_usage', project: 'project_context', context: 'fact', goal: 'goal', rule: 'rule',
    };

    var expanded = {};
    var integrationsCache = null;
    var profileCache = null;

    /* ---------- helpers ---------- */

    function humanizeCategory(cat) {
        return MEMORY_CATEGORIES[cat] || String(cat || '').replace(/_/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); });
    }

    function esc(s) {
        return String(s === null || s === undefined ? '' : s).replace(/[&<>"']/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
    }

    function toast(msg) {
        if (window.showToast) { window.showToast(msg); return; }
        var t = document.getElementById('toast');
        if (t) { t.textContent = msg; t.classList.add('show'); setTimeout(function () { t.classList.remove('show'); }, 2500); }
    }

    async function api(url, opts) {
        opts = opts || {};
        var headers = { 'Content-Type': 'application/json' };
        if (opts.headers) Object.assign(headers, opts.headers);
        var res = await fetch(url, { headers: headers, method: opts.method || 'GET', body: opts.body });
        if (!res.ok) {
            var detail = 'HTTP ' + res.status;
            try { var j = await res.json(); detail = j.detail || j.error || detail; } catch (e) {}
            var err = new Error(detail);
            err.status = res.status;
            throw err;
        }
        return res.json();
    }

    function getJSON(resp, keys, fallback) {
        for (var i = 0; i < keys.length; i++) {
            var cur = resp;
            var ok = true;
            var parts = keys[i].split('.');
            for (var p = 0; p < parts.length; p++) {
                if (cur === null || cur === undefined || typeof cur !== 'object') { ok = false; break; }
                cur = cur[parts[p]];
            }
            if (ok && cur !== null && cur !== undefined) return cur;
        }
        return fallback;
    }

    function el(tag, attrs, children) {
        var node = document.createElement(tag);
        if (attrs) {
            Object.keys(attrs).forEach(function (k) {
                if (k === 'class') node.className = attrs[k];
                else if (k === 'html') node.innerHTML = attrs[k];
                else if (k === 'text') node.textContent = attrs[k];
                else if (k.slice(0, 2) === 'on') node.addEventListener(k.slice(2), attrs[k]);
                else node.setAttribute(k, attrs[k]);
            });
        }
        (children || []).forEach(function (c) { if (c) node.appendChild(c); });
        return node;
    }

    /* ---------- API endpoints ---------- */

    function endpoints() {
        return {
            integrations: '/api/integrations',
            config: function (id) { return '/api/integrations/' + id + '/config'; },
            test: function (id) { return '/api/integrations/' + id + '/test'; },
            disconnect: function (id) { return '/api/integrations/' + id + '/disconnect'; },
            action: function (id) { return '/api/integrations/' + id + '/action'; },
            completeness: '/api/profile/completeness',
            learn: '/api/profile/learn',
            onboard: '/api/profile/onboard',
            profile: '/api/profile',
            memList: '/api/memory/personal',
            memCreate: '/api/memory/personal',
            memDelete: function (cat, key) {
                return '/api/memory/personal/' + encodeURIComponent(cat) + '/' + encodeURIComponent(key);
            },
        };
    }

    /* ================================================================
     * INTEGRATIONS HUB
     * ================================================================ */

    async function loadIntegrations(force) {
        var root = document.getElementById('integrations-root');
        if (!root) return;
        if (!force && integrationsCache) { renderIntegrations(integrationsCache); return; }
        root.innerHTML = '<div class="integrations-loading"><span class="spinner"></span><span>Loading connectors…</span></div>';
        try {
            var data = await api(endpoints().integrations);
            var list = data.integrations || [];
            integrationsCache = list;
            renderIntegrations(list);
        } catch (e) {
            if (e.status === 404) {
                root.innerHTML = '<div class="integrations-unavailable">' +
                    '<div class="integrations-unavailable-icon"></div>' +
                    '<strong>Integrations hub is still warming up</strong>' +
                    '<span>Backend module not ready yet — check back in a moment.</span></div>';
            } else {
                root.innerHTML = '<div class="integrations-unavailable">' +
                    '<strong>Could not load integrations</strong><span>' + esc(e.message) + '</span></div>';
            }
        }
    }

    function renderIntegrations(list) {
        var root = document.getElementById('integrations-root');
        if (!root) return;
        root.innerHTML = '';
        var grouped = {};
        CATEGORY_ORDER.forEach(function (c) { grouped[c] = []; });
        list.forEach(function (conn) {
            var cat = CATEGORY_ORDER.indexOf(conn.category) >= 0 ? conn.category : 'dev';
            grouped[cat].push(conn);
        });

        CATEGORY_ORDER.forEach(function (cat) {
            var conns = grouped[cat] || [];
            if (!conns.length) return;
            var meta = CATEGORY_META[cat] || CATEGORY_META.dev;
            var section = el('div', { class: 'integration-section' }, [
                el('div', { class: 'integration-section-header' }, [
                    el('span', { class: 'integration-section-icon', style: 'color:' + meta.color, text: meta.icon }),
                    el('h4', { class: 'integration-section-title', text: meta.label }),
                    el('span', { class: 'integration-section-count', text: String(conns.length) }),
                ]),
            ]);
            conns.forEach(function (conn) { section.appendChild(connectorCard(conn)); });
            root.appendChild(section);
        });

        if (!list.length) {
            root.innerHTML = '<div class="integrations-unavailable"><strong>No connectors registered</strong></div>';
        }
    }

    function connectorCard(conn) {
        var status = STATUS_META[conn.status] || STATUS_META.available;
        var isOpen = !!expanded[conn.id];
        var card = el('div', { class: 'connector-card' + (isOpen ? ' open' : '') });

        var head = el('div', { class: 'connector-head', onclick: function () { toggleConnector(conn.id); } }, [
            el('div', { class: 'connector-icon', style: 'background:' + (CONNECTOR_ICONS[conn.id] ? '' : 'var(--color-surface-2)'), text: (CONNECTOR_ICONS[conn.id] || conn.name.slice(0, 1)) }),
            el('div', { class: 'connector-main' }, [
                el('div', { class: 'connector-name-row' }, [
                    el('span', { class: 'connector-name', text: conn.name }),
                    conn.coming_soon ? el('span', { class: 'connector-flag', text: 'Soon' })
                        : el('span', { class: 'connector-badge', style: 'color:' + status.color + ';border-color:' + status.color + '33;background:' + status.color + '1a', text: status.label }),
                ]),
                el('div', { class: 'connector-desc', text: conn.description || '' }),
                el('div', { class: 'connector-caps' },
                    (conn.capabilities || []).slice(0, 4).map(function (cap) {
                        return el('span', { class: 'connector-cap', text: cap });
                    })
                ),
            ]),
            el('span', { class: 'connector-chevron' + (isOpen ? ' open' : '') }, ''),
        ]);

        card.appendChild(head);
        if (isOpen) card.appendChild(connectorBody(conn));
        return card;
    }

    function toggleConnector(id) {
        expanded[id] = !expanded[id];
        loadIntegrations(true);
    }

    function connectorBody(conn) {
        var wrap = el('div', { class: 'connector-body' });

        if (conn.setup_guide && conn.needs_setup_guide) {
            wrap.appendChild(el('div', { class: 'connector-guide' }, [
                el('div', { class: 'connector-guide-title', text: 'How to connect' }),
                el('p', { class: 'connector-guide-text', text: conn.setup_guide }),
            ]));
        }

        var fields = (conn.config_fields || []).filter(function (f) { return !f.has_value; });
        if (fields.length) {
            var form = el('div', { class: 'connector-form' });
            fields.forEach(function (f) {
                var isSelect = f.type === 'select' && f.options && f.options.length;
                var label = el('label', { class: 'connector-field-label', text: f.label || f.key });
                var input;
                if (isSelect) {
                    input = el('select', { class: 'connector-input' });
                    f.options.forEach(function (opt) {
                        input.appendChild(el('option', { value: String(opt), text: String(opt) }));
                    });
                } else {
                    input = el('input', {
                        class: 'connector-input',
                        type: f.secret ? 'password' : (f.type === 'number' ? 'number' : 'text'),
                        placeholder: f.placeholder || (f.secret ? '••••••••••••' : ''),
                        'data-key': f.key,
                    });
                    if (f.help) {
                        var hint = el('span', { class: 'connector-field-hint', text: f.help });
                        form.appendChild(el('div', { class: 'connector-field' }, [label, input, hint]));
                        return;
                    }
                }
                form.appendChild(el('div', { class: 'connector-field' }, [label, input]));
            });
            var saveBtn = el('button', {
                class: 'btn-save connector-save',
                onclick: function () { saveConnectorConfig(conn.id); },
            }, [el('span', { text: 'Save & Connect' })]);
            form.appendChild(el('div', { class: 'connector-field connector-actions' }, [saveBtn]));
            wrap.appendChild(form);
        }

        var actions = el('div', { class: 'connector-actions' }, []);
        if (conn.status === 'connected' || conn.status === 'configured') {
            actions.appendChild(el('button', {
                class: 'btn-outline connector-btn',
                onclick: function () { testConnector(conn.id); },
            }, [el('span', { text: 'Test Connection' })]));
            actions.appendChild(el('button', {
                class: 'btn-danger-ghost connector-btn',
                onclick: function () { disconnectConnector(conn.id); },
            }, [el('span', { text: 'Disconnect' })]));
        }
        if (conn.status === 'error' && conn.error) {
            actions.appendChild(el('span', { class: 'connector-error', text: 'Last error: ' + conn.error }));
        }
        if (conn.id === 'apple' && (conn.status === 'connected' || conn.status === 'available')) {
            actions.appendChild(appleDemoBar());
        }
        wrap.appendChild(actions);
        return wrap;
    }

    function appleDemoBar() {
        var bar = el('div', { class: 'apple-demo' }, [
            el('div', { class: 'apple-demo-title', text: 'Try it live (reads your Mac)' }),
        ]);
        var row = el('div', { class: 'apple-demo-row' }, []);
        var demos = [
            { action: 'calendar_upcoming', label: 'Calendar' },
            { action: 'reminders_list', label: 'Reminders' },
            { action: 'mail_unread', label: 'Unread Mail' },
        ];
        demos.forEach(function (d) {
            row.appendChild(el('button', {
                class: 'connector-btn apple-demo-btn',
                onclick: function () { runAppleAction(d.action); },
            }, [el('span', { text: d.label })]));
        });
        var searchWrap = el('div', { class: 'apple-demo-search' }, [
            el('input', { class: 'connector-input', id: 'apple-contact-query', placeholder: 'Search contacts…' }),
            el('button', {
                class: 'btn-save',
                onclick: function () {
                    var q = document.getElementById('apple-contact-query');
                    runAppleAction('contacts_search', { query: q ? q.value : '' });
                },
            }, [el('span', { text: 'Search' })]),
        ]);
        row.appendChild(searchWrap);
        bar.appendChild(row);
        var out = el('pre', { class: 'apple-demo-output hidden' });
        bar.appendChild(out);
        return bar;
    }

    async function saveConnectorConfig(id) {
        var card = document.querySelector('.connector-card.open');
        var inputs = card ? card.querySelectorAll('.connector-input') : [];
        var config = {};
        inputs.forEach(function (inp) {
            if (!inp.dataset.key) return;
            if (inp.value.trim() === '' && inp.getAttribute('type') === 'password') return;
            config[inp.dataset.key] = inp.value.trim();
        });
        if (!Object.keys(config).length) { toast('Nothing to save — enter at least one field'); return; }
        try {
            await api(endpoints().config(id), { method: 'POST', body: JSON.stringify({ config: config }) });
            toast('Saved — testing connection…');
            await testConnector(id, true);
        } catch (e) {
            toast('Failed to save: ' + e.message);
        }
    }

    async function testConnector(id, silent) {
        try {
            var data = await api(endpoints().test(id), { method: 'POST', body: JSON.stringify({}) });
            integrationsCache = null;
            await loadIntegrations(true);
            toast(data.ok ? ('Connected: ' + (data.detail || 'ok')) : ('Test failed: ' + (data.detail || 'unknown')));
        } catch (e) {
            integrationsCache = null;
            await loadIntegrations(true);
            if (!silent) toast('Test error: ' + e.message);
        }
    }

    async function disconnectConnector(id) {
        try {
            await api(endpoints().disconnect(id), { method: 'POST', body: JSON.stringify({}) });
            integrationsCache = null;
            await loadIntegrations(true);
            toast('Disconnected');
        } catch (e) {
            toast('Failed to disconnect: ' + e.message);
        }
    }

    async function runAppleAction(action, params) {
        var out = document.querySelector('.apple-demo-output');
        if (out) { out.classList.remove('hidden'); out.textContent = 'Running ' + action + '…'; }
        try {
            var data = await api(endpoints().action('apple'), {
                method: 'POST',
                body: JSON.stringify({ action: action, params: params || {} }),
            });
            if (out) {
                out.textContent = data.ok
                    ? JSON.stringify(getJSON(data, ['result', 'data'], data.detail || data), null, 2)
                    : ('Error: ' + (data.detail || 'unknown'));
            }
        } catch (e) {
            if (out) out.textContent = 'Error: ' + e.message;
        }
    }

    /* ================================================================
     * KNOW ME — right sidebar panel
     * ================================================================ */

    async function loadKnowsYou() {
        var panel = document.getElementById('knows-you-panel');
        if (!panel) return;
        panel.innerHTML = '<div class="knows-you-loading"><span class="spinner"></span><span>Loading…</span></div>';

        var score = 0;
        var level = 'Getting to know you';
        var suggestions = [];
        var memories = [];
        try { score = getJSON(await api(endpoints().completeness), ['score', 'completeness', 'percent'], 0); } catch (e) {}
        try {
            var m = await api(endpoints().memList);
            memories = m.memories || m || [];
        } catch (e) { memories = []; }

        if (!score) score = Math.min(95, memories.length * 12 + (memories.length ? 10 : 0));
        if (score >= 80) level = 'Deeply known';
        else if (score >= 50) level = 'Getting to know you';
        else if (score >= 25) level = 'Early connection';
        else level = 'Let\u2019s connect';

        panel.innerHTML = '';
        var ring = el('div', { class: 'knows-ring-wrap' }, [svgRing(score)]);
        var info = el('div', { class: 'knows-info' }, [
            el('div', { class: 'knows-level', text: level }),
            el('div', { class: 'knows-count', text: memories.length + ' ' + (memories.length === 1 ? 'memory' : 'memories') }),
        ]);
        panel.appendChild(el('div', { class: 'knows-top' }, [ring, info]));

        var chips = el('div', { class: 'knows-chips' }, []);
        memories.slice(0, 4).forEach(function (mem) {
            var cat = humanizeCategory(mem.category);
            chips.appendChild(el('div', { class: 'knows-chip' }, [
                el('span', { class: 'knows-chip-cat', text: cat }),
                el('span', { class: 'knows-chip-val', text: mem.value || mem.key || '' }),
            ]));
        });
        if (memories.length) panel.appendChild(chips);

        var quick = el('div', { class: 'knows-quick' }, [
            el('input', { class: 'connector-input knows-input', id: 'knows-quick-input', placeholder: 'Tell JARVIS something…' }),
            el('select', { class: 'connector-input knows-select', id: 'knows-quick-cat' },
                Object.keys(MEMORY_CATEGORIES).map(function (c) {
                    return el('option', { value: c, text: MEMORY_CATEGORIES[c] });
                })
            ),
            el('button', { class: 'btn-save knows-save', onclick: quickLearn }, [el('span', { text: 'Remember' })]),
        ]);
        panel.appendChild(quick);

        var footer = el('div', { class: 'knows-footer' }, [
            el('button', {
                class: 'connector-btn',
                onclick: function () {
                    var overlay = document.getElementById('settings-overlay');
                    if (overlay && overlay.classList.contains('hidden')) {
                        if (window.toggleSettings) window.toggleSettings();
                    }
                    if (window.switchSettingsSection) window.switchSettingsSection('profile');
                },
            }, [el('span', { text: 'Open Profile' })]),
        ]);
        panel.appendChild(footer);
    }

    function svgRing(score) {
        var r = 26;
        var circ = 2 * Math.PI * r;
        var pct = Math.max(0, Math.min(100, score));
        var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('viewBox', '0 0 64 64');
        svg.setAttribute('class', 'knows-ring');
        var track = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        track.setAttribute('cx', '32'); track.setAttribute('cy', '32'); track.setAttribute('r', String(r));
        track.setAttribute('class', 'knows-ring-track');
        var bar = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        bar.setAttribute('cx', '32'); bar.setAttribute('cy', '32'); bar.setAttribute('r', String(r));
        bar.setAttribute('class', 'knows-ring-bar');
        bar.setAttribute('stroke-dasharray', String(circ));
        bar.setAttribute('stroke-dashoffset', String(circ * (1 - pct / 100)));
        bar.style.setProperty('--ring-pct', pct + '%');
        var text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', '32'); text.setAttribute('y', '37');
        text.setAttribute('class', 'knows-ring-text');
        text.textContent = Math.round(pct) + '%';
        svg.appendChild(track); svg.appendChild(bar); svg.appendChild(text);
        return svg;
    }

    async function quickLearn() {
        var input = document.getElementById('knows-quick-input');
        var catSel = document.getElementById('knows-quick-cat');
        var text = input ? input.value.trim() : '';
        if (!text) { toast('Type something first'); return; }
        var category = catSel ? catSel.value : 'context';
        try {
            await createMemory(category, text);
            toast('Noted — JARVIS will remember that');
            if (input) input.value = '';
            await Promise.all([loadKnowsYou(), loadProfileEditor()]);
        } catch (e) {
            toast('Could not save: ' + e.message);
        }
    }

    async function createMemory(category, content) {
        var key = content.split(/[\s,.:;!?]+/).slice(0, 6).join('_').toLowerCase().slice(0, 80) || 'note';
        try {
            return await api(endpoints().learn, {
                method: 'POST',
                body: JSON.stringify({ content: content, category: category, source: 'ui' }),
            });
        } catch (e) {
            if (e.status === 404) {
                var legacy = LEGACY_CATEGORY_MAP[category] || 'fact';
                return await api(endpoints().memCreate, {
                    method: 'POST',
                    body: JSON.stringify({
                        category: legacy, key: key, value: content, confidence: 0.9, remember_mode: 'always',
                    }),
                });
            }
            throw e;
        }
    }

    /* ================================================================
     * KNOW-ME ONBOARDING
     * ================================================================ */

    var knowMeStep = 0;

    function knowMeNextStep() {
        if (knowMeStep >= 2) { submitKnowMeOnboarding(); return; }
        knowMeStep++;
        renderKnowMeStep();
    }

    function knowMePrevStep() {
        if (knowMeStep <= 0) return;
        knowMeStep--;
        renderKnowMeStep();
    }

    function renderKnowMeStep() {
        document.querySelectorAll('.knowme-step').forEach(function (s) {
            s.classList.toggle('hidden', parseInt(s.dataset.step, 10) !== knowMeStep);
        });
        var bar = document.getElementById('knowme-progress-bar');
        if (bar) bar.style.width = ((knowMeStep + 1) / 3 * 100) + '%';
        var back = document.getElementById('knowme-back');
        var next = document.getElementById('knowme-next');
        if (back) back.style.visibility = knowMeStep === 0 ? 'hidden' : 'visible';
        if (next) {
            next.textContent = knowMeStep === 2 ? 'Finish' : 'Continue';
            if (knowMeStep === 2) next.style.display = 'none';
            else next.style.display = '';
        }
        var dots = document.getElementById('knowme-dots');
        if (dots) {
            dots.innerHTML = '';
            for (var i = 0; i < 3; i++) {
                dots.appendChild(el('span', { class: 'knowme-dot' + (i === knowMeStep ? ' active' : '') }));
            }
        }
        var done = document.getElementById('knowme-done');
        if (done) done.style.display = knowMeStep === 2 ? '' : 'none';
    }

    async function submitKnowMeOnboarding() {
        var name = (document.getElementById('knowme-name') || {}).value || '';
        var tz = (document.getElementById('knowme-timezone') || {}).value || '';
        var goal = (document.getElementById('knowme-goal') || {}).value || '';
        var notes = (document.getElementById('knowme-notes') || {}).value || '';
        var payload = { name: name, timezone: tz, goal: goal, notes: notes };
        try {
            await api(endpoints().onboard, { method: 'POST', body: JSON.stringify(payload) });
        } catch (e) {
            if (e.status === 404) {
                if (name) await createMemory('bio', 'My name is ' + name);
                if (tz) await createMemory('preference', 'My timezone is ' + tz);
                if (goal) await createMemory('goal', 'Currently building: ' + goal);
                if (notes) await createMemory('context', notes);
            } else {
                toast('Onboarding error: ' + e.message);
            }
        }
        localStorage.setItem('jarvis.knowme.onboarded', '1');
        document.getElementById('knowme-overlay').classList.add('hidden');
        toast('Welcome aboard — JARVIS knows you now');
        await Promise.all([loadKnowsYou(), loadProfileEditor()]);
    }

    function dismissKnowMeOnboarding() {
        localStorage.setItem('jarvis.knowme.onboarded', '1');
        document.getElementById('knowme-overlay').classList.add('hidden');
    }

    async function maybeShowKnowMeOnboarding() {
        if (localStorage.getItem('jarvis.knowme.onboarded')) return;
        var firstRun = document.getElementById('onboarding-overlay');
        if (firstRun && !firstRun.classList.contains('hidden')) return;
        var score = 0;
        var memories = [];
        try { score = getJSON(await api(endpoints().completeness), ['score', 'completeness', 'percent'], 0); } catch (e) {}
        if (!score) {
            try { var m = await api(endpoints().memList); memories = m.memories || m || []; } catch (e2) {}
            score = Math.min(95, memories.length * 12 + (memories.length ? 10 : 0));
        }
        if (score >= 25) return;
        setTimeout(function () {
            var overlay = document.getElementById('knowme-overlay');
            if (overlay && !localStorage.getItem('jarvis.knowme.onboarded')) {
                overlay.classList.remove('hidden');
                renderKnowMeStep();
            }
        }, 1500);
    }

    /* ================================================================
     * PROFILE EDITOR (settings)
     * ================================================================ */

    async function loadProfileEditor() {
        var root = document.getElementById('profile-root');
        if (!root) return;
        root.innerHTML = '<div class="integrations-loading"><span class="spinner"></span><span>Loading profile…</span></div>';

        var profile = {};
        var memories = [];
        var score = 0;
        try { profile = await api(endpoints().profile); } catch (e) {}
        try { var m = await api(endpoints().memList); memories = m.memories || m || []; } catch (e) {}
        try { score = getJSON(await api(endpoints().completeness), ['score', 'completeness', 'percent'], 0); } catch (e) {}

        var profileMap = {};
        if (profile && typeof profile === 'object') {
            Object.keys(profile).forEach(function (cat) {
                var inner = profile[cat];
                if (!inner || typeof inner !== 'object') return;
                Object.keys(inner).forEach(function (k) {
                    var v = inner[k];
                    if (v && typeof v === 'object') profileMap[cat + '.' + k] = v.value;
                    else profileMap[cat + '.' + k] = v;
                });
            });
        }
        if (!memories.length) memories = flattenProfileToMemories(profileMap);

        root.innerHTML = '';

        var completeness = el('div', { class: 'profile-completeness' }, [
            el('div', { class: 'profile-completeness-top' }, [
                el('span', { class: 'profile-completeness-label', text: 'How well JARVIS knows you' }),
                el('span', { class: 'profile-completeness-value', text: Math.round(score) + '%' }),
            ]),
            el('div', { class: 'profile-completeness-track' }, [
                el('div', { class: 'profile-completeness-bar', style: 'width:' + Math.round(score) + '%' }),
            ]),
        ]);
        root.appendChild(completeness);

        var quick = el('div', { class: 'profile-quick' }, [
            el('input', { class: 'connector-input', id: 'profile-quick-input', placeholder: 'Add a memory… e.g. I use VS Code daily' }),
            el('select', { class: 'connector-input', id: 'profile-quick-cat' },
                Object.keys(MEMORY_CATEGORIES).map(function (c) {
                    return el('option', { value: c, text: MEMORY_CATEGORIES[c] });
                })
            ),
            el('button', { class: 'btn-save', onclick: profileQuickLearn }, [el('span', { text: 'Add' })]),
        ]);
        root.appendChild(el('div', { class: 'profile-block' }, [
            el('h5', { class: 'profile-block-title', text: 'Add a memory' }),
            quick,
        ]));

        if (memories.length) {
            var list = el('div', { class: 'profile-memories' }, []);
            var cats = memories.reduce(function (acc, mem) {
                if (acc.indexOf(mem.category) < 0) acc.push(mem.category);
                return acc;
            }, []);
            cats.forEach(function (cat) {
                var items = memories.filter(function (mem) { return mem.category === cat; });
                if (!items.length) return;
                var catLabel = humanizeCategory(cat);
                var group = el('div', { class: 'profile-group' }, [
                    el('div', { class: 'profile-group-title', text: catLabel }),
                ]);
                items.forEach(function (mem) {
                    group.appendChild(profileMemoryRow(mem));
                });
                list.appendChild(group);
            });
            root.appendChild(el('div', { class: 'profile-block' }, [
                el('h5', { class: 'profile-block-title', text: 'Stored memories (' + memories.length + ')' }),
                list,
            ]));
        } else {
            root.appendChild(el('div', { class: 'integrations-unavailable' }, [
                el('strong', { text: 'No memories yet' }),
                el('span', { text: 'Add your first memory above, or use the Know-Me onboarding.' }),
            ]));
        }
    }

    function flattenProfileToMemories(profileMap) {
        var out = [];
        Object.keys(profileMap).forEach(function (k) {
            var parts = k.split('.');
            out.push({
                category: parts[0],
                key: parts.slice(1).join('.'),
                value: profileMap[k],
                confidence: 0.8,
                source: 'profile',
            });
        });
        return out;
    }

    function profileMemoryRow(mem) {
        return el('div', { class: 'profile-memory' }, [
            el('div', { class: 'profile-memory-main' }, [
                el('div', { class: 'profile-memory-key', text: mem.key || '' }),
                el('div', { class: 'profile-memory-value', text: mem.value || '' }),
                el('div', { class: 'profile-memory-meta', text: 'confidence ' + Math.round((mem.confidence || 0) * 100) + '%' + (mem.source ? ' · ' + mem.source : '') }),
            ]),
            el('button', {
                class: 'profile-memory-delete',
                title: 'Delete',
                onclick: function () { deleteMemory(mem); },
            }, [el('span', { text: '✕' })]),
        ]);
    }

    async function profileQuickLearn() {
        var input = document.getElementById('profile-quick-input');
        var catSel = document.getElementById('profile-quick-cat');
        var text = input ? input.value.trim() : '';
        if (!text) { toast('Type something first'); return; }
        var category = catSel ? catSel.value : 'context';
        try {
            await createMemory(category, text);
            toast('Saved');
            if (input) input.value = '';
            await loadProfileEditor();
        } catch (e) {
            toast('Could not save: ' + e.message);
        }
    }

    async function deleteMemory(mem) {
        try {
            await api(endpoints().memDelete(mem.category, mem.key), { method: 'DELETE' });
            toast('Forgotten');
            await Promise.all([loadProfileEditor(), loadKnowsYou()]);
        } catch (e) {
            toast('Could not delete: ' + e.message);
        }
    }

    /* ================================================================
     * INIT
     * ================================================================ */

    function init() {
        var orig = window.switchSettingsSection;
        if (typeof orig === 'function') {
            window.switchSettingsSection = function (section) {
                orig(section);
                if (section === 'integrations') loadIntegrations(false);
                if (section === 'profile') loadProfileEditor();
            };
        }

        var settingsOverlay = document.getElementById('settings-overlay');
        if (settingsOverlay) {
            settingsOverlay.addEventListener('click', function (e) {
                if (e.target === settingsOverlay) {
                    setTimeout(function () { loadKnowsYou(); }, 100);
                }
            });
        }

        loadKnowsYou();
        maybeShowKnowMeOnboarding();

        window.IntegrationsUI = {
            refreshHub: function () { loadIntegrations(true); },
            refreshKnowsYou: function () { loadKnowsYou(); },
            refreshProfile: function () { loadProfileEditor(); },
            refreshAll: function () {
                loadIntegrations(true);
                loadKnowsYou();
                loadProfileEditor();
            },
        };
    }

    window.knowMeNextStep = knowMeNextStep;
    window.knowMePrevStep = knowMePrevStep;
    window.submitKnowMeOnboarding = submitKnowMeOnboarding;
    window.dismissKnowMeOnboarding = dismissKnowMeOnboarding;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
