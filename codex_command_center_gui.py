#!/usr/bin/env python3
"""
Command Center GUI - Web-based interface for monitoring and controlling Codex Arena bots.

This provides a visual dashboard with:
- Real-time bot status display
- Manual control buttons (Resign, Switch Teams)
- Command history log
- Connection status

Usage:
    1. Start the Command Center server:
       python codex_command_center.py
    
    2. Start the GUI in another terminal:
       python codex_command_center_gui.py
    
    3. Open browser to http://localhost:5000
"""

from flask import Flask, render_template, jsonify, request
import socket
import json
import time
import threading
from datetime import datetime

app = Flask(__name__)

# GUI state
gui_state = {
    'bots': {},
    'last_update': None,
    'command_history': [],
    'connected': False
}

# Connect to Command Center as a monitoring client
cc_socket = None
cc_lock = threading.Lock()


def connect_to_command_center(host='127.0.0.1', port=12345):
    """Connect to the Command Center for monitoring."""
    global cc_socket, gui_state
    
    try:
        cc_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cc_socket.connect((host, port))
        
        # Register as GUI client
        registration = {
            'type': 'REGISTER',
            'bot_id': 'GUI_Monitor',
            'is_winning_team': False,  # Not a real bot
            'is_gui': True
        }
        cc_socket.sendall(json.dumps(registration).encode())
        
        # Wait for ACK
        data = cc_socket.recv(4096)
        response = json.loads(data.decode())
        
        if response.get('type') == 'REGISTER_ACK':
            gui_state['connected'] = True
            print("Connected to Command Center!")
            return True
        else:
            print("Failed to register with Command Center")
            return False
            
    except Exception as e:
        print(f"Failed to connect to Command Center: {e}")
        gui_state['connected'] = False
        return False


def send_command(command_type, **kwargs):
    """Send a command through the Command Center."""
    global cc_socket
    
    if not cc_socket or not gui_state['connected']:
        return {'success': False, 'error': 'Not connected to Command Center'}
    
    try:
        message = {
            'type': f'GUI_{command_type}',
            'timestamp': time.time(),
            **kwargs
        }
        
        with cc_lock:
            cc_socket.sendall(json.dumps(message).encode())
        
        # Log command
        gui_state['command_history'].insert(0, {
            'time': datetime.now().strftime('%H:%M:%S'),
            'command': command_type,
            'params': kwargs
        })
        
        # Keep only last 50 commands
        gui_state['command_history'] = gui_state['command_history'][:50]
        
        return {'success': True}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}


@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('command_center.html')


@app.route('/api/status')
def get_status():
    """Get current bot status."""
    return jsonify(gui_state)


@app.route('/api/command/resign', methods=['POST'])
def command_resign():
    """Issue resign command to both bots."""
    result = send_command('RESIGN', reason='manual_gui_command')
    return jsonify(result)


@app.route('/api/command/switch_teams', methods=['POST'])
def command_switch_teams():
    """Issue switch teams command."""
    result = send_command('SWITCH_TEAMS')
    return jsonify(result)


@app.route('/api/command/queue', methods=['POST'])
def command_queue():
    """Force both bots to queue now."""
    result = send_command('FORCE_QUEUE')
    return jsonify(result)


