"""
IELTS Master Hub - Comprehensive IELTS Preparation Web Application.
Built with Python (Flask) and SQLite.
"""

import os
import json
import re
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import (
    init_db, save_test_result, get_test_history,
    save_writing_submission, get_writing_submissions,
    save_speaking_log, toggle_vocab_mastery, get_vocab_progress,
    get_dashboard_summary, create_user, get_user_by_username_or_email,
    get_user_by_id, update_user_target_band
)
from vocab_service import get_or_fetch_vocabulary

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ielts-master-secret-key-2026'

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

def load_json(filename):
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

# Ensure DB initialized
init_db()

# --- Context Processor for Auth State ---
@app.context_processor
def inject_user():
    user_id = session.get('user_id')
    user = get_user_by_id(user_id) if user_id else None
    return {'current_user': user}

# --- Band Score Conversion Helper ---
def raw_to_reading_academic_band(raw_score, max_score=40):
    scaled = int(round((raw_score / max_score) * 40))
    if scaled >= 39: return 9.0
    if scaled >= 37: return 8.5
    if scaled >= 35: return 8.0
    if scaled >= 33: return 7.5
    if scaled >= 30: return 7.0
    if scaled >= 27: return 6.5
    if scaled >= 23: return 6.0
    if scaled >= 19: return 5.5
    if scaled >= 15: return 5.0
    if scaled >= 13: return 4.5
    if scaled >= 10: return 4.0
    if scaled >= 8:  return 3.5
    if scaled >= 6:  return 3.0
    return 2.5

def raw_to_listening_band(raw_score, max_score=40):
    scaled = int(round((raw_score / max_score) * 40))
    if scaled >= 39: return 9.0
    if scaled >= 37: return 8.5
    if scaled >= 35: return 8.0
    if scaled >= 32: return 7.5
    if scaled >= 30: return 7.0
    if scaled >= 26: return 6.5
    if scaled >= 23: return 6.0
    if scaled >= 18: return 5.5
    if scaled >= 16: return 5.0
    if scaled >= 13: return 4.5
    if scaled >= 10: return 4.0
    if scaled >= 8:  return 3.5
    if scaled >= 6:  return 3.0
    return 2.5

def calculate_overall_band(l, r, w, s):
    avg = (l + r + w + s) / 4.0
    integer_part = int(avg)
    fraction = avg - integer_part
    if fraction < 0.25:
        return float(integer_part)
    elif fraction < 0.75:
        return float(integer_part) + 0.5
    else:
        return float(integer_part + 1)

