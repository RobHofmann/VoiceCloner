// API Base URL
const API_BASE = '';

// DOM Elements
const cloneForm = document.getElementById('clone-form');
const generateForm = document.getElementById('generate-form');
const audioFileInput = document.getElementById('audio-file');
const fileNameDisplay = document.getElementById('file-name');
const voicesList = document.getElementById('voices-list');
const voiceSelect = document.getElementById('voice-select');
const textInput = document.getElementById('text-input');
const charCount = document.getElementById('char-count');
const audioPlayerContainer = document.getElementById('audio-player-container');
const audioPlayer = document.getElementById('audio-player');
const downloadBtn = document.getElementById('download-btn');
const cloneStatus = document.getElementById('clone-status');
const generateStatus = document.getElementById('generate-status');
const statusIndicator = document.getElementById('status-indicator');
const statusText = document.getElementById('status-text');

let currentAudioBlob = null;
let currentAudioFilename = null;

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    checkHealth();
    loadVoices();
    setupEventListeners();
});

// Check API health
async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        const data = await response.json();

        if (data.status === 'healthy') {
            statusIndicator.classList.add('online');
            statusText.textContent = `Connected - ${data.voices_count} voice(s) available`;
        } else {
            statusText.textContent = 'API offline';
        }
    } catch (error) {
        statusText.textContent = 'Connection error';
        console.error('Health check failed:', error);
    }
}

// Setup event listeners
function setupEventListeners() {
    // File input display
    audioFileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            fileNameDisplay.textContent = `Selected: ${file.name} (${formatFileSize(file.size)})`;
        } else {
            fileNameDisplay.textContent = '';
        }
    });

    // Character counter
    textInput.addEventListener('input', (e) => {
        charCount.textContent = `${e.target.value.length} characters`;
    });

    // Clone form
    cloneForm.addEventListener('submit', handleCloneVoice);

    // Generate form
    generateForm.addEventListener('submit', handleGenerateSpeech);

    // Download button
    downloadBtn.addEventListener('click', handleDownload);
}

// Load voices
async function loadVoices() {
    try {
        const response = await fetch(`${API_BASE}/voices`);
        const data = await response.json();

        displayVoices(data.voices);
        updateVoiceSelect(data.voices);
    } catch (error) {
        console.error('Failed to load voices:', error);
        voicesList.innerHTML = '<p class="error">Failed to load voices</p>';
    }
}

// Display voices in the list
function displayVoices(voices) {
    if (voices.length === 0) {
        voicesList.innerHTML = '<p class="loading">No voices cloned yet. Clone your first voice above!</p>';
        return;
    }

    voicesList.innerHTML = voices.map(voice => `
        <div class="voice-item">
            <div class="voice-info">
                <h3>${escapeHtml(voice.name)}</h3>
                <p>Original file: ${escapeHtml(voice.original_file)}${voice.has_reference_text ? ' • Has reference text' : ''}</p>
            </div>
            <div class="voice-actions">
                <button class="btn btn-danger" onclick="deleteVoice('${escapeHtml(voice.name)}')">Delete</button>
            </div>
        </div>
    `).join('');
}

// Update voice select dropdown
function updateVoiceSelect(voices) {
    voiceSelect.innerHTML = '<option value="">-- Select a voice --</option>' +
        voices.map(voice => `<option value="${escapeHtml(voice.name)}">${escapeHtml(voice.name)}</option>`).join('');
}

// Handle voice cloning
async function handleCloneVoice(e) {
    e.preventDefault();

    const voiceName = document.getElementById('voice-name').value;
    const referenceText = document.getElementById('reference-text').value;
    const audioFile = audioFileInput.files[0];

    if (!audioFile) {
        showStatus(cloneStatus, 'Please select an audio file', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', audioFile);
    formData.append('voice_name', voiceName);
    if (referenceText) {
        formData.append('reference_text', referenceText);
    }

    const cloneBtn = document.getElementById('clone-btn');
    cloneBtn.disabled = true;
    cloneBtn.innerHTML = '<span class="spinner"></span> Cloning...';
    showStatus(cloneStatus, 'Processing your voice sample...', 'loading');

    try {
        const response = await fetch(`${API_BASE}/voices/clone`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            showStatus(cloneStatus, `Success! Voice "${voiceName}" has been cloned.`, 'success');
            cloneForm.reset();
            fileNameDisplay.textContent = '';
            await loadVoices();
            await checkHealth();
        } else {
            showStatus(cloneStatus, `Error: ${data.detail || 'Failed to clone voice'}`, 'error');
        }
    } catch (error) {
        console.error('Clone error:', error);
        showStatus(cloneStatus, 'Network error. Please try again.', 'error');
    } finally {
        cloneBtn.disabled = false;
        cloneBtn.textContent = 'Clone Voice';
    }
}

// Handle speech generation
async function handleGenerateSpeech(e) {
    e.preventDefault();

    const voiceName = voiceSelect.value;
    const text = textInput.value;

    if (!voiceName) {
        showStatus(generateStatus, 'Please select a voice', 'error');
        return;
    }

    if (!text.trim()) {
        showStatus(generateStatus, 'Please enter some text', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('text', text);
    formData.append('voice_name', voiceName);

    const generateBtn = document.getElementById('generate-btn');
    generateBtn.disabled = true;
    generateBtn.innerHTML = '<span class="spinner"></span> Generating...';
    showStatus(generateStatus, 'Generating speech...', 'loading');
    audioPlayerContainer.style.display = 'none';

    try {
        const response = await fetch(`${API_BASE}/tts/generate`, {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);

            // Get filename from response headers
            const contentDisposition = response.headers.get('content-disposition');
            const filenameMatch = contentDisposition && contentDisposition.match(/filename="(.+)"/);
            currentAudioFilename = filenameMatch ? filenameMatch[1] : 'generated_speech.wav';

            currentAudioBlob = blob;
            audioPlayer.src = url;
            audioPlayerContainer.style.display = 'block';

            showStatus(generateStatus, 'Speech generated successfully!', 'success');
        } else {
            const data = await response.json();
            showStatus(generateStatus, `Error: ${data.detail || 'Failed to generate speech'}`, 'error');
        }
    } catch (error) {
        console.error('Generate error:', error);
        showStatus(generateStatus, 'Network error. Please try again.', 'error');
    } finally {
        generateBtn.disabled = false;
        generateBtn.textContent = 'Generate Speech';
    }
}

// Handle download
function handleDownload() {
    if (!currentAudioBlob) return;

    const url = URL.createObjectURL(currentAudioBlob);
    const a = document.createElement('a');
    a.href = url;
    a.download = currentAudioFilename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// Delete voice
async function deleteVoice(voiceName) {
    if (!confirm(`Are you sure you want to delete the voice "${voiceName}"?`)) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/voices/${encodeURIComponent(voiceName)}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (response.ok) {
            await loadVoices();
            await checkHealth();
        } else {
            alert(`Error: ${data.detail || 'Failed to delete voice'}`);
        }
    } catch (error) {
        console.error('Delete error:', error);
        alert('Network error. Please try again.');
    }
}

// Show status message
function showStatus(element, message, type) {
    element.textContent = message;
    element.className = `status-message show ${type}`;

    if (type === 'success' || type === 'error') {
        setTimeout(() => {
            element.classList.remove('show');
        }, 5000);
    }
}

// Utility functions
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