def create_html_template():
    """Create the HTML template for the GUI."""
    html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Command Center - Codex Arena Bot Control</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            padding: 20px;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        header {
            text-align: center;
            padding: 20px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 10px;
            margin-bottom: 20px;
        }
        
        h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }
        
        .status-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
        }
        
        .status-connected {
            background: #10b981;
        }
        
        .status-disconnected {
            background: #ef4444;
        }
        
        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .panel {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        }
        
        .panel h2 {
            margin-bottom: 15px;
            font-size: 1.5em;
            border-bottom: 2px solid rgba(255,255,255,0.3);
            padding-bottom: 10px;
        }
        
        .bot-card {
            background: rgba(0, 0, 0, 0.3);
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
        }
        
        .bot-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .bot-name {
            font-size: 1.2em;
            font-weight: bold;
        }
        
        .team-badge {
            padding: 3px 10px;
            border-radius: 15px;
            font-size: 0.85em;
        }
        
        .team-winning {
            background: #fbbf24;
            color: #000;
        }
        
        .team-losing {
            background: #6366f1;
        }
        
        .bot-stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            font-size: 0.9em;
        }
        
        .stat {
            display: flex;
            justify-content: space-between;
        }
        
        .stat-label {
            opacity: 0.8;
        }
        
        .stat-value {
            font-weight: bold;
        }
        
        .controls {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        
        .btn {
            padding: 15px 20px;
            font-size: 1em;
            font-weight: bold;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }
        
        .btn:active {
            transform: translateY(0);
        }
        
        .btn-resign {
            background: linear-gradient(135deg, #ef4444, #dc2626);
            color: white;
        }
        
        .btn-switch {
            background: linear-gradient(135deg, #8b5cf6, #7c3aed);
            color: white;
        }
        
        .btn-queue {
            background: linear-gradient(135deg, #10b981, #059669);
            color: white;
        }
        
        .log-container {
            background: rgba(0, 0, 0, 0.5);
            padding: 15px;
            border-radius: 8px;
            height: 300px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 0.85em;
        }
        
        .log-entry {
            padding: 5px;
            margin-bottom: 5px;
            border-left: 3px solid #8b5cf6;
            padding-left: 10px;
        }
        
        .log-time {
            color: #fbbf24;
            margin-right: 10px;
        }
        
        .log-command {
            color: #10b981;
            font-weight: bold;
        }
        
        @keyframes pulse {
            0%, 100% {
                opacity: 1;
            }
            50% {
                opacity: 0.5;
            }
        }
        
        .in-match {
            animation: pulse 2s infinite;
        }
        
        .full-width {
            grid-column: 1 / -1;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>⚔️ Codex Arena Command Center ⚔️</h1>
            <span class="status-badge" id="connectionStatus">
                <span id="statusText">Connecting...</span>
            </span>
        </header>
        
        <div class="grid">
            <!-- Bot Status Panel -->
            <div class="panel">
                <h2>📊 Bot Status</h2>
                <div id="botList">
                    <p style="opacity: 0.6; text-align: center;">No bots connected</p>
                </div>
            </div>
            
            <!-- Manual Controls Panel -->
            <div class="panel">
                <h2>🎮 Manual Controls</h2>
                <div class="controls">
                    <button class="btn btn-resign" onclick="sendCommand('resign')">
                        ⚠️ Force Resign
                    </button>
                    <button class="btn btn-switch" onclick="sendCommand('switch_teams')">
                        🔄 Switch Teams
                    </button>
                    <button class="btn btn-queue" onclick="sendCommand('queue')">
                        ▶️ Force Queue
                    </button>
                </div>
                
                <div style="margin-top: 20px; padding: 15px; background: rgba(0,0,0,0.3); border-radius: 8px;">
                    <h3 style="margin-bottom: 10px;">Command Reference:</h3>
                    <ul style="list-style: none; font-size: 0.9em; line-height: 1.8;">
                        <li><strong>Force Resign:</strong> Both teams resign immediately</li>
                        <li><strong>Switch Teams:</strong> Swap winning/losing team roles</li>
                        <li><strong>Force Queue:</strong> Command both teams to queue now</li>
                    </ul>
                </div>
            </div>
            
            <!-- Command History Panel -->
            <div class="panel full-width">
                <h2>📜 Command History</h2>
                <div class="log-container" id="commandLog">
                    <p style="opacity: 0.6;">Command history will appear here...</p>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let updateInterval;
        
        function updateStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    updateConnectionStatus(data.connected);
                    updateBotList(data.bots);
                    updateCommandLog(data.command_history);
                })
                .catch(error => {
                    console.error('Error fetching status:', error);
                    updateConnectionStatus(false);
                });
        }
        
        function updateConnectionStatus(connected) {
            const badge = document.getElementById('connectionStatus');
            const text = document.getElementById('statusText');
            
            if (connected) {
                badge.className = 'status-badge status-connected';
                text.textContent = '🟢 Connected';
            } else {
                badge.className = 'status-badge status-disconnected';
                text.textContent = '🔴 Disconnected';
            }
        }
        
        function updateBotList(bots) {
            const container = document.getElementById('botList');
            
            if (!bots || Object.keys(bots).length === 0) {
                container.innerHTML = '<p style="opacity: 0.6; text-align: center;">No bots connected</p>';
                return;
            }
            
            let html = '';
            for (const [botId, bot] of Object.entries(bots)) {
                const teamClass = bot.is_winning_team ? 'team-winning' : 'team-losing';
                const teamLabel = bot.is_winning_team ? 'Winning' : 'Losing';
                const matchClass = bot.in_match ? 'in-match' : '';
                
                html += `
                    <div class="bot-card ${matchClass}">
                        <div class="bot-header">
                            <span class="bot-name">${botId}</span>
                            <span class="team-badge ${teamClass}">${teamLabel}</span>
                        </div>
                        <div class="bot-stats">
                            <div class="stat">
                                <span class="stat-label">Consecutive Wins:</span>
                                <span class="stat-value">${bot.consecutive_wins || 0}</span>
                            </div>
                            <div class="stat">
                                <span class="stat-label">Strongboxes:</span>
                                <span class="stat-value">${bot.strongboxes_earned || 0}</span>
                            </div>
                            <div class="stat">
                                <span class="stat-label">In Match:</span>
                                <span class="stat-value">${bot.in_match ? '✓ Yes' : '✗ No'}</span>
                            </div>
                            <div class="stat">
                                <span class="stat-label">Map ID:</span>
                                <span class="stat-value">${bot.current_map_id || 'N/A'}</span>
                            </div>
                        </div>
                    </div>
                `;
            }
            
            container.innerHTML = html;
        }
        
        function updateCommandLog(history) {
            const container = document.getElementById('commandLog');
            
            if (!history || history.length === 0) {
                container.innerHTML = '<p style="opacity: 0.6;">Command history will appear here...</p>';
                return;
            }
            
            let html = '';
            for (const entry of history) {
                const params = JSON.stringify(entry.params || {});
                html += `
                    <div class="log-entry">
                        <span class="log-time">[${entry.time}]</span>
                        <span class="log-command">${entry.command}</span>
                        ${params !== '{}' ? `<span style="opacity: 0.7;"> ${params}</span>` : ''}
                    </div>
                `;
            }
            
            container.innerHTML = html;
        }
        
        function sendCommand(commandType) {
            fetch(`/api/command/${commandType}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    console.log(`Command ${commandType} sent successfully`);
                    updateStatus(); // Refresh immediately
                } else {
                    alert(`Failed to send command: ${data.error || 'Unknown error'}`);
                }
            })
            .catch(error => {
                console.error('Error sending command:', error);
                alert('Failed to send command - check connection');
            });
        }
        
        // Start updating
        updateStatus();
        updateInterval = setInterval(updateStatus, 1000); // Update every second
    </script>
</body>
</html>
"""
    return html


def save_template():
    """Save the HTML template to templates folder."""
    import os
    
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    with open('templates/command_center.html', 'w') as f:
        f.write(create_html_template())
    
    print("HTML template created at templates/command_center.html")


if __name__ == '__main__':
    print("=" * 60)
    print("Codex Arena Bot - Command Center GUI")
    print("=" * 60)
    print()
    
    # Save HTML template
    save_template()
    
    # Try to connect to Command Center
    print("Connecting to Command Center...")
    if connect_to_command_center():
        print("✓ Connected successfully!")
    else:
        print("⚠ Not connected - make sure Command Center is running")
        print("  Start it with: python codex_command_center.py")
    
    print()
    print("Starting web server...")
    print("Open your browser to: http://localhost:5000")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    app.run(debug=False, host='0.0.0.0', port=5000)
