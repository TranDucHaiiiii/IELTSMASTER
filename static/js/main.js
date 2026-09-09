/**
 * IELTSMASTER - Client-side Utilities
 */

// Toast Notification System (Minimalist)
function showToast(message, type = 'info') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.2s ease';
    setTimeout(() => toast.remove(), 200);
  }, 3000);
}

// Speech Synthesis for Audio Pronunciation
function speakText(text, lang = 'en-GB', rate = 0.95) {
  if (!('speechSynthesis' in window)) {
    showToast('Speech synthesis is not supported in this browser.', 'warning');
    return;
  }

  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = lang;
  utterance.rate = rate;

  const voices = window.speechSynthesis.getVoices();
  const englishVoice = voices.find(v => (v.lang === 'en-GB' || v.lang === 'en-US') && v.name.includes('Natural')) ||
                       voices.find(v => v.lang === 'en-GB' || v.lang === 'en-US');
  if (englishVoice) {
    utterance.voice = englishVoice;
  }

  window.speechSynthesis.speak(utterance);
}

// Format seconds into MM:SS
function formatTime(totalSeconds) {
  const mins = Math.floor(totalSeconds / 60);
  const secs = totalSeconds % 60;
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

// Audio Pronunciation with Soundwave Animation
function playVocabAudioWithWave(word, lang = 'en-GB') {
  const wave = document.getElementById('home-soundwave');
  if (wave) wave.classList.add('active');
  speakText(word, lang, 0.9);
  setTimeout(() => {
    if (wave) wave.classList.remove('active');
  }, 1300);
}

// Namespace export
window.IELTSApp = {
  showToast,
  speakText,
  playVocabAudioWithWave,
  formatTime
};

document.addEventListener('DOMContentLoaded', () => {
  if ('speechSynthesis' in window) {
    window.speechSynthesis.onvoiceschanged = () => {
      window.speechSynthesis.getVoices();
    };
  }
});
