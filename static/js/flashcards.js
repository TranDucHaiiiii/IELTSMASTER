/**
 * IELTS Vocabulary - 3D Flashcards & Study Deck
 */

class FlashcardDeck {
  constructor(cards) {
    this.allCards = cards;
    this.filteredCards = [...cards];
    this.currentIndex = 0;

    this.initElements();
    this.bindEvents();
    this.renderCard();
  }

  initElements() {
    this.cardElement = document.getElementById('active-flashcard');
    this.wordEl = document.getElementById('card-word');
    this.ipaEl = document.getElementById('card-ipa');
    this.posEl = document.getElementById('card-pos');
    this.bandEl = document.getElementById('card-band');
    this.meaningEl = document.getElementById('card-meaning');
    this.exampleEl = document.getElementById('card-example');
    this.synonymsEl = document.getElementById('card-synonyms');
    this.counterEl = document.getElementById('card-counter');
    this.masteredBtn = document.getElementById('mark-mastered-btn');
    this.audioBtn = document.getElementById('pronounce-btn');
    this.topicFilter = document.getElementById('topic-filter');
  }

  bindEvents() {
    // Click card to flip
    if (this.cardElement) {
      this.cardElement.addEventListener('click', (e) => {
        // Prevent flipping if clicked on action buttons
        if (e.target.closest('button') || e.target.closest('.no-flip')) return;
        this.cardElement.classList.toggle('flipped');
      });
    }

    // Prev / Next
    const prevBtn = document.getElementById('prev-card-btn');
    const nextBtn = document.getElementById('next-card-btn');
    if (prevBtn) prevBtn.addEventListener('click', () => this.prevCard());
    if (nextBtn) nextBtn.addEventListener('click', () => this.nextCard());

    // Pronunciation
    if (this.audioBtn) {
      this.audioBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const current = this.getCurrentCard();
        if (current) {
          speakText(current.word, 'en-GB', 0.9);
        }
      });
    }

    // Toggle Mastered
    if (this.masteredBtn) {
      this.masteredBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.toggleMastered();
      });
    }

    // Topic Filter
    if (this.topicFilter) {
      this.topicFilter.addEventListener('change', (e) => {
        const topic = e.target.value;
        if (topic === 'all') {
          this.filteredCards = [...this.allCards];
        } else {
          this.filteredCards = this.allCards.filter(c => c.topic === topic);
        }
        this.currentIndex = 0;
        this.renderCard();
      });
    }

    // Keyboard navigation (ArrowLeft, ArrowRight, Space for flip)
    document.addEventListener('keydown', (e) => {
      if (document.activeElement && (document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'TEXTAREA')) return;
      if (e.code === 'Space') {
        e.preventDefault();
        this.cardElement.classList.toggle('flipped');
      } else if (e.code === 'ArrowRight') {
        this.nextCard();
      } else if (e.code === 'ArrowLeft') {
        this.prevCard();
      }
    });
  }

  getCurrentCard() {
    return this.filteredCards[this.currentIndex];
  }

  renderCard() {
    if (this.filteredCards.length === 0) {
      this.wordEl.textContent = 'Không có từ nào';
      this.counterEl.textContent = '0/0';
      return;
    }

    // Reset flip
    this.cardElement.classList.remove('flipped');

    const card = this.getCurrentCard();
    this.wordEl.textContent = card.word;
    this.ipaEl.textContent = card.ipa;
    this.posEl.textContent = card.pos;
    this.bandEl.textContent = card.band || 'Band 7.5+';
    this.meaningEl.textContent = card.meaning_vi;
    this.exampleEl.textContent = `"${card.example}"`;
    
    if (card.synonyms && card.synonyms.length > 0) {
      this.synonymsEl.innerHTML = card.synonyms.map(s => `<span class="badge badge-primary">${s}</span>`).join(' ');
    } else {
      this.synonymsEl.innerHTML = '<em>Không có từ đồng nghĩa</em>';
    }

    this.counterEl.textContent = `${this.currentIndex + 1} / ${this.filteredCards.length}`;

    // Update mastered button state
    if (card.is_mastered) {
      this.masteredBtn.classList.remove('btn-secondary');
      this.masteredBtn.classList.add('btn-emerald');
      this.masteredBtn.innerHTML = '✓ Đã thuộc từ này';
    } else {
      this.masteredBtn.classList.remove('btn-emerald');
      this.masteredBtn.classList.add('btn-secondary');
      this.masteredBtn.innerHTML = 'Đánh dấu đã thuộc';
    }
  }

  nextCard() {
    if (this.currentIndex < this.filteredCards.length - 1) {
      this.currentIndex++;
      this.renderCard();
    } else {
      this.currentIndex = 0; // wrap around
      this.renderCard();
    }
  }

  prevCard() {
    if (this.currentIndex > 0) {
      this.currentIndex--;
      this.renderCard();
    } else {
      this.currentIndex = this.filteredCards.length - 1;
      this.renderCard();
    }
  }

  async toggleMastered() {
    const card = this.getCurrentCard();
    if (!card) return;

    try {
      const res = await fetch('/api/vocabulary/toggle-mastery', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ word_id: card.id })
      });
      const data = await res.json();
      if (res.ok) {
        card.is_mastered = data.is_mastered;
        this.renderCard();
        showToast(card.is_mastered ? 'Đã ghi nhận bạn đã thuộc từ này! 🎉' : 'Đã chuyển từ vào danh sách cần ôn tập.', 'success');
      }
    } catch (err) {
      console.error(err);
      showToast('Không thể cập nhật tiến độ.', 'error');
    }
  }
}
