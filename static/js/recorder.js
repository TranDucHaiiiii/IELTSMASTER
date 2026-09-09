/**
 * IELTS Speaking Room - Voice Recorder & Timers
 */

class SpeakingRoom {
  constructor() {
    this.mediaRecorder = null;
    this.audioChunks = [];
    this.isRecording = false;
    this.recordingStartTime = null;
    this.timerInterval = null;
    this.recordedAudioUrl = null;

    this.initElements();
    this.bindEvents();
  }

  initElements() {
    this.recordBtn = document.getElementById('mic-record-btn');
    this.recordTimer = document.getElementById('record-timer');
    this.recordStatus = document.getElementById('record-status');
    this.audioPlayer = document.getElementById('audio-playback');
    this.playerContainer = document.getElementById('playback-container');
    
    // Cue card timers
    this.prepTimerDisplay = document.getElementById('prep-timer-display');
    this.startPrepBtn = document.getElementById('start-prep-btn');
  }

  bindEvents() {
    if (this.recordBtn) {
      this.recordBtn.addEventListener('click', () => this.toggleRecording());
    }

    if (this.startPrepBtn) {
      this.startPrepBtn.addEventListener('click', () => this.startCueCardPrep(60));
    }
  }

  async toggleRecording() {
    if (this.isRecording) {
      this.stopRecording();
    } else {
      await this.startRecording();
    }
  }

  async startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.mediaRecorder = new MediaRecorder(stream);
      this.audioChunks = [];

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data);
        }
      };

      this.mediaRecorder.onstop = () => {
        const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
        this.recordedAudioUrl = URL.createObjectURL(audioBlob);
        if (this.audioPlayer) {
          this.audioPlayer.src = this.recordedAudioUrl;
          this.playerContainer.style.display = 'block';
        }
        showToast('Đã lưu bản ghi âm! Bạn có thể nghe lại bên dưới.', 'success');
      };

      this.mediaRecorder.start();
      this.isRecording = true;
      this.recordingStartTime = Date.now();
      
      this.recordBtn.classList.add('recording');
      this.recordStatus.textContent = 'Đang ghi âm câu trả lời của bạn... (Nhấn lại để dừng)';
      this.recordStatus.style.color = 'var(--accent-rose)';

      this.timerInterval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - this.recordingStartTime) / 1000);
        this.recordTimer.textContent = formatTime(elapsed);
      }, 1000);

    } catch (err) {
      console.error(err);
      showToast('Không thể kết nối Microphone. Hãy kiểm tra quyền truy cập!', 'error');
    }
  }

  stopRecording() {
    if (this.mediaRecorder && this.isRecording) {
      this.mediaRecorder.stop();
      this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
      this.isRecording = false;
      clearInterval(this.timerInterval);

      this.recordBtn.classList.remove('recording');
      this.recordStatus.textContent = 'Đã hoàn thành ghi âm. Nhấn vào mic nếu muốn thu âm lại.';
      this.recordStatus.style.color = 'var(--accent-emerald)';
    }
  }

  startCueCardPrep(seconds = 60) {
    let timeLeft = seconds;
    this.startPrepBtn.disabled = true;
    this.prepTimerDisplay.textContent = `01:00`;
    this.prepTimerDisplay.style.color = 'var(--accent-amber)';

    const interval = setInterval(() => {
      timeLeft--;
      this.prepTimerDisplay.textContent = formatTime(timeLeft);

      if (timeLeft <= 0) {
        clearInterval(interval);
        this.prepTimerDisplay.textContent = "HẾT 1 PHÚT CHUẨN BỊ! BẮT ĐẦU NÓI";
        this.prepTimerDisplay.style.color = 'var(--accent-rose)';
        this.startPrepBtn.disabled = false;
        showToast('Hết 1 phút chuẩn bị! Hãy bấm ghi âm và bắt đầu nói trong 2 phút.', 'warning');
      }
    }, 1000);
  }
}