# --- Authentication Routes ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('user_id'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        try:
            target_band = float(request.form.get('target_band', 7.5))
        except ValueError:
            target_band = 7.5

        if not username or not email or not password:
            return render_template('register.html', error='Vui lòng điền đầy đủ các trường thông tin.', form=request.form)

        if len(username) < 3:
            return render_template('register.html', error='Tên đăng nhập phải có ít nhất 3 ký tự.', form=request.form)

        if '@' not in email or '.' not in email:
            return render_template('register.html', error='Địa chỉ email không hợp lệ.', form=request.form)

        if len(password) < 6:
            return render_template('register.html', error='Mật khẩu phải có ít nhất 6 ký tự.', form=request.form)

        if password != confirm_password:
            return render_template('register.html', error='Mật khẩu xác nhận không trùng khớp!', form=request.form)

        if get_user_by_username_or_email(username):
            return render_template('register.html', error=f'Tên đăng nhập "{username}" đã được sử dụng. Vui lòng chọn tên khác.', form=request.form)

        if get_user_by_username_or_email(email):
            return render_template('register.html', error=f'Email "{email}" đã được đăng ký. Vui lòng đăng nhập hoặc dùng email khác.', form=request.form)

        password_hash = generate_password_hash(password)
        user_id = create_user(username, email, password_hash, target_band)

        # Log user in
        session['user_id'] = user_id
        session['username'] = username
        return redirect(url_for('index'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')

        if not identifier or not password:
            return render_template('login.html', error='Vui lòng nhập tên đăng nhập/email và mật khẩu.', identifier=identifier)

        user = get_user_by_username_or_email(identifier)
        if not user or not check_password_hash(user['password_hash'], password):
            return render_template('login.html', error='Tên đăng nhập hoặc mật khẩu không chính xác!', identifier=identifier)

        session['user_id'] = user['id']
        session['username'] = user['username']
        next_url = request.args.get('next')
        return redirect(next_url or url_for('index'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# --- Template Views ---
@app.route('/')
def index():
    user_id = session.get('user_id')
    summary = get_dashboard_summary(user_id=user_id)
    recent_tests = get_test_history(limit=5, user_id=user_id)
    recent_writings = get_writing_submissions(limit=3, user_id=user_id)
    vocab_list = load_json('vocabulary.json')
    return render_template(
        'index.html',
        summary=summary,
        recent_tests=recent_tests,
        recent_writings=recent_writings,
        vocab_count=len(vocab_list)
    )

@app.route('/reading')
def reading():
    tests = load_json('reading_tests.json')
    test = tests[0] if tests else None
    return render_template('reading.html', test=test, tests=tests)

@app.route('/listening')
def listening():
    tests = load_json('listening_tests.json')
    test = tests[0] if tests else None
    return render_template('listening.html', test=test, tests=tests)

@app.route('/writing')
def writing():
    user_id = session.get('user_id')
    prompts = load_json('writing_prompts.json')
    history = get_writing_submissions(limit=10, user_id=user_id)
    return render_template('writing.html', prompts=prompts, history=history)

@app.route('/speaking')
def speaking():
    topics = load_json('speaking_topics.json')
    return render_template('speaking.html', topics=topics)

@app.route('/vocabulary')
def vocabulary():
    user_id = session.get('user_id') or 1
    vocab_list = load_json('vocabulary.json')
    progress = get_vocab_progress(user_id=user_id)
    for item in vocab_list:
        item_id = item['id']
        item['is_mastered'] = progress.get(item_id, {}).get('is_mastered', False)
        item['review_count'] = progress.get(item_id, {}).get('review_count', 0)
    topics = sorted(list(set(item['topic'] for item in vocab_list)))
    return render_template('vocabulary.html', vocab_list=vocab_list, topics=topics)

@app.route('/calculator')
def calculator():
    return render_template('calculator.html')

@app.route('/history')
def history():
    user_id = session.get('user_id')
    tests = get_test_history(limit=25, user_id=user_id)
    writings = get_writing_submissions(limit=15, user_id=user_id)
    return render_template('history.html', tests=tests, writings=writings)

@app.route('/grammar')
def grammar():
    return render_template('grammar.html')


# --- REST API Endpoints ---
@app.route('/api/tests/reading/grade', methods=['POST'])
def grade_reading():
    user_id = session.get('user_id')
    data = request.json or {}
    test_id = data.get('test_id')
    user_answers = data.get('answers', {})
    time_spent = data.get('time_spent', 0)
    
    tests = load_json('reading_tests.json')
    target_test = next((t for t in tests if t['id'] == test_id), None)
    
    if not target_test:
        return jsonify({'error': 'Test not found'}), 404
        
    correct_count = 0
    total_questions = 0
    detailed_results = []
    
    for passage in target_test.get('passages', []):
        for q in passage.get('questions', []):
            total_questions += 1
            qid = q['id']
            ans = str(user_answers.get(qid, '')).strip().lower()
            correct = str(q['correct_answer']).strip().lower()
            
            is_correct = (ans == correct)
            if is_correct:
                correct_count += 1
                
            detailed_results.append({
                'id': qid,
                'question': q['question'],
                'user_answer': user_answers.get(qid, ''),
                'correct_answer': q['correct_answer'],
                'is_correct': is_correct,
                'explanation': q.get('explanation', '')
            })
            
    band = raw_to_reading_academic_band(correct_count, total_questions)
    
    save_test_result(
        test_type='Reading Academic',
        test_id=test_id,
        test_title=target_test['title'],
        score=correct_count,
        max_score=total_questions,
        band_score=band,
        time_spent=time_spent,
        answers=detailed_results,
        user_id=user_id
    )
    
    return jsonify({
        'score': correct_count,
        'max_score': total_questions,
        'band_score': band,
        'detailed_results': detailed_results
    })

@app.route('/api/tests/listening/grade', methods=['POST'])
def grade_listening():
    user_id = session.get('user_id')
    data = request.json or {}
    test_id = data.get('test_id')
    user_answers = data.get('answers', {})
    time_spent = data.get('time_spent', 0)
    
    tests = load_json('listening_tests.json')
    target_test = next((t for t in tests if t['id'] == test_id), None)
    
    if not target_test:
        return jsonify({'error': 'Test not found'}), 404
        
    correct_count = 0
    total_questions = 0
    detailed_results = []
    
    for section in target_test.get('sections', []):
        for q in section.get('questions', []):
            total_questions += 1
            qid = q['id']
            ans = str(user_answers.get(qid, '')).strip().lower()
            correct = str(q['correct_answer']).strip().lower()
            
            is_correct = (ans == correct)
            if is_correct:
                correct_count += 1
                
            detailed_results.append({
                'id': qid,
                'question': q['question'],
                'user_answer': user_answers.get(qid, ''),
                'correct_answer': q['correct_answer'],
                'is_correct': is_correct,
                'explanation': q.get('explanation', '')
            })
            
    band = raw_to_listening_band(correct_count, total_questions)
    
    save_test_result(
        test_type='Listening',
        test_id=test_id,
        test_title=target_test['title'],
        score=correct_count,
        max_score=total_questions,
        band_score=band,
        time_spent=time_spent,
        answers=detailed_results,
        user_id=user_id
    )
    
    return jsonify({
        'score': correct_count,
        'max_score': total_questions,
        'band_score': band,
        'detailed_results': detailed_results
    })

@app.route('/api/writing/evaluate', methods=['POST'])
def evaluate_writing():
    user_id = session.get('user_id')
    data = request.json or {}
    prompt_id = data.get('prompt_id')
    prompt_title = data.get('prompt_title', 'IELTS Writing Essay')
    task_type = data.get('task_type', 'task2')
    essay_text = data.get('essay_text', '').strip()
    
    words = re.findall(r'\b\w+\b', essay_text)
    word_count = len(words)
    min_required = 150 if task_type == 'task1' else 250
    
    paragraphs = [p.strip() for p in essay_text.split('\n') if len(p.strip()) > 0]
    num_paragraphs = len(paragraphs)
    
    # 1. Task Achievement / Response
    task_response_score = 6.0
    task_feedback = []
    if word_count < min_required:
        task_response_score = max(4.0, 5.5 - ((min_required - word_count) / 50) * 0.5)
        task_feedback.append(f"Bài viết chưa đạt độ dài tối thiểu {min_required} từ (hiện tại: {word_count} từ), sẽ bị trừ điểm Task Response.")
    else:
        task_response_score = 6.5
        if word_count >= min_required + 30:
            task_response_score += 0.5
        task_feedback.append(f"Độ dài tốt ({word_count} từ), đáp ứng tiêu chuẩn phòng thi.")
        
    if num_paragraphs < 3:
        task_feedback.append("Cần phân chia đoạn văn rõ ràng (Mở bài, Thân bài 1, Thân bài 2, Kết luận).")
    else:
        task_feedback.append(f"Cấu trúc gồm {num_paragraphs} đoạn văn hợp lý.")

    # 2. Coherence & Cohesion
    cohesive_devices = [
        'furthermore', 'moreover', 'in addition', 'consequently', 'therefore',
        'nevertheless', 'on the other hand', 'in contrast', 'for instance',
        'for example', 'in conclusion', 'overall', 'admittedly', 'conversely'
    ]
    essay_lower = essay_text.lower()
    cohesive_count = sum(1 for word in cohesive_devices if word in essay_lower)
    
    coherence_score = 6.0
    coherence_feedback = []
    if cohesive_count >= 5:
        coherence_score = 7.5
        coherence_feedback.append(f"Sử dụng rất phong phú và tự nhiên các từ nối ({cohesive_count} từ nối học thuật).")
    elif cohesive_count >= 3:
        coherence_score = 6.5
        coherence_feedback.append(f"Có sử dụng từ nối ({cohesive_count} từ nối), liên kết ý tương đối mượt.")
    else:
        coherence_score = 5.5
        coherence_feedback.append("Nên bổ sung thêm các liên từ học thuật (Furthermore, In contrast, Consequently, Overall...).")

    # 3. Lexical Resource
    academic_words = [
        'unprecedented', 'mitigate', 'ubiquitous', 'deteriorate', 'paramount',
        'supersede', 'indispensable', 'proliferate', 'conducive', 'detrimental',
        'exacerbate', 'equitable', 'feasible', 'subsidize', 'stringent', 'burgeoning',
        'trajectory', 'significant', 'demonstrate', 'phenomenon', 'infrastructure',
        'perspective', 'consequently', 'substantial', 'pedagogical', 'advancement'
    ]
    detected_academic = [w for w in academic_words if w in essay_lower]
    lexical_score = 6.0
    lexical_feedback = []
    if len(detected_academic) >= 6:
        lexical_score = 8.0
        lexical_feedback.append(f"Vốn từ học thuật xuất sắc! Nhận diện {len(detected_academic)} từ/cụm từ Academic C1-C2.")
    elif len(detected_academic) >= 3:
        lexical_score = 7.0
        lexical_feedback.append(f"Vốn từ tốt, có sử dụng {len(detected_academic)} từ vựng học thuật.")
    else:
        lexical_score = 5.5
        lexical_feedback.append("Nên tăng cường sử dụng các từ vựng Academic và Collocations nâng cao để đạt Band 7.0+.")

    # 4. Grammatical Range & Accuracy
    complex_indicators = [';', 'which', 'that', 'although', 'even though', 'whereas', 'while', 'if', 'unless']
    complex_count = sum(1 for ind in complex_indicators if ind in essay_lower)
    grammar_score = 6.5 if complex_count >= 4 else 6.0
    grammar_feedback = []
    if complex_count >= 6:
        grammar_score = 7.5
        grammar_feedback.append("Sử dụng kết hợp đa dạng nhiều cấu trúc câu phức, mệnh đề quan hệ và điều kiện.")
    else:
        grammar_feedback.append("Nên đa dạng hóa cấu trúc câu: câu ghép, mệnh đề quan hệ, câu điều kiện, cấu trúc bị động.")

    overall_estimated = round((task_response_score + coherence_score + lexical_score + grammar_score) / 4.0, 1)
    
    evaluation = {
        'task_response': {'score': task_response_score, 'comments': task_feedback},
        'coherence_cohesion': {'score': coherence_score, 'comments': coherence_feedback},
        'lexical_resource': {'score': lexical_score, 'comments': lexical_feedback, 'detected_academic': detected_academic},
        'grammatical_accuracy': {'score': grammar_score, 'comments': grammar_feedback},
        'overall_band': overall_estimated,
        'word_count': word_count,
        'paragraph_count': num_paragraphs
    }
    
    sub_id = save_writing_submission(
        task_type=task_type,
        prompt_id=prompt_id or 'custom',
        prompt_title=prompt_title,
        essay_text=essay_text,
        word_count=word_count,
        estimated_band=overall_estimated,
        evaluation=evaluation,
        user_id=user_id
    )
    
    return jsonify({
        'submission_id': sub_id,
        'evaluation': evaluation
    })

@app.route('/api/speaking/log', methods=['POST'])
def log_speaking():
    user_id = session.get('user_id')
    data = request.json or {}
    topic_id = data.get('topic_id', 'general')
    part = data.get('part', 'Part 2')
    question = data.get('question', '')
    duration = data.get('duration_seconds', 0)
    notes = data.get('notes', '')
    
    save_speaking_log(topic_id, part, question, duration, notes, user_id=user_id)
    return jsonify({'success': True})

@app.route('/api/vocabulary/toggle-mastery', methods=['POST'])
def toggle_mastery():
    user_id = session.get('user_id') or 1
    data = request.json or {}
    word_id = data.get('word_id')
    if not word_id:
        return jsonify({'error': 'Missing word_id'}), 400
    new_status = toggle_vocab_mastery(word_id, user_id=user_id)
    return jsonify({'word_id': word_id, 'is_mastered': bool(new_status)})

@app.route('/api/vocabulary/<word>', methods=['GET'])
def get_vocabulary_word(word):
    """
    Returns rich vocabulary definition for a specific word:
    Free Dictionary API -> Gemini AI -> Database Cache.
    """
    clean_word = word.strip().lower()
    if not clean_word:
        return jsonify({'error': 'Missing word parameter'}), 400
        
    vocab_data = get_or_fetch_vocabulary(clean_word)
    if not vocab_data:
        return jsonify({'error': f'Word "{clean_word}" could not be found'}), 404
        
    return jsonify({
        'status': 'success',
        'data': vocab_data
    })

@app.route('/api/calculator/calculate', methods=['POST'])
def calculate_band():
    data = request.json or {}
    listening_raw = float(data.get('listening_raw', 0))
    reading_raw = float(data.get('reading_raw', 0))
    reading_type = data.get('reading_type', 'academic')
    writing_band = float(data.get('writing_band', 6.0))
    speaking_band = float(data.get('speaking_band', 6.0))
    
    l_band = raw_to_listening_band(listening_raw, 40)
    
    if reading_type == 'general':
        if reading_raw >= 39: r_band = 9.0
        elif reading_raw >= 37: r_band = 8.5
        elif reading_raw >= 36: r_band = 8.0
        elif reading_raw >= 34: r_band = 7.5
        elif reading_raw >= 32: r_band = 7.0
        elif reading_raw >= 30: r_band = 6.5
        elif reading_raw >= 27: r_band = 6.0
        elif reading_raw >= 23: r_band = 5.5
        elif reading_raw >= 19: r_band = 5.0
        else: r_band = 4.0
    else:
        r_band = raw_to_reading_academic_band(reading_raw, 40)
        
    overall = calculate_overall_band(l_band, r_band, writing_band, speaking_band)
    
    return jsonify({
        'listening_band': l_band,
        'reading_band': r_band,
        'writing_band': writing_band,
        'speaking_band': speaking_band,
        'overall_band': overall
    })

@app.route('/api/dashboard/stats', methods=['GET'])
def dashboard_stats():
    user_id = session.get('user_id')
    summary = get_dashboard_summary(user_id=user_id)
    return jsonify(summary)

if __name__ == '__main__':
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    print("=" * 60)
    print(">> IELTS Master Hub dang khoi chay tai http://127.0.0.1:5000")
    print("=" * 60)
    app.run(debug=True, port=5000, host='127.0.0.1')
