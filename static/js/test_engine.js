/**
 * IELTS Computer-Delivered Test Engine (Reading & Listening)
 */

class IELTSTestEngine {
  constructor(config) {
    this.testId = config.testId;
    this.testType = config.testType; // 'reading' or 'listening'
    this.durationMinutes = config.durationMinutes || 60;
    this.timeRemaining = this.durationMinutes * 60;
    this.timerInterval = null;
    this.answers = {};
    this.totalQuestions = config.totalQuestions || 0;
    
    this.initElements();
    this.bindEvents();
    this.startTimer();
  }

  initElements() {
    this.timerDisplay = document.getElementById('test-timer');
    this.submitBtn = document.getElementById('submit-test-btn');
    this.resultModal = document.getElementById('result-modal');
    this.modalContent = document.getElementById('modal-results-body');
  }

  bindEvents() {
    // Listen for inputs inside questions
    document.querySelectorAll('.question-input').forEach(input => {
      input.addEventListener('change', (e) => {
        const qid = e.target.getAttribute('data-qid');
        this.answers[qid] = e.target.value.trim();
        this.updateNavPill(qid, true);
      });

      // Handle text input typing
      if (input.tagName === 'INPUT' && input.type === 'text') {
        input.addEventListener('input', (e) => {
          const qid = e.target.getAttribute('data-qid');
          const val = e.target.value.trim();
          if (val) {
            this.answers[qid] = val;
            this.updateNavPill(qid, true);
          } else {
            delete this.answers[qid];
            this.updateNavPill(qid, false);
          }
        });
      }
    });

    // Nav pills jumping
    document.querySelectorAll('.nav-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        const qid = pill.getAttribute('data-qid');
        const targetQ = document.getElementById(`card-${qid}`);
        if (targetQ) {
          targetQ.scrollIntoView({ behavior: 'smooth', block: 'center' });
          targetQ.style.borderColor = 'var(--accent-primary)';
          setTimeout(() => {
            targetQ.style.borderColor = '';
          }, 1200);
        }
      });
    });

    // Submit button
    if (this.submitBtn) {
      this.submitBtn.addEventListener('click', () => this.confirmSubmit());
    }
  }

  updateNavPill(qid, isAnswered) {
    const pill = document.querySelector(`.nav-pill[data-qid="${qid}"]`);
    if (pill) {
      if (isAnswered) {
        pill.classList.add('answered');
      } else {
        pill.classList.remove('answered');
      }
    }
  }

  startTimer() {
    this.updateTimerDisplay();
    this.timerInterval = setInterval(() => {
      this.timeRemaining--;
      this.updateTimerDisplay();

      if (this.timeRemaining <= 0) {
        clearInterval(this.timerInterval);
        showToast('Hết thời gian làm bài! Hệ thống đang tự động nộp bài...', 'warning');
        this.submitTest();
      }
    }, 1000);
  }

  updateTimerDisplay() {
    if (this.timerDisplay) {
      this.timerDisplay.textContent = formatTime(Math.max(0, this.timeRemaining));
      if (this.timeRemaining < 300) { // Less than 5 mins
        this.timerDisplay.parentElement.style.borderColor = 'var(--accent-rose)';
        this.timerDisplay.style.color = 'var(--accent-rose)';
      }
    }
  }

  confirmSubmit() {
    const answeredCount = Object.keys(this.answers).length;
    const unanswered = this.totalQuestions - answeredCount;
    let message = `Bạn đã hoàn thành ${answeredCount}/${this.totalQuestions} câu hỏi.`;
    if (unanswered > 0) {
      message += ` Còn ${unanswered} câu chưa làm. Bạn có chắc chắn muốn nộp bài?`;
    } else {
      message += ' Bạn có chắc chắn muốn nộp bài để xem điểm số và giải thích?';
    }

    if (confirm(message)) {
      this.submitTest();
    }
  }

  async submitTest() {
    clearInterval(this.timerInterval);
    const timeSpent = (this.durationMinutes * 60) - this.timeRemaining;
    const endpoint = this.testType === 'reading' 
      ? '/api/tests/reading/grade' 
      : '/api/tests/listening/grade';

    this.submitBtn.disabled = true;
    this.submitBtn.innerHTML = '⏳ Đang chấm điểm...';

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          test_id: this.testId,
          answers: this.answers,
          time_spent: timeSpent
        })
      });

      const data = await res.json();
      if (res.ok) {
        this.displayResults(data, timeSpent);
      } else {
        showToast(data.error || 'Có lỗi xảy ra khi chấm bài.', 'error');
        this.submitBtn.disabled = false;
        this.submitBtn.innerHTML = 'Nộp bài thi';
      }
    } catch (err) {
      console.error(err);
      showToast('Lỗi kết nối tới máy chủ.', 'error');
      this.submitBtn.disabled = false;
      this.submitBtn.innerHTML = 'Nộp bài thi';
    }
  }

  displayResults(result, timeSpent) {
    const { score, max_score, band_score, detailed_results } = result;

    let html = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; border-bottom: 1px solid var(--border-hairline); padding-bottom: 0.75rem;">
        <div>
          <h2 style="font-size: 1.25rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.2rem;">
            Test Results — ${this.testType.toUpperCase()}
          </h2>
          <span style="font-size: 0.82rem; color: var(--text-muted);">Completed in ${formatTime(timeSpent)}</span>
        </div>
        <div style="text-align: right;">
          <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Official Band</span>
          <div style="font-size: 2rem; font-weight: 700; color: var(--text-primary); line-height: 1;">
            ${band_score}
          </div>
        </div>
      </div>

      <div style="display: flex; gap: 1rem; margin-bottom: 1.5rem;">
        <div style="flex: 1; padding: 0.75rem; background: var(--bg-subtle); border: 1px solid var(--border-hairline); border-radius: var(--radius-sm); text-align: center;">
          <span style="font-size: 0.75rem; color: var(--text-muted);">RAW SCORE</span>
          <div style="font-size: 1.25rem; font-weight: 600; color: var(--text-primary); margin-top: 0.15rem;">${score} / ${max_score}</div>
        </div>
        <div style="flex: 1; padding: 0.75rem; background: var(--bg-subtle); border: 1px solid var(--border-hairline); border-radius: var(--radius-sm); text-align: center;">
          <span style="font-size: 0.75rem; color: var(--text-muted);">ACCURACY</span>
          <div style="font-size: 1.25rem; font-weight: 600; color: var(--text-primary); margin-top: 0.15rem;">${Math.round((score / max_score) * 100)}%</div>
        </div>
      </div>

      <div style="font-size: 0.88rem; font-weight: 600; margin-bottom: 0.75rem; color: var(--text-primary);">
        Question Breakdown & Answers
      </div>
      <div style="display: flex; flex-direction: column; gap: 0.75rem; max-height: 380px; overflow-y: auto; margin-bottom: 1.5rem; padding-right: 0.5rem;">
    `;

    detailed_results.forEach((item, index) => {
      const isCorrect = item.is_correct;
      html += `
        <div style="padding: 0.85rem; border: 1px solid var(--border-hairline); border-radius: var(--radius-sm); background: ${isCorrect ? '#ffffff' : '#fafafa'};">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.35rem;">
            <span style="font-size: 0.88rem; font-weight: 600; color: var(--text-primary);">
              ${index + 1}. ${item.question}
            </span>
            <span class="badge ${isCorrect ? 'badge-success' : 'badge-danger'}">
              ${isCorrect ? 'Correct (+1)' : 'Incorrect'}
            </span>
          </div>
          <div style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.25rem;">
            Your answer: <strong style="color: ${isCorrect ? 'var(--success)' : 'var(--danger)'};">${item.user_answer || '(Empty)'}</strong>
            ${!isCorrect ? ` • Correct answer: <strong style="color: var(--text-primary);">${item.correct_answer}</strong>` : ''}
          </div>
          <div style="font-size: 0.8rem; color: var(--text-muted); background: var(--bg-subtle); padding: 0.5rem 0.75rem; border-radius: var(--radius-xs); margin-top: 0.4rem;">
            Explanation: ${item.explanation}
          </div>
        </div>
      `;
    });

    html += `
      </div>
      <div style="display: flex; justify-content: flex-end; gap: 0.5rem; border-top: 1px solid var(--border-hairline); padding-top: 1rem;">
        <button class="btn btn-secondary btn-sm" onclick="location.reload()">
          Retake test
        </button>
        <a href="/" class="btn btn-primary btn-sm">
          Return to Dashboard
        </a>
      </div>
    `;

    this.modalContent.innerHTML = html;
    this.resultModal.classList.add('active');
  }
}
