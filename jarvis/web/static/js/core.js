(function () {
    'use strict';

    // ── bridges ───────────────────────────────────────────────────────

    function bridge() {
        return window.pywebview ? window.pywebview.api : null;
    }

    function quit() {
        var api = bridge();
        if (api && api.quit) {
            api.quit();
        } else {
            window.close();
        }
    }

    function openBrowser() {
        var api = bridge();
        if (api && api.open_browser) {
            api.open_browser();
        } else {
            window.open(window.location.href.replace('/core', ''), '_blank');
        }
    }

    function reportError(msg) {
        var api = bridge();
        if (api && api.report_error) {
            try { api.report_error(String(msg)); } catch (e) {}
        }
    }

    function reportReady(mode) {
        var api = bridge();
        if (!api || !api.core_ready) return;
        try {
            api.core_ready(JSON.stringify({
                mode: mode,
                state: window.goldenCore ? window.goldenCore.state : null,
                canvasCount: document.querySelectorAll('canvas').length,
                width: window.innerWidth,
                height: window.innerHeight
            }));
        } catch (e) {}
    }

    function apiFetch(url, opts) {
        return fetch(url, opts).then(function (r) {
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
        });
    }

    // ── boot sequence ─────────────────────────────────────────────────

    var PHASES = [
        { at: 0, label: 'INITIALIZING NEURAL CORE' },
        { at: 18, label: 'LOADING MODULES' },
        { at: 36, label: 'CONNECTING DATABASE' },
        { at: 52, label: 'PREPARING AGENTS' },
        { at: 70, label: 'CALIBRATING VOICE' },
        { at: 86, label: 'FINALIZING' }
    ];
    var BOOT_MS = 2600;

    var statusEl = document.getElementById('os-status');
    var barFill = document.getElementById('os-bar-fill');
    var pctEl = document.getElementById('os-pct');
    var loadingScreen = document.getElementById('loading-screen');

    function mountFallbackCore(container) {
        var canvas = document.createElement('canvas');
        container.appendChild(canvas);
        var ctx = canvas.getContext('2d');
        function resize() {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        }
        resize();
        window.addEventListener('resize', resize);

        var t = 0;
        function draw() {
            t += 0.016;
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            var cx = canvas.width / 2;
            var cy = canvas.height / 2;
            var R = Math.min(canvas.width, canvas.height) * 0.16;

            ctx.strokeStyle = 'rgba(255, 184, 0, 0.5)';
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.arc(cx, cy, R, 0, Math.PI * 2);
            ctx.stroke();

            var orbit = t * 0.6;
            ctx.fillStyle = '#ffb800';
            ctx.shadowColor = 'rgba(255, 184, 0, 0.9)';
            ctx.shadowBlur = 16;
            ctx.beginPath();
            ctx.arc(cx + Math.cos(orbit) * R, cy + Math.sin(orbit) * R, 3, 0, Math.PI * 2);
            ctx.fill();
            ctx.shadowBlur = 0;

            ctx.strokeStyle = 'rgba(255, 184, 0, 0.25)';
            ctx.beginPath();
            ctx.arc(cx, cy, R * 0.78, 0, Math.PI * 2);
            ctx.stroke();

            var pulse = 1 + Math.sin(t * 2) * 0.06;
            var g = ctx.createRadialGradient(cx, cy, 0, cx, cy, R * 0.55 * pulse);
            g.addColorStop(0, 'rgba(255, 184, 0, 0.95)');
            g.addColorStop(0.4, 'rgba(255, 184, 0, 0.35)');
            g.addColorStop(1, 'rgba(255, 184, 0, 0)');
            ctx.fillStyle = g;
            ctx.beginPath();
            ctx.arc(cx, cy, R * 0.55 * pulse, 0, Math.PI * 2);
            ctx.fill();

            for (var i = 0; i < 40; i++) {
                var pa = t * (0.1 + (i % 5) * 0.03) + i * 2.4;
                var pr = R * (1.6 + (i % 7) * 0.35);
                var px = cx + Math.cos(pa) * pr;
                var py = cy + Math.sin(pa) * pr * 0.6;
                var alpha = 0.15 + 0.25 * Math.sin(pa * 3 + i);
                ctx.fillStyle = 'rgba(255, 200, 80, ' + Math.max(0.05, alpha) + ')';
                ctx.beginPath();
                ctx.arc(px, py, 1.2, 0, Math.PI * 2);
                ctx.fill();
            }
            requestAnimationFrame(draw);
        }
        draw();
    }

    // ── sound engine ──────────────────────────────────────────────────

    var Sound = (function () {
        var ctx = null;
        var enabled = localStorage.getItem('jarvis.sound') !== 'off';

        function ensure() {
            if (!ctx) {
                try { ctx = new (window.AudioContext || window.webkitAudioContext)(); }
                catch (e) { ctx = null; }
            }
            if (ctx && ctx.state === 'suspended') ctx.resume();
            return ctx;
        }

        function tone(freq, start, dur, gain, type) {
            var c = ensure();
            if (!c) return;
            var osc = c.createOscillator();
            var g = c.createGain();
            osc.type = type || 'sine';
            osc.frequency.value = freq;
            var t0 = c.currentTime + start;
            g.gain.setValueAtTime(0, t0);
            g.gain.linearRampToValueAtTime(gain, t0 + 0.012);
            g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
            osc.connect(g);
            g.connect(c.destination);
            osc.start(t0);
            osc.stop(t0 + dur + 0.05);
        }

        return {
            enabled: function () { return enabled; },
            setEnabled: function (v) {
                enabled = v;
                localStorage.setItem('jarvis.sound', v ? 'on' : 'off');
            },
            chime: function (kind) {
                if (!enabled) return;
                if (kind === 'open') { tone(660, 0, 0.18, 0.05); tone(880, 0.09, 0.22, 0.05); }
                else if (kind === 'close') { tone(660, 0, 0.14, 0.04); tone(440, 0.07, 0.2, 0.04); }
                else if (kind === 'send') { tone(520, 0, 0.1, 0.04); }
                else if (kind === 'success') { tone(523, 0, 0.12, 0.05); tone(659, 0.08, 0.12, 0.05); tone(784, 0.16, 0.2, 0.05); }
                else if (kind === 'error') { tone(180, 0, 0.28, 0.06, 'sawtooth'); }
                else if (kind === 'listen') { tone(880, 0, 0.08, 0.04); tone(1100, 0.07, 0.1, 0.04); }
            }
        };
    })();

    // ── toast ─────────────────────────────────────────────────────────

    var toastEl = document.getElementById('desktop-toast');
    var toastTimer = null;
    function toast(msg) {
        toastEl.textContent = msg;
        toastEl.classList.add('show');
        clearTimeout(toastTimer);
        toastTimer = setTimeout(function () { toastEl.classList.remove('show'); }, 3200);
    }

    // ── markdown ──────────────────────────────────────────────────────

    function sanitizeDom(el) {
        el.querySelectorAll('script,iframe,object,embed,link,style').forEach(function (n) { n.remove(); });
        el.querySelectorAll('*').forEach(function (n) {
            ['onclick', 'onerror', 'onload', 'onmouseover', 'onmouseout'].forEach(function (a) { n.removeAttribute(a); });
        });
        return el;
    }

    function renderMarkdown(text) {
        if (!window.marked) {
            var p = document.createElement('p');
            p.textContent = text || '';
            return p;
        }
        var div = document.createElement('div');
        div.innerHTML = window.marked.parse(text || '');
        return sanitizeDom(div);
    }

    // ── command bar ───────────────────────────────────────────────────

    var CommandBar = (function () {
        var bar = document.getElementById('command-bar');
        var input = document.getElementById('command-input');
        var bubble = document.getElementById('command-bubble');
        var talk = document.getElementById('core-talk');
        var listening = false;

        function speak(text) {
            if (!Sound.enabled() || !text) return;
            var fd = new FormData();
            fd.append('text', text);
            fetch('/api/voice/generate', { method: 'POST', body: fd })
                .then(function (r) {
                    if (!r.ok) throw new Error('tts');
                    return r.blob();
                })
                .then(function (blob) {
                    var url = URL.createObjectURL(blob);
                    var a = new Audio(url);
                    a.play().catch(function () {});
                })
                .catch(function () {});
        }

        function setThinking(on) {
            var hudText = document.getElementById('core-status-text');
            if (window.goldenCore) {
                try { window.goldenCore.setState(on ? 'thinking' : 'listening'); } catch (e) {}
            }
            if (hudText) hudText.textContent = on ? 'PROCESSING' : 'READY — LISTENING';
            if (on) {
                bubble.classList.remove('hidden');
                bubble.innerHTML =
                    '<div class="command-thinking"><span class="dot"></span><span class="dot"></span>' +
                    '<span class="dot"></span>THINKING</div>';
            }
        }

        function surfaceIntent(text) {
            var t = text.toLowerCase();
            if (/(quit|exit|shut down|goodbye)/.test(t)) return { type: 'quit' };
            if (/(todo|task|today|schedule|agenda|reminder|calendar|mail|email|inbox)/.test(t)) return { type: 'todos' };
            if (/(document|report|research|doc|mission|artifact|read me|file)/.test(t)) return { type: 'docs' };
            if (/(world|webcam|camera|yolo|traffic)/.test(t)) return { type: 'world' };
            if (/(notebook|notes)/.test(t)) return { type: 'notebook' };
            if (/(roadmap|learning)/.test(t)) return { type: 'roadmap' };
            if (/(settings|integrations|install|github|repo|setup|config)/.test(t)) return { type: 'settings' };
            if (/(project|about|help|what can you do)/.test(t)) return { type: 'project' };
            return null;
        }

        function submit(text) {
            text = (text || '').trim();
            if (!text) return;
            Sound.chime('send');
            var intent = surfaceIntent(text);
            if (intent) {
                if (intent.type === 'quit') { quit(); return; }
                if (intent.type === 'todos') { TodosView.open(true); }
                else if (intent.type === 'settings') { SettingsView.open(); }
                else if (intent.type === 'world') { WorldMapView.open(); }
                else if (intent.type === 'notebook') { NotebookView.open(); }
                else if (intent.type === 'roadmap') { RoadmapView.open(); }
                else if (intent.type === 'project') { ProjectView.open(); }
                else { DocView.open(); }
                close();
                return;
            }
            setThinking(true);
            apiFetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            }).then(function (data) {
                var html = renderMarkdown(data.response || '');
                bubble.classList.remove('hidden');
                bubble.innerHTML = '';
                bubble.appendChild(html);
                speak((data.response || '').replace(/[#*`>_]/g, ''));
            }).catch(function (err) {
                setThinking(false);
                bubble.classList.remove('hidden');
                bubble.innerHTML = '<p style="color:rgba(255,120,120,0.9)">JARVIS could not reach the brain: ' + err.message + '</p>';
            });
        }

        function open(prefill) {
            bar.classList.remove('hidden');
            bar.classList.add('open');
            if (prefill) input.value = prefill;
            setTimeout(function () { input.focus(); }, 120);
        }

        function close() {
            bar.classList.remove('open');
            input.blur();
        }

        function isOpen() { return bar.classList.contains('open'); }

        var recorder = null;

        function startFallbackRecorder() {
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                toast('Voice capture unavailable in this window — typing works too');
                Sound.chime('error');
                return;
            }
            navigator.mediaDevices.getUserMedia({ audio: true }).then(function (stream) {
                var mime = 'audio/mp4';
                if (!window.MediaRecorder || !MediaRecorder.isTypeSupported(mime)) mime = '';
                var chunks = [];
                recorder = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
                recorder.ondataavailable = function (e) {
                    if (e.data && e.data.size) chunks.push(e.data);
                };
                recorder.onstop = function () {
                    stream.getTracks().forEach(function (t) { t.stop(); });
                    var type = mime || 'audio/webm';
                    var fd = new FormData();
                    fd.append('audio', new Blob(chunks, { type: type }), 'speech' + (mime === 'audio/mp4' ? '.m4a' : '.webm'));
                    toast('Transcribing...');
                    fetch('/api/voice/transcribe', { method: 'POST', body: fd })
                        .then(function (r) { return r.json(); })
                        .then(function (d) {
                            listening = false;
                            if (d.error) { toast(d.error); Sound.chime('error'); return; }
                            input.value = d.text || '';
                            toast('');
                            if (d.text) submit(d.text);
                        })
                        .catch(function () {
                            listening = false;
                            toast('Transcription failed — typing works too');
                            Sound.chime('error');
                        });
                };
                recorder.start();
                listening = true;
                Sound.chime('listen');
                toast('Listening...');
            }).catch(function () {
                toast('Microphone access denied — check mic permission');
                Sound.chime('error');
            });
        }

        function toggleMic() {
            if (listening) {
                if (recorder && recorder.state !== 'inactive') { recorder.stop(); }
                else { listening = false; }
                return;
            }
            var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SR) { startFallbackRecorder(); return; }
            listening = true;
            Sound.chime('listen');
            toast('Listening...');
            var rec = new SR();
            rec.lang = 'en-US';
            rec.interimResults = false;
            rec.maxAlternatives = 1;
            rec.onresult = function (e) {
                var said = e.results[0][0].transcript;
                input.value = said;
                listening = false;
                toast('');
            };
            rec.onerror = function () {
                listening = false;
                toast('Voice capture failed — typing works too');
            };
            rec.onend = function () { listening = false; };
            try { rec.start(); } catch (e) { listening = false; }
        }

        talk.addEventListener('click', function () { open(); });
        document.getElementById('command-send').addEventListener('click', function () {
            submit(input.value);
        });
        document.getElementById('command-mic').addEventListener('click', toggleMic);
        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') submit(input.value);
        });

        return { open: open, close: close, submit: submit, speak: speak, isOpen: isOpen, toggleMic: toggleMic };
    })();

    // ── today board ───────────────────────────────────────────────────

    var TodosView = (function () {
        var surface = document.getElementById('surface-todos');
        var groupsEl = document.getElementById('todos-groups');
        var summaryEl = document.getElementById('todos-summary');
        var feedbackInput = document.getElementById('todos-feedback');

        function speakSummary(summary) {
            var parts = [];
            if (summary.overdue) parts.push(summary.overdue + ' overdue');
            if (summary.today) parts.push(summary.today + ' due today');
            if (summary.upcoming) parts.push(summary.upcoming + ' coming up');
            if (summary.jarvis) parts.push(summary.jarvis + ' JARVIS missions active');
            if (summary.inbox) parts.push(summary.inbox + ' in your inbox');
            if (!parts.length) parts.push('all clear, nothing on the board');
            CommandBar.speak('You have ' + parts.join(', ') + '.');
        }

        function chip(sourceLabel) {
            var c = document.createElement('span');
            c.className = 'todo-chip';
            c.textContent = sourceLabel;
            return c;
        }

        function renderGroup(group, now) {
            var wrap = document.createElement('div');
            wrap.className = 'todos-group';
            var label = document.createElement('div');
            label.className = 'todos-group-label';
            label.textContent = group.label;
            wrap.appendChild(label);

            if (!group.items.length) {
                var empty = document.createElement('div');
                empty.className = 'todo-empty';
                empty.textContent = 'Nothing here';
                wrap.appendChild(empty);
                return wrap;
            }

            group.items.forEach(function (item, idx) {
                var row = document.createElement('div');
                row.className = 'todo-item';
                row.style.animationDelay = (idx * 0.04) + 's';

                var check = document.createElement('div');
                check.className = 'todo-check';
                check.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>';
                check.title = 'Mark done';

                var main = document.createElement('div');
                main.className = 'todo-main';
                var title = document.createElement('div');
                title.className = 'todo-title';
                title.textContent = item.title || '(untitled)';
                main.appendChild(title);

                var meta = document.createElement('div');
                meta.className = 'todo-meta';
                meta.appendChild(chip(item.source_label));
                if (item.when) {
                    var when = document.createElement('span');
                    when.className = 'todo-when';
                    when.textContent = item.when;
                    meta.appendChild(when);
                }
                if (item.source === 'jarvis' && item.workspace_id) {
                    var ws = document.createElement('span');
                    ws.className = 'todo-when';
                    ws.textContent = item.workspace_id;
                    meta.appendChild(ws);
                }
                main.appendChild(meta);

                var done = false;
                check.addEventListener('click', function () {
                    if (done) return;
                    done = true;
                    row.classList.add('done');
                    Sound.chime('success');
                    apiFetch('/api/desktop/todos/complete', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            source: item.source,
                            title: item.title,
                            action: item.action,
                            workspace_id: item.workspace_id,
                            task_id: item.task_id
                        })
                    }).then(function (res) {
                        if (!res.ok) throw new Error(res.reason || 'writeback failed');
                        setTimeout(function () { row.remove(); }, 450);
                    }).catch(function (err) {
                        done = false;
                        row.classList.remove('done');
                        toast('Could not complete: ' + err.message);
                        Sound.chime('error');
                    });
                });

                row.appendChild(check);
                row.appendChild(main);
                wrap.appendChild(row);
            });
            return wrap;
        }

        function render(data) {
            groupsEl.innerHTML = '';
            var summary = data.summary || {};
            summaryEl.textContent =
                (summary.overdue ? summary.overdue + ' OVERDUE · ' : '') +
                (summary.today ? summary.today + ' DUE TODAY · ' : '') +
                (summary.upcoming ? summary.upcoming + ' UPCOMING · ' : '') +
                (summary.jarvis ? summary.jarvis + ' JARVIS · ' : '') +
                (summary.inbox ? summary.inbox + ' INBOX' : '');

            var groups = data.groups || [];
            if (!groups.length) {
                var empty = document.createElement('div');
                empty.className = 'todo-empty';
                empty.textContent = 'Your board is clear — nothing due, nothing queued.';
                groupsEl.appendChild(empty);
                speakSummary(summary);
                return;
            }
            groups.forEach(function (g) {
                groupsEl.appendChild(renderGroup(g));
            });
            speakSummary(summary);
        }

        function open(withVoice) {
            SurfaceManager.open('todos');
            groupsEl.innerHTML = '<div class="todo-empty">GATHERING YOUR DAY...</div>';
            summaryEl.textContent = '';
            apiFetch('/api/desktop/todos/today')
                .then(render)
                .catch(function (err) {
                    groupsEl.innerHTML = '<div class="todo-empty">Board unavailable: ' + err.message + '</div>';
                    Sound.chime('error');
                });
        }

        document.getElementById('todos-close').addEventListener('click', function () {
            SurfaceManager.close('todos');
        });
        document.getElementById('todos-feedback-send').addEventListener('click', function () {
            var text = feedbackInput.value.trim();
            if (!text) return;
            apiFetch('/api/desktop/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ surface: 'todo', target: 'today', text: text })
            }).then(function () {
                feedbackInput.value = '';
                toast('JARVIS heard you — logged for the next pass');
                Sound.chime('success');
            }).catch(function () {
                toast('Could not send feedback');
                Sound.chime('error');
            });
        });

        return { open: open };
    })();

    // ── documents ─────────────────────────────────────────────────────

    var DocView = (function () {
        var surface = document.getElementById('surface-doc');
        var titleEl = document.getElementById('doc-title');
        var subEl = document.getElementById('doc-sub');
        var contentEl = document.getElementById('doc-content');
        var tocEl = document.getElementById('doc-toc');
        var backBtn = document.getElementById('doc-back');
        var feedbackInput = document.getElementById('doc-feedback-input');
        var toolbar = document.getElementById('selection-toolbar');
        var currentDoc = null;
        var currentMode = 'list';

        function setMode(mode) {
            currentMode = mode;
            backBtn.style.visibility = mode === 'reader' ? 'visible' : 'hidden';
            tocEl.classList.toggle('hidden', mode !== 'reader');
            feedbackInput.placeholder = mode === 'reader'
                ? 'Select text, or tell JARVIS what to change...'
                : 'Tell JARVIS what to change...';
        }

        function buildToc() {
            tocEl.innerHTML = '';
            var heads = contentEl.querySelectorAll('h1, h2, h3');
            if (!heads.length) {
                tocEl.classList.add('hidden');
                return;
            }
            tocEl.classList.remove('hidden');
            var label = document.createElement('div');
            label.className = 'doc-toc-label';
            label.textContent = 'CONTENTS';
            tocEl.appendChild(label);
            heads.forEach(function (h, i) {
                if (!h.id) h.id = 'sec-' + i;
                var a = document.createElement('a');
                a.textContent = h.textContent;
                a.style.paddingLeft = (8 + (h.tagName === 'H2' ? 10 : h.tagName === 'H3' ? 20 : 0)) + 'px';
                a.addEventListener('click', function () {
                    h.scrollIntoView({ behavior: 'smooth', block: 'start' });
                });
                tocEl.appendChild(a);
            });
        }

        function renderList(docs) {
            titleEl.textContent = 'JARVIS DOCUMENTS';
            subEl.textContent = docs.length ? docs.length + ' REPORTS AVAILABLE' : 'NO REPORTS YET';
            contentEl.innerHTML = '';
            setMode('list');
            if (!docs.length) {
                var empty = document.createElement('div');
                empty.className = 'todo-empty';
                empty.textContent = 'No documents yet. Ask JARVIS to research something.';
                contentEl.appendChild(empty);
                return;
            }
            docs.forEach(function (d, i) {
                var item = document.createElement('div');
                item.className = 'doc-list-item';
                item.style.animationDelay = (i * 0.05) + 's';

                var t = document.createElement('div');
                t.className = 'doc-list-title';
                t.textContent = d.title;
                item.appendChild(t);

                var meta = document.createElement('div');
                meta.className = 'doc-list-meta';
                var kind = document.createElement('span');
                kind.textContent = d.kind === 'workspace' ? 'MISSION REPORT' : 'RESEARCH REPORT';
                var date = document.createElement('span');
                date.textContent = (d.date || '').slice(0, 16).replace('T', ' ');
                meta.appendChild(kind);
                meta.appendChild(date);
                item.appendChild(meta);

                if (d.snippet) {
                    var sn = document.createElement('div');
                    sn.className = 'doc-list-snippet';
                    sn.textContent = d.snippet;
                    item.appendChild(sn);
                }

                item.addEventListener('click', function () { loadDetail(d.kind, d.id); });
                contentEl.appendChild(item);
            });
        }

        function loadDetail(kind, id) {
            currentDoc = { kind: kind, id: id };
            titleEl.textContent = 'LOADING DOCUMENT...';
            subEl.textContent = '';
            contentEl.innerHTML = '';
            setMode('reader');
            apiFetch('/api/desktop/documents/' + encodeURIComponent(kind) + '/' + encodeURIComponent(id))
                .then(function (d) {
                    currentDoc = { kind: d.kind, id: d.id };
                    titleEl.textContent = d.title;
                    subEl.textContent = (d.date || '').slice(0, 16).replace('T', ' ');
                    contentEl.innerHTML = '';
                    var node = renderMarkdown(d.content || '_No content yet._');
                    contentEl.appendChild(node);
                    buildToc();
                    contentEl.scrollTop = 0;
                })
                .catch(function (err) {
                    titleEl.textContent = 'DOCUMENT ERROR';
                    contentEl.innerHTML = '<div class="todo-empty">' + err.message + '</div>';
                    Sound.chime('error');
                });
        }

        function open() {
            SurfaceManager.open('doc');
            titleEl.textContent = 'JARVIS DOCUMENTS';
            subEl.textContent = 'FETCHING...';
            contentEl.innerHTML = '';
            setMode('list');
            apiFetch('/api/desktop/documents')
                .then(function (data) { renderList(data.documents || []); })
                .catch(function (err) {
                    contentEl.innerHTML = '<div class="todo-empty">Documents unavailable: ' + err.message + '</div>';
                    Sound.chime('error');
                });
        }

        document.getElementById('doc-close').addEventListener('click', function () {
            SurfaceManager.close('doc');
        });
        backBtn.addEventListener('click', open);

        document.getElementById('doc-feedback-send').addEventListener('click', function () {
            var text = feedbackInput.value.trim();
            if (!text) return;
            apiFetch('/api/desktop/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    surface: 'doc',
                    target: currentDoc ? currentDoc.kind + ':' + currentDoc.id : '',
                    text: text
                })
            }).then(function () {
                feedbackInput.value = '';
                toast('JARVIS heard you — feedback logged');
                Sound.chime('success');
            }).catch(function () {
                toast('Could not send feedback');
                Sound.chime('error');
            });
        });

        contentEl.addEventListener('mouseup', function () {
            var sel = window.getSelection();
            if (!sel || sel.isCollapsed || !sel.toString().trim()) {
                toolbar.classList.add('hidden');
                return;
            }
            var rect = sel.getRangeAt(0).getBoundingClientRect();
            toolbar.style.left = Math.min(rect.left + rect.width / 2 - 90, window.innerWidth - 200) + 'px';
            toolbar.style.top = Math.max(10, rect.top - 44) + 'px';
            toolbar.classList.remove('hidden');
        });
        document.addEventListener('mousedown', function (e) {
            if (!toolbar.contains(e.target)) toolbar.classList.add('hidden');
        });
        document.getElementById('sel-copy').addEventListener('click', function () {
            var sel = window.getSelection();
            if (sel && sel.toString()) {
                navigator.clipboard.writeText(sel.toString()).then(function () { toast('Copied'); });
            }
        });
        document.getElementById('sel-ask').addEventListener('click', function () {
            var sel = window.getSelection();
            var text = sel ? sel.toString().trim() : '';
            toolbar.classList.add('hidden');
            CommandBar.open('About "' + text.slice(0, 120) + '": ');
        });

        return { open: open, loadDetail: loadDetail };
    })();

    // ── settings / integrations ──────────────────────────────────────

    var SettingsView = (function () {
        var urlInput = document.getElementById('settings-url');
        var researchBtn = document.getElementById('settings-research');
        var report = document.getElementById('settings-report');
        var repoName = document.getElementById('settings-repo-name');
        var repoStats = document.getElementById('settings-repo-stats');
        var summaryEl = document.getElementById('settings-summary');
        var benefitsEl = document.getElementById('settings-benefits');
        var consEl = document.getElementById('settings-cons');
        var installHint = document.getElementById('settings-install-hint');
        var installBtn = document.getElementById('settings-install');
        var verdictEl = document.getElementById('settings-verdict');
        var installStatus = document.getElementById('settings-install-status');
        var historyEl = document.getElementById('settings-history');
        var currentUrl = null;
        var installed = false;

        function fillList(el, items) {
            el.innerHTML = '';
            (items || []).forEach(function (item) {
                var li = document.createElement('li');
                li.textContent = item;
                el.appendChild(li);
            });
        }

        function renderReport(data) {
            currentUrl = data.repo.url;
            repoName.textContent = data.repo.full_name;
            repoStats.textContent = [
                data.repo.language || 'unknown',
                data.repo.stars + ' stars',
                data.repo.license || 'no license',
                'pushed ' + (data.repo.pushed_at || '?').slice(0, 10)
            ].join(' · ');
            if (data.verdict) {
                var level = data.verdict.level || 'low';
                verdictEl.textContent = level.toUpperCase() + ' RISK';
                verdictEl.className = 'settings-verdict verdict-' + level;
                verdictEl.title = (data.verdict.factors || []).join('\n') || 'No risk factors flagged';
            } else {
                verdictEl.textContent = '';
                verdictEl.className = 'settings-verdict';
            }
            summaryEl.textContent = data.summary || '(no summary extracted)';
            fillList(benefitsEl, data.benefits);
            fillList(consEl, data.cons);
            installHint.textContent = data.install.command_hint;
            setInstalled(false);
            installStatus.textContent = '';
            installStatus.className = 'settings-install-status';
            report.classList.remove('hidden');
        }

        function setInstalled(value) {
            installed = value;
            installBtn.textContent = value ? 'REMOVE' : 'INSTALL';
            installBtn.className = value
                ? 'surface-footer-send settings-remove'
                : 'surface-footer-send';
            installBtn.disabled = false;
        }

        function research() {
            var url = urlInput.value.trim();
            if (!url) { toast('Paste a GitHub repo URL first'); Sound.chime('error'); return; }
            report.classList.add('hidden');
            toast('Investigating ' + url + '...');
            Sound.chime('listen');
            apiFetch('/api/integrations/research', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url })
            }).then(function (data) {
                renderReport(data);
                toast('Research complete — ' + data.source + ' analysis');
                Sound.chime('success');
                loadHistory();
            }).catch(function (err) {
                toast('Research failed: ' + err.message);
                Sound.chime('error');
            });
        }

        function install() {
            if (!currentUrl) return;
            if (installed) { uninstall(); return; }
            installBtn.disabled = true;
            installStatus.className = 'settings-install-status';
            installStatus.textContent = 'Installing... this can take a few minutes';
            apiFetch('/api/integrations/install', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: currentUrl })
            }).then(function (data) {
                setInstalled(true);
                installStatus.textContent = data.detail || (data.status + ' — ' + data.target);
                Sound.chime('success');
                loadHistory();
            }).catch(function (err) {
                installStatus.textContent = err.message;
                installStatus.className = 'settings-install-status error';
                Sound.chime('error');
                installBtn.disabled = false;
            });
        }

        function uninstall() {
            installBtn.disabled = true;
            installStatus.className = 'settings-install-status';
            installStatus.textContent = 'Removing...';
            apiFetch('/api/integrations/uninstall', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: currentUrl })
            }).then(function (data) {
                setInstalled(false);
                installStatus.textContent = data.detail || 'Removed';
                Sound.chime('success');
                loadHistory();
            }).catch(function (err) {
                installStatus.textContent = err.message;
                installStatus.className = 'settings-install-status error';
                Sound.chime('error');
                installBtn.disabled = false;
            });
        }

        function loadHistory() {
            apiFetch('/api/integrations/research/list').then(function (data) {
                historyEl.innerHTML = '';
                (data.repos || []).forEach(function (r) {
                    var row = document.createElement('div');
                    row.className = 'settings-history-item';
                    var name = document.createElement('span');
                    name.className = 'settings-history-name';
                    name.textContent = r.full_name;
                    var status = document.createElement('span');
                    status.className = 'settings-history-status' + (r.status === 'installed' ? ' installed' : '');
                    status.textContent = r.status.toUpperCase();
                    row.appendChild(name);
                    row.appendChild(status);
                    historyEl.appendChild(row);
                });
            }).catch(function () {});
        }

        function open() {
            SurfaceManager.open('settings');
            loadHistory();
            setTimeout(function () { urlInput.focus(); }, 150);
        }

        researchBtn.addEventListener('click', research);
        installBtn.addEventListener('click', install);
        urlInput.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') research();
        });
        document.getElementById('settings-close').addEventListener('click', function () {
            SurfaceManager.close('settings');
        });

        return { open: open };
    })();

    // ── surface manager ───────────────────────────────────────────────

    var SurfaceManager = (function () {
        var backdrop = document.getElementById('surface-backdrop');
        var stack = [];
        var surfaces = { todos: 'surface-todos', doc: 'surface-doc', settings: 'surface-settings',
                         world: 'surface-world', notebook: 'surface-notebook',
                         project: 'surface-project', roadmap: 'surface-roadmap' };
        var listeners = [];

        function emit() {
            for (var i = 0; i < listeners.length; i++) listeners[i](top());
        }

        function top() { return stack.length ? stack[stack.length - 1] : null; }

        function onChange(fn) { listeners.push(fn); }

        function open(name) {
            var el = document.getElementById(surfaces[name]);
            if (!el) return;
            if (stack.indexOf(name) === -1) stack.push(name);
            backdrop.classList.remove('hidden');
            el.classList.remove('hidden');
            requestAnimationFrame(function () {
                backdrop.classList.add('show');
                el.classList.add('open');
            });
            Sound.chime('open');
            emit();
        }

        function close(name) {
            var el = document.getElementById(surfaces[name]);
            if (!el) return;
            el.classList.remove('open');
            stack = stack.filter(function (s) { return s !== name; });
            Sound.chime('close');
            emit();
            setTimeout(function () {
                if (stack.length === 0) {
                    backdrop.classList.remove('show');
                    setTimeout(function () { backdrop.classList.add('hidden'); }, 350);
                }
                el.classList.add('hidden');
            }, 360);
        }

        function closeTop() {
            if (!stack.length) return false;
            close(stack[stack.length - 1]);
            return true;
        }

        backdrop.addEventListener('click', function () { closeTop(); });
        return { open: open, close: close, closeTop: closeTop, top: top, onChange: onChange };
    })();

    var DockView = (function () {
        var hotzone = document.getElementById('edge-hotzone');
        var dock = document.getElementById('edge-dock');
        var hideTimer = null;

        function isOpen() { return dock.classList.contains('dock-open'); }

        function open() {
            if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
            dock.classList.add('dock-open');
        }

        function close() {
            if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
            dock.classList.remove('dock-open');
        }

        function setActive(name) {
            var tabs = dock.querySelectorAll('.dock-tab');
            for (var i = 0; i < tabs.length; i++) {
                tabs[i].classList.toggle('active', tabs[i].getAttribute('data-surface') === name);
            }
        }

        hotzone.addEventListener('mouseenter', open);
        hotzone.addEventListener('mouseleave', function () {
            if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
            hideTimer = setTimeout(close, 350);
        });
        dock.addEventListener('mouseenter', function () {
            if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
        });
        dock.addEventListener('mouseleave', function () {
            if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
            hideTimer = setTimeout(close, 350);
        });

        var tabs = dock.querySelectorAll('.dock-tab');
        for (var i = 0; i < tabs.length; i++) {
            (function (tab) {
                tab.addEventListener('click', function () {
                    var name = tab.getAttribute('data-surface');
                    if (name) SurfaceManager.open(name);
                    close();
                });
            })(tabs[i]);
        }

        SurfaceManager.onChange(function (name) { setActive(name); });
        return { open: open, close: close, isOpen: isOpen, setActive: setActive };
    })();

    var WorldMapView = (function () {
        var gridEl = document.getElementById('wm-grid');
        var statusEl = document.getElementById('wm-status');
        var eventsEl = document.getElementById('wm-events');
        var notifyStatus = document.getElementById('wm-notify-status');
        var timer = null;

        function esc(s) {
            return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
                return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
            });
        }

        function renderStatus(s) {
            if (!s) { statusEl.innerHTML = '<span class="warn">CONNECTING…</span>'; return; }
            var n = s.notifications || {};
            var html = '<span class="' + (s.running ? 'ok' : 'warn') + '">' +
                (s.running ? '● MONITOR RUNNING' : '● MONITOR IDLE') + '</span>' +
                ' · yolo ' + (s.yolo_loaded ? '<span class="ok">loaded</span>' : '<span class="err">not loaded</span>') +
                ' · every ' + esc(s.interval) + 's' +
                ' · telegram ' + (n.telegram_configured ? '<span class="ok">on</span>' : '<span class="warn">off</span>') +
                ' · imessage ' + (n.imessage_configured ? '<span class="ok">on</span>' : '<span class="warn">off</span>');
            statusEl.innerHTML = html;
        }

        function renderSources(sources) {
            gridEl.innerHTML = '';
            if (!sources || !sources.length) {
                var empty = document.createElement('div');
                empty.className = 'wm-empty';
                empty.textContent = 'No sources yet — add one below.';
                gridEl.appendChild(empty);
                return;
            }
            sources.forEach(function (src) {
                var card = document.createElement('div');
                card.className = 'wm-card' + (src.enabled === false ? ' off' : '');
                var th = src.image_url
                    ? '<img class="wm-thumb" src="' + esc(src.image_url) + '" alt="" loading="lazy">'
                    : '<div class="wm-thumb-ph">NO IMAGE</div>';
                var thText = src.thresholds
                    ? 'p ' + esc(src.thresholds.persons) + ' · v ' + esc(src.thresholds.vehicles)
                    : '';
                card.innerHTML = th +
                    '<div class="wm-card-body">' +
                    '<div class="wm-card-name">' + esc(src.name) + '</div>' +
                    '<div class="wm-card-meta"><span class="wm-kind">' + esc(src.kind || 'cam') + '</span>' +
                    '<span>' + esc(src.location || '') + '</span></div>' +
                    '<div class="wm-card-row"><span class="wm-thresholds">' + thText + '</span>' +
                    '<button class="wm-toggle' + (src.enabled === false ? '' : ' on') + '" data-id="' + esc(src.id) + '">' +
                    (src.enabled === false ? 'OFF' : 'ON') + '</button></div></div>';
                gridEl.appendChild(card);
            });
        }

        function renderEvents(events) {
            eventsEl.innerHTML = '';
            if (!events || !events.length) {
                var empty = document.createElement('div');
                empty.className = 'wm-empty';
                empty.textContent = 'No events yet.';
                eventsEl.appendChild(empty);
                return;
            }
            events.forEach(function (ev) {
                var row = document.createElement('div');
                row.className = 'wm-event';
                row.innerHTML = '<div class="wm-event-head"><span>' +
                    esc(ev.source_name || ev.source_id || '') + ' — ' + esc(ev.kind || '') + '</span>' +
                    '<span class="wm-event-time">' + esc(ev.at || '') + '</span></div>' +
                    '<div class="wm-event-sum">' + esc(ev.summary || '') + '</div>';
                eventsEl.appendChild(row);
            });
        }

        function refresh() {
            apiFetch('/api/world/status').then(renderStatus).catch(function () { renderStatus(null); });
            apiFetch('/api/world/sources').then(function (d) { renderSources(d.sources); }).catch(function () { gridEl.innerHTML = ''; });
            apiFetch('/api/world/events').then(function (d) { renderEvents(d.events); }).catch(function () { eventsEl.innerHTML = ''; });
        }

        function startPoll() {
            stopPoll();
            var tick = function () {
                refresh();
                timer = setTimeout(tick, 15000);
            };
            tick();
        }

        function stopPoll() {
            if (timer) { clearTimeout(timer); timer = null; }
        }

        function open() {
            SurfaceManager.open('world');
            refresh();
            startPoll();
        }

        document.getElementById('wm-scan').addEventListener('click', function () {
            apiFetch('/api/world/scan', { method: 'POST' }).then(function (d) {
                toast('Scan done — ' + (d.events || []).length + ' new events');
                refresh();
            }).catch(function (err) { toast('Scan failed: ' + err.message); });
        });

        document.getElementById('wm-test-notify').addEventListener('click', function () {
            notifyStatus.textContent = 'sending…';
            apiFetch('/api/world/notify/test', { method: 'POST' }).then(function (d) {
                var c = d.channels || {};
                notifyStatus.textContent = 'telegram ' + (c.telegram ? 'OK' : 'FAIL') +
                    ' · imessage ' + (c.imessage ? 'OK' : 'FAIL');
            }).catch(function (err) { notifyStatus.textContent = 'failed: ' + err.message; });
        });

        document.getElementById('wm-add').addEventListener('click', function () {
            var name = document.getElementById('wm-name').value.trim();
            var url = document.getElementById('wm-url').value.trim();
            if (!name || !url) { toast('Name and image URL required'); return; }
            apiFetch('/api/world/sources', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: name,
                    kind: document.getElementById('wm-kind').value,
                    location: document.getElementById('wm-location').value.trim(),
                    image_url: url
                })
            }).then(function () {
                toast('Source added');
                document.getElementById('wm-name').value = '';
                document.getElementById('wm-location').value = '';
                document.getElementById('wm-url').value = '';
                refresh();
            }).catch(function (err) { toast('Add failed: ' + err.message); });
        });

        gridEl.addEventListener('click', function (e) {
            var btn = e.target.closest ? e.target.closest('.wm-toggle') : null;
            if (!btn) return;
            var id = btn.getAttribute('data-id');
            var enable = !btn.classList.contains('on');
            apiFetch('/api/world/sources/' + encodeURIComponent(id), {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled: enable })
            }).then(refresh).catch(function (err) { toast('Toggle failed: ' + err.message); });
        });

        document.getElementById('world-close').addEventListener('click', function () { SurfaceManager.close('world'); });
        SurfaceManager.onChange(function (name) { if (name !== 'world') stopPoll(); });
        return { open: open };
    })();

    var NotebookView = (function () {
        var entriesEl = document.getElementById('nb-entries');
        var answerEl = document.getElementById('nb-answer');

        function esc(s) {
            return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
                return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
            });
        }

        function renderList(entries) {
            entriesEl.innerHTML = '';
            if (!entries || !entries.length) {
                var empty = document.createElement('div');
                empty.className = 'wm-empty';
                empty.textContent = 'Notebook is empty — import your first note.';
                entriesEl.appendChild(empty);
                return;
            }
            entries.forEach(function (e) {
                var row = document.createElement('div');
                row.className = 'nb-entry';
                row.innerHTML = '<div class="nb-entry-head">' +
                    '<span class="nb-entry-title">' + esc(e.title) + '</span>' +
                    '<span class="nb-entry-tags">' + esc((e.tags || []).join(' · ')) + '</span>' +
                    '<button class="nb-entry-del" data-id="' + esc(e.id) + '">DEL</button></div>' +
                    '<div class="nb-entry-body">' + esc(e.body || e.preview || '') + '</div>';
                entriesEl.appendChild(row);
            });
        }

        function refresh() {
            apiFetch('/api/notebook').then(function (d) { renderList(d.entries); }).catch(function () { entriesEl.innerHTML = ''; });
        }

        function open() {
            SurfaceManager.open('notebook');
            refresh();
        }

        document.getElementById('nb-add').addEventListener('click', function () {
            var title = document.getElementById('nb-title').value.trim();
            var body = document.getElementById('nb-body').value.trim();
            if (!title || !body) { toast('Title and body required'); return; }
            apiFetch('/api/notebook', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: title, body: body })
            }).then(function () {
                toast('Note saved');
                document.getElementById('nb-title').value = '';
                document.getElementById('nb-body').value = '';
                refresh();
            }).catch(function (err) { toast('Save failed: ' + err.message); });
        });

        entriesEl.addEventListener('click', function (e) {
            var del = e.target.closest ? e.target.closest('.nb-entry-del') : null;
            if (del) {
                apiFetch('/api/notebook/' + encodeURIComponent(del.getAttribute('data-id')), { method: 'DELETE' })
                    .then(refresh).catch(function (err) { toast('Delete failed: ' + err.message); });
                return;
            }
            var head = e.target.closest ? e.target.closest('.nb-entry-head') : null;
            if (head) head.parentElement.classList.toggle('open');
        });

        document.getElementById('nb-ask').addEventListener('click', function () {
            var q = document.getElementById('nb-question').value.trim();
            if (!q) { toast('Type a question first'); return; }
            answerEl.textContent = 'THINKING…';
            apiFetch('/api/notebook/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: q })
            }).then(function (d) {
                answerEl.textContent = d.answer || '(no answer)';
            }).catch(function (err) { answerEl.textContent = 'failed: ' + err.message; });
        });

        document.getElementById('notebook-close').addEventListener('click', function () { SurfaceManager.close('notebook'); });
        return { open: open };
    })();

    var ProjectView = (function () {
        function open() { SurfaceManager.open('project'); }
        document.getElementById('project-close').addEventListener('click', function () { SurfaceManager.close('project'); });
        var chips = document.querySelectorAll('.pj-commands li');
        for (var i = 0; i < chips.length; i++) {
            (function (chip) {
                chip.addEventListener('click', function () { CommandBar.open(chip.textContent); });
            })(chips[i]);
        }
        return { open: open };
    })();

    var RoadmapView = (function () {
        function open() { SurfaceManager.open('roadmap'); }
        document.getElementById('roadmap-close').addEventListener('click', function () { SurfaceManager.close('roadmap'); });
        return { open: open };
    })();

    // ── boot completion ───────────────────────────────────────────────

    function bootComplete() {
        loadingScreen.classList.add('hidden');
        var container = document.getElementById('golden-core-container');
        var mounted = 'fallback';
        try {
            var core = new Graph3D(container);
            window.goldenCore = core;
            core.init();
            core.loadData();
            core.start();
            core.setState('listening');
            mounted = 'webgl';
        } catch (err) {
            reportError('Graph3D mount failed: ' + (err && err.message ? err.message : err));
            mountFallbackCore(container);
        }
        reportReady(mounted);

        var hud = document.getElementById('core-hud');
        var controls = document.getElementById('core-controls');
        var talk = document.getElementById('core-talk');
        hud.classList.remove('hidden');
        talk.classList.remove('hidden');
        setTimeout(function () { controls.classList.remove('hidden'); }, 600);
        setTimeout(function () { controls.classList.add('hidden'); }, 5000);
    }

    function boot() {
        var start = null;
        function frame(ts) {
            if (start === null) start = ts;
            var t = Math.min((ts - start) / BOOT_MS, 1);
            var eased = 1 - Math.pow(1 - t, 2);
            var pct = Math.round(eased * 100);

            barFill.style.width = pct + '%';
            pctEl.textContent = pct + '%';

            var label = PHASES[PHASES.length - 1].label;
            for (var i = PHASES.length - 1; i >= 0; i--) {
                if (pct >= PHASES[i].at) { label = PHASES[i].label; break; }
            }
            if (statusEl.textContent !== label) statusEl.textContent = label;

            if (t < 1) {
                requestAnimationFrame(frame);
            } else {
                statusEl.textContent = 'SYSTEM READY';
                setTimeout(bootComplete, 350);
            }
        }
        requestAnimationFrame(frame);
    }

    // ── wiring ────────────────────────────────────────────────────────

    var soundBtn = document.getElementById('core-sound');
    function paintSoundBtn() {
        soundBtn.style.opacity = Sound.enabled() ? '1' : '0.35';
    }
    soundBtn.addEventListener('click', function () {
        Sound.setEnabled(!Sound.enabled());
        paintSoundBtn();
        Sound.chime(Sound.enabled() ? 'success' : 'close');
        toast(Sound.enabled() ? 'Sound on' : 'Sound off');
    });
    paintSoundBtn();

    document.getElementById('core-quit').addEventListener('click', quit);
    document.getElementById('core-open-browser').addEventListener('click', openBrowser);

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            if (CommandBar.isOpen()) { CommandBar.close(); return; }
            if (SurfaceManager.closeTop()) return;
            if (DockView.isOpen()) { DockView.close(); return; }
            quit();
        }
    });

    window.addEventListener('error', function (e) { reportError(e.message); });
    window.addEventListener('unhandledrejection', function (e) { reportError(e.reason); });

    document.addEventListener('mousemove', function (e) {
        var controls = document.getElementById('core-controls');
        if (!controls) return;
        var nearTop = e.clientY < 80;
        controls.classList.toggle('core-controls-fade', !nearTop);
        if (nearTop) controls.classList.remove('hidden');
    });

    boot();
})();
