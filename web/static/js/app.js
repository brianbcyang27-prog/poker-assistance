/**
 * JARVIS Web - Main Application
 * Integrates chat, visualization, and state management
 */

let currentSessionId = null;
let selectedVoiceId = null;
let messageCount = 0;

// Panel management
function togglePanel(panel) {
    const panelEl = document.getElementById(panel + '-panel');
    const isOpen = panelEl.classList.contains('open');

    // Close all panels first
    document.querySelectorAll('.side-panel').forEach(p => p.classList.remove('open'));

    // Toggle the clicked panel
    if (!isOpen) {
        panelEl.classList.add('open');
    }
}

// Chat panel toggle
function toggleChat() {
    const panel = document.getElementById('chat-panel');
    panel.classList.toggle('collapsed');
}

// Send message
function sendMessage() {
    const input = document.getElementById('message-input');
    const message = input.value.trim();
    if (!message) return;

    appendMessage('user', message);
    input.value = '';
    input.style.height = 'auto';

    // Update state to thinking
    if (window.jarvisState) {
        window.jarvisState.startThinking();
    }

    showTyping();

    const body = { message, session_id: currentSessionId };
    if (selectedVoiceId) body.voice_id = selectedVoiceId;

    fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    })
    .then(r => r.json())
    .then(data => {
        removeTyping();
        currentSessionId = data.session_id;
        appendMessage('assistant', data.response);

        // Update state to speaking if audio
        if (data.audio_url && window.jarvisState) {
            window.jarvisState.startSpeaking();
            playAudioWithAnalysis(data.audio_url);
        } else if (window.jarvisState) {
            window.jarvisState.set('idle');
        }
    })
    .catch(err => {
        removeTyping();
        appendMessage('assistant', 'Error: ' + err.message);
        if (window.jarvisState) {
            window.jarvisState.set('idle');
        }
    });
}

function sendQuick(text) {
    document.getElementById('message-input').value = text;
    sendMessage();
}

function appendMessage(role, content) {
    const messages = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = `message ${role}`;
    div.innerHTML = renderMarkdown(content);
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;

    // Update count
    messageCount++;
    document.getElementById('message-count').textContent = messageCount;
}

function renderMarkdown(text) {
    let html = text
        .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="lang-$1">$2</code></pre>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>');
    return html;
}

function showTyping() {
    const messages = document.getElementById('messages');
    const div = document.createElement('div');
    div.id = 'typing-indicator';
    div.className = 'typing-indicator';
    div.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
}

function removeTyping() {
    const el = document.getElementById('typing-indicator');
    if (el) el.remove();
}

// Audio playback with visualization integration
function playAudioWithAnalysis(url) {
    const audio = new Audio(url);

    // Connect to audio analyzer if available
    if (window.audioAnalyzer && window.audioAnalyzer.audioContext) {
        try {
            window.audioAnalyzer.connectAudioElement(audio);
        } catch (e) {
            // May already be connected
        }
    }

    // Update visualization with audio data
    const updateVisualization = () => {
        if (window.audioAnalyzer && window.audioAnalyzer.isActive) {
            const values = window.audioAnalyzer.getValues();
            if (window.jarvisCore) {
                window.jarvisCore.setAudio(values.volume, values.frequency, values.pitch);
            }
        }
        if (!audio.paused) {
            requestAnimationFrame(updateVisualization);
        }
    };

    audio.addEventListener('play', () => {
        updateVisualization();
    });

    audio.addEventListener('ended', () => {
        if (window.jarvisState) {
            window.jarvisState.stopSpeaking();
        }
        if (window.jarvisCore) {
            window.jarvisCore.setAudio(0, 0, 0);
        }
    });

    audio.play().catch(() => {});
}

// Voice sample upload
async function uploadVoice() {
    const form = document.getElementById('upload-form');
    const formData = new FormData(form);

    const res = await fetch('/api/voice/sample', { method: 'POST', body: formData });
    if (res.ok) {
        form.reset();
        document.getElementById('upload-modal').close();
        // Reload voice samples
        const voiceContent = document.getElementById('voice-content');
        if (voiceContent) {
            htmx.trigger(voiceContent, 'htmx:load');
        }
    }
}

// Select voice sample
function selectVoice(id) {
    selectedVoiceId = selectedVoiceId === id ? null : id;
    document.querySelectorAll('.voice-sample').forEach(el => {
        el.classList.toggle('selected', el.dataset.id == selectedVoiceId);
    });
}

// Delete voice sample
async function deleteVoice(id) {
    if (!confirm('Delete this voice sample?')) return;

    await fetch(`/api/voice/sample/${id}`, { method: 'DELETE' });
    const voiceContent = document.getElementById('voice-content');
    if (voiceContent) {
        htmx.trigger(voiceContent, 'htmx:load');
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    // Check TTS status
    fetch('/api/voice/samples')
        .then(r => r.json())
        .then(samples => {
            // Update TTS status indicator if needed
        })
        .catch(() => {});
});
