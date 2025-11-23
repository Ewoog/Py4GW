#!/usr/bin/env python3
"""
Codex Arena Bot Command Center - Unified Version with Optional GUI

This script combines the Command Center server and Tkinter GUI in a single file.
Run without --gui for headless server mode, or with --gui for the visual interface.

Features:
- Central hub for leader-to-leader communication
- Intelligent coordination (queue timing, map verification)
- Real-time monitoring of bot states
- Optional Tkinter GUI for manual control
- Event logging and diagnostics

Usage:
    python codex_command_center_with_gui.py [--host HOST] [--port PORT] [--gui]
    
    --gui: Launch with graphical interface (default: headless server)
    Default: HOST=127.0.0.1, PORT=12345

Examples:
    python codex_command_center_with_gui.py              # Headless server
    python codex_command_center_with_gui.py --gui         # With GUI
    python codex_command_center_with_gui.py --gui --port 8888  # Custom port with GUI
"""

import socket
import threading
import json
import time
import argparse
import logging
from datetime import datetime
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# Try to import tkinter for GUI mode
TKINTER_AVAILABLE = False
try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext, messagebox
    TKINTER_AVAILABLE = True
except ImportError:
    pass

# Configuration constants
DEFAULT_HEARTBEAT_TIMEOUT = 30  # seconds - time before considering a client disconnected
DEFAULT_STATUS_INTERVAL = 10  # seconds - interval for printing status updates


class SignalType(Enum):
    """Signal types for bot communication."""
    # Bot to CC signals
    READY_TO_QUEUE = 1.0
    QUEUE_NOW = 2.0  # Deprecated - CC now sends this
    MATCH_START = 3.0
    MATCH_END = 4.0
    MAP_VERIFY = 11.0
    WIN_COUNT = 12.0
    HEARTBEAT = 99.0  # Keep-alive signal
    STATUS_UPDATE = 100.0  # General status update
    
    # CC to Bot commands
    CMD_QUEUE_NOW = 200.0  # CC tells bots to queue
    CMD_MATCH_CONFIRMED = 201.0  # CC confirms maps match
    CMD_RESIGN = 202.0  # CC tells bots to resign (desync detected)


@dataclass
class BotState:
    """Represents the state of a connected bot."""
    bot_id: str
    is_winning_team: bool
    consecutive_wins: int
    strongboxes_earned: int
    in_match: bool
    current_map_id: int
    last_heartbeat: float
    connected_at: float
    last_signal: Optional[str] = None
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class CommandCenter:
    """Central command center for coordinating Codex Arena bots."""
    
    def __init__(self, host='127.0.0.1', port=12345, buffer_size=4096, 
                 heartbeat_timeout=DEFAULT_HEARTBEAT_TIMEOUT, 
                 status_interval=DEFAULT_STATUS_INTERVAL):
        self.host = host
        self.port = port
        self.buffer_size = buffer_size
        self.heartbeat_timeout = heartbeat_timeout
        self.status_interval = status_interval
        self.server_socket: Optional[socket.socket] = None
        self.running = False
        self.lock = threading.Lock()
        
        # Connected clients: {client_id: (socket, address, BotState)}
        self.clients: Dict[str, Tuple[socket.socket, tuple, BotState]] = {}
        
        # Message queue for routing
        self.message_queue: List[Dict] = []
        
        # Coordination state
        self.ready_to_queue: set = set()  # Set of client_ids ready to queue
        self.map_verifications: Dict[str, int] = {}  # {client_id: map_id}
        
        # Setup logging
        self.setup_logging()
        
    def setup_logging(self):
        """Configure logging for the command center."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('codex_command_center.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('CommandCenter')
        
    def start_server(self):
        """Start the TCP server and bind to the specified host and port."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)  # Allow up to 5 connections
            self.running = True
            self.logger.info(f"Command Center started on {self.host}:{self.port}")
            self.logger.info("Waiting for Leader bots to connect...")
        except socket.error as e:
            self.logger.error(f"Error starting server: {e}")
            raise
            
    def accept_connections(self):
        """Accept incoming connections from Leader bots."""
        while self.running:
            try:
                self.server_socket.settimeout(1.0)  # Timeout to check running flag
                client_socket, address = self.server_socket.accept()
                self.logger.info(f"New connection from {address}")
                
                # Start a thread to handle this client
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, address),
                    daemon=True
                )
                client_thread.start()
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error accepting connection: {e}")
                    
    def handle_client(self, client_socket: socket.socket, address: tuple):
        """Handle communication with a connected client."""
        client_id = None
        
        try:
            # First message should be a registration with bot details
            # Use buffer to handle newline-delimited messages from the start
            buffer = b''
            while b'\n' not in buffer:
                data = client_socket.recv(self.buffer_size)
                if not data:
                    self.logger.warning(f"Client {address} disconnected before registration")
                    return
                buffer += data
            
            message_data, buffer = buffer.split(b'\n', 1)
            message = json.loads(message_data.decode())
            
            if message.get('type') == 'REGISTER':
                client_id = message.get('bot_id')
                is_winning_team = message.get('is_winning_team', False)
                
                # Create bot state
                bot_state = BotState(
                    bot_id=client_id,
                    is_winning_team=is_winning_team,
                    consecutive_wins=0,
                    strongboxes_earned=0,
                    in_match=False,
                    current_map_id=0,
                    last_heartbeat=time.time(),
                    connected_at=time.time()
                )
                
                with self.lock:
                    self.clients[client_id] = (client_socket, address, bot_state)
                
                self.logger.info(f"Registered {client_id} ({'Winning' if is_winning_team else 'Losing'} team) from {address}")
                
                # Send acknowledgment
                self.send_to_client(client_id, {
                    'type': 'REGISTER_ACK',
                    'message': 'Registration successful'
                })
                
                # Now handle regular messages - use a buffer for newline-delimited messages
                buffer = b''
                while self.running:
                    data = client_socket.recv(self.buffer_size)
                    if not data:
                        self.logger.info(f"{client_id} disconnected")
                        break
                    
                    # Add received data to buffer
                    buffer += data
                    
                    # Process all complete messages (delimited by newline)
                    while b'\n' in buffer:
                        message_data, buffer = buffer.split(b'\n', 1)
                        if message_data:  # Skip empty lines
                            try:
                                message = json.loads(message_data.decode())
                                self.process_message(client_id, message)
                            except json.JSONDecodeError as e:
                                self.logger.error(f"Invalid JSON from {client_id}: {e}")
                                self.logger.error(f"Data: {message_data}")
                    
                    
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON from {address}: {e}")
        except Exception as e:
            self.logger.error(f"Error handling client {client_id or address}: {e}")
        finally:
            if client_id:
                with self.lock:
                    if client_id in self.clients:
                        del self.clients[client_id]
                self.logger.info(f"Removed {client_id} from active clients")
            try:
                client_socket.close()
            except:
                pass
                
    def process_message(self, sender_id: str, message: Dict):
        """Process a message from a Leader bot."""
        msg_type = message.get('type')
        
        with self.lock:
            if sender_id not in self.clients:
                return
                
            _, _, bot_state = self.clients[sender_id]
            
            # Update last signal
            bot_state.last_signal = msg_type
            
            # Handle different message types
            if msg_type == 'HEARTBEAT':
                bot_state.last_heartbeat = time.time()
                
            elif msg_type == 'STATUS_UPDATE':
                # Update bot state from the message
                bot_state.consecutive_wins = message.get('consecutive_wins', bot_state.consecutive_wins)
                bot_state.strongboxes_earned = message.get('strongboxes_earned', bot_state.strongboxes_earned)
                bot_state.in_match = message.get('in_match', bot_state.in_match)
                bot_state.current_map_id = message.get('current_map_id', bot_state.current_map_id)
                self.logger.info(f"Status update from {sender_id}: Wins={bot_state.consecutive_wins}, Boxes={bot_state.strongboxes_earned}, InMatch={bot_state.in_match}")
                
            elif msg_type == 'READY_TO_QUEUE':
                # Leader signals they're ready to queue
                self.handle_ready_to_queue(sender_id)
                
            elif msg_type == 'MAP_VERIFY':
                # Leader sends their map ID for verification
                map_id = int(message.get('param1', 0))
                self.logger.info(f"Received MAP_VERIFY from {sender_id} with map_id={map_id}")
                self.handle_map_verify(sender_id, map_id)
                
            elif msg_type in ['MATCH_START', 'MATCH_END', 'WIN_COUNT']:
                # These still get routed to partner for informational purposes
                self.route_signal(sender_id, message)
            
            # GUI commands
            elif msg_type == 'GUI_RESIGN':
                self.logger.info("GUI commanded RESIGN for all bots")
                self.handle_gui_resign()
                
            elif msg_type == 'GUI_SWITCH_TEAMS':
                self.logger.info("GUI commanded SWITCH_TEAMS")
                self.handle_gui_switch_teams()
                
            elif msg_type == 'GUI_FORCE_QUEUE':
                self.logger.info("GUI commanded FORCE_QUEUE")
                self.handle_gui_force_queue()
                
            else:
                self.logger.warning(f"Unknown message type from {sender_id}: {msg_type}")
    
    def handle_ready_to_queue(self, sender_id: str):
        """Handle READY_TO_QUEUE signal - coordinate both leaders to queue together.
        Note: This is called from process_message which holds self.lock"""
        self.ready_to_queue.add(sender_id)
        self.logger.info(f"{sender_id} is ready to queue ({len(self.ready_to_queue)}/2 ready)")
        
        # Check if both leaders are ready
        if len(self.ready_to_queue) >= 2:
            self.logger.info("Both leaders ready! Commanding them to queue...")
            
            # Send QUEUE_NOW command to both leaders (using unlocked version since we hold the lock)
            for client_id in list(self.ready_to_queue):
                self._send_to_client_unlocked(client_id, {
                    'type': 'CMD_QUEUE_NOW',
                    'timestamp': time.time()
                })
            
            # Clear ready state for next queue cycle
            self.ready_to_queue.clear()
            self.logger.info("QUEUE_NOW commands sent to both leaders")
    
    def handle_map_verify(self, sender_id: str, map_id: int):
        """Handle MAP_VERIFY signal - verify both leaders are in same match.
        Note: This is called from process_message which holds self.lock"""
        self.map_verifications[sender_id] = map_id
        self.logger.info(f"{sender_id} is on map {map_id} ({len(self.map_verifications)}/2 verified)")
        
        # Check if both leaders have reported their maps
        if len(self.map_verifications) >= 2:
            # Get both map IDs
            map_ids = list(self.map_verifications.values())
            map1, map2 = map_ids[0], map_ids[1]
            
            if map1 == map2:
                # Maps match - confirm to both leaders
                self.logger.info(f"✓ Maps match (ID: {map1})! Confirming to both leaders...")
                
                for client_id in list(self.map_verifications.keys()):
                    self._send_to_client_unlocked(client_id, {
                        'type': 'CMD_MATCH_CONFIRMED',
                        'map_id': map1,
                        'timestamp': time.time()
                    })
                self.logger.info("Match confirmed - both leaders can proceed")
            else:
                # Maps don't match - DESYNC detected
                self.logger.warning(f"✗ DESYNC DETECTED! Maps don't match: {map1} vs {map2}")
                self.logger.warning("Commanding both leaders to resign...")
                
                for client_id in list(self.map_verifications.keys()):
                    self._send_to_client_unlocked(client_id, {
                        'type': 'CMD_RESIGN',
                        'reason': 'desync',
                        'map_ids': [map1, map2],
                        'timestamp': time.time()
                    })
                self.logger.warning("RESIGN commands sent to both leaders")
            
            # Clear map verifications for next match
            self.map_verifications.clear()
    
    def handle_gui_resign(self):
        """Handle GUI resign command - force both bots to resign."""
        self.logger.warning("GUI RESIGN command - forcing both leaders to resign...")
        
        for client_id in list(self.clients.keys()):
            if not client_id.startswith('GUI_'):  # Don't send to GUI clients
                self.send_to_client(client_id, {
                    'type': 'CMD_RESIGN',
                    'reason': 'gui_manual_command',
                    'timestamp': time.time()
                })
        
        self.logger.warning("RESIGN commands sent to all leaders")
    
    def handle_gui_switch_teams(self):
        """Handle GUI switch teams command - swap winning/losing teams."""
        self.logger.info("GUI SWITCH_TEAMS command - swapping team roles...")
        
        # Swap is_winning_team for all bots
        for client_id, (sock, addr, bot_state) in list(self.clients.items()):
            if not client_id.startswith('GUI_'):  # Don't process GUI clients
                bot_state.is_winning_team = not bot_state.is_winning_team
                new_role = "Winning" if bot_state.is_winning_team else "Losing"
                
                # Notify the bot of its new role
                self.send_to_client(client_id, {
                    'type': 'CMD_SWITCH_TEAMS',
                    'new_role': new_role,
                    'is_winning_team': bot_state.is_winning_team,
                    'timestamp': time.time()
                })
                
                self.logger.info(f"{client_id} is now {new_role} team")
        
        self.logger.info("Team switch complete")
    
    def handle_gui_force_queue(self):
        """Handle GUI force queue command - command both leaders to queue immediately."""
        self.logger.info("GUI FORCE_QUEUE command - forcing leaders to queue now...")
        
        for client_id in list(self.clients.keys()):
            if not client_id.startswith('GUI_'):  # Don't send to GUI clients
                self.send_to_client(client_id, {
                    'type': 'CMD_QUEUE_NOW',
                    'source': 'gui',
                    'timestamp': time.time()
                })
        
        # Clear ready state since we're forcing queue
        self.ready_to_queue.clear()
        self.logger.info("QUEUE_NOW commands sent to all leaders")
                
    def route_signal(self, sender_id: str, message: Dict):
        """
        Route a signal from one Leader to its partner.
        
        NOTE: This method assumes the caller already holds self.lock!
        """
        msg_type = message.get('type')
        
        if sender_id not in self.clients:
            return
            
        _, _, sender_state = self.clients[sender_id]
        
        # Find the partner (opposite team)
        partner_id = None
        for client_id, (_, _, state) in self.clients.items():
            if client_id != sender_id and state.is_winning_team != sender_state.is_winning_team:
                partner_id = client_id
                break
                
        if partner_id:
            self.logger.info(f"Routing {msg_type} from {sender_id} to {partner_id}")
            self._send_to_client_unlocked(partner_id, message)
        else:
            self.logger.warning(f"No partner found for {sender_id}, cannot route {msg_type}")
                
    def send_to_client(self, client_id: str, message: Dict):
        """Send a message to a specific client."""
        with self.lock:
            if client_id not in self.clients:
                self.logger.warning(f"Cannot send to {client_id}: not connected")
                return
                
            client_socket, _, _ = self.clients[client_id]
            
        try:
            data = json.dumps(message).encode() + b'\n'  # Add newline delimiter
            client_socket.sendall(data)
        except Exception as e:
            self.logger.error(f"Error sending to {client_id}: {e}")
    
    def _send_to_client_unlocked(self, client_id: str, message: Dict):
        """Send a message to a specific client (lock must already be held)."""
        if client_id not in self.clients:
            self.logger.warning(f"Cannot send to {client_id}: not connected")
            return
            
        client_socket, _, _ = self.clients[client_id]
        
        try:
            data = json.dumps(message).encode() + b'\n'  # Add newline delimiter
            client_socket.sendall(data)
        except Exception as e:
            self.logger.error(f"Error sending to {client_id}: {e}")
        except Exception as e:
            self.logger.error(f"Error sending to {client_id}: {e}")
            
    def broadcast(self, message: Dict, exclude: Optional[str] = None):
        """Broadcast a message to all connected clients."""
        with self.lock:
            clients_to_send = [(cid, sock) for cid, (sock, _, _) in self.clients.items() if cid != exclude]
            
        for client_id, client_socket in clients_to_send:
            try:
                data = json.dumps(message).encode()
                client_socket.sendall(data)
            except Exception as e:
                self.logger.error(f"Error broadcasting to {client_id}: {e}")
    
    def get_bot_status_for_gui(self) -> Dict:
        """Get current bot status for GUI display."""
        with self.lock:
            bots = {}
            for client_id, (_, _, bot_state) in self.clients.items():
                if not client_id.startswith('GUI_'):  # Don't include GUI clients
                    bots[client_id] = bot_state.to_dict()
            
            return bots
                
    def monitor_heartbeats(self):
        """Monitor client heartbeats and disconnect stale connections."""
        while self.running:
            time.sleep(5)  # Check every 5 seconds
            
            current_time = time.time()
            stale_clients = []
            
            with self.lock:
                for client_id, (_, _, bot_state) in self.clients.items():
                    if current_time - bot_state.last_heartbeat > self.heartbeat_timeout:
                        stale_clients.append(client_id)
                        
            for client_id in stale_clients:
                self.logger.warning(f"Client {client_id} heartbeat timeout, disconnecting")
                with self.lock:
                    if client_id in self.clients:
                        sock, _, _ = self.clients[client_id]
                        try:
                            sock.close()
                        except:
                            pass
                        del self.clients[client_id]
                        
    def print_status(self):
        """Print current status of all connected bots."""
        while self.running:
            time.sleep(self.status_interval)
            
            with self.lock:
                if not self.clients:
                    continue
                    
                self.logger.info("=" * 60)
                self.logger.info("COMMAND CENTER STATUS")
                self.logger.info("=" * 60)
                
                for client_id, (_, address, bot_state) in self.clients.items():
                    team_type = "Winning" if bot_state.is_winning_team else "Losing"
                    status = "IN MATCH" if bot_state.in_match else "IDLE"
                    uptime = int(time.time() - bot_state.connected_at)
                    
                    self.logger.info(f"{client_id} ({team_type} Team):")
                    self.logger.info(f"  Address: {address}")
                    self.logger.info(f"  Status: {status}")
                    self.logger.info(f"  Map ID: {bot_state.current_map_id}")
                    self.logger.info(f"  Consecutive Wins: {bot_state.consecutive_wins}")
                    self.logger.info(f"  Strongboxes: {bot_state.strongboxes_earned}")
                    self.logger.info(f"  Last Signal: {bot_state.last_signal}")
                    self.logger.info(f"  Uptime: {uptime}s")
                    self.logger.info("-" * 60)
                    
                self.logger.info("=" * 60)
                
    def run(self):
        """Main run loop for the command center."""
        self.start_server()
        
        # Start monitoring threads
        accept_thread = threading.Thread(target=self.accept_connections, daemon=True)
        heartbeat_thread = threading.Thread(target=self.monitor_heartbeats, daemon=True)
        status_thread = threading.Thread(target=self.print_status, daemon=True)
        
        accept_thread.start()
        heartbeat_thread.start()
        status_thread.start()
        
        self.logger.info("Command Center is running. Press Ctrl+C to stop.")
        
        try:
            # Keep main thread alive
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Shutting down Command Center...")
            self.shutdown()
            
    def shutdown(self):
        """Shutdown the command center gracefully."""
        self.running = False
        
        # Close all client connections
        with self.lock:
            for client_id, (sock, _, _) in list(self.clients.items()):
                try:
                    sock.close()
                except:
                    pass
                    
            self.clients.clear()
            
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
                
        self.logger.info("Command Center shutdown complete")



class CommandCenterGUI:
    """Tkinter GUI for Command Center control and monitoring."""
    
    def __init__(self, host='127.0.0.1', port=12345, command_center=None):
        self.host = host
        self.port = port
        self.command_center = command_center  # Direct reference to CC server
        self.connected = True  # Always connected in embedded mode
        self.running = True
        
        # Bot state
        self.bots = {}
        self.command_history = []
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("⚔️ Codex Arena Command Center ⚔️")
        self.root.geometry("900x700")
        self.root.configure(bg='#2d3748')
        
        # Style configuration
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background='#2d3748')
        style.configure('TLabel', background='#2d3748', foreground='white', font=('Arial', 10))
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'))
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'))
        style.configure('Status.TLabel', font=('Arial', 10, 'bold'))
        
        self.create_widgets()
        
        # Start update loop
        self.update_loop()
        
    def create_widgets(self):
        """Create all GUI widgets."""
        
        # Header
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        title_label = ttk.Label(header_frame, text="⚔️ Codex Arena Command Center ⚔️", 
                               style='Title.TLabel')
        title_label.pack()
        
        self.status_label = ttk.Label(header_frame, text="🔴 Disconnected", 
                                     style='Status.TLabel', foreground='#ef4444')
        self.status_label.pack()
        
        # Main content area
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left panel - Bot Status
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        ttk.Label(left_frame, text="📊 Bot Status", style='Header.TLabel').pack(anchor=tk.W)
        
        # Bot status area with scrollbar
        bot_frame = tk.Frame(left_frame, bg='#1a202c', relief=tk.SUNKEN, bd=2)
        bot_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.bot_text = scrolledtext.ScrolledText(bot_frame, height=15, width=45,
                                                   bg='#1a202c', fg='white',
                                                   font=('Courier New', 9),
                                                   relief=tk.FLAT)
        self.bot_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.bot_text.insert('1.0', 'No bots connected\n')
        self.bot_text.config(state=tk.DISABLED)
        
        # Right panel - Controls
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        ttk.Label(right_frame, text="🎮 Manual Controls", style='Header.TLabel').pack(anchor=tk.W)
        
        # Control buttons
        controls_frame = ttk.Frame(right_frame)
        controls_frame.pack(fill=tk.X, pady=5)
        
        # Resign button
        resign_btn = tk.Button(controls_frame, text="⚠️ Force Resign", 
                              bg='#ef4444', fg='white', font=('Arial', 10, 'bold'),
                              activebackground='#dc2626', cursor='hand2',
                              command=self.cmd_resign, pady=10)
        resign_btn.pack(fill=tk.X, pady=2)
        
        # Switch Teams button
        switch_btn = tk.Button(controls_frame, text="🔄 Switch Teams",
                              bg='#8b5cf6', fg='white', font=('Arial', 10, 'bold'),
                              activebackground='#7c3aed', cursor='hand2',
                              command=self.cmd_switch_teams, pady=10)
        switch_btn.pack(fill=tk.X, pady=2)
        
        # Force Queue button
        queue_btn = tk.Button(controls_frame, text="▶️ Force Queue",
                             bg='#10b981', fg='white', font=('Arial', 10, 'bold'),
                             activebackground='#059669', cursor='hand2',
                             command=self.cmd_force_queue, pady=10)
        queue_btn.pack(fill=tk.X, pady=2)
        
        # Command reference
        ref_frame = tk.LabelFrame(right_frame, text="Command Reference", 
                                 bg='#374151', fg='white', font=('Arial', 9, 'bold'))
        ref_frame.pack(fill=tk.X, pady=5)
        
        ref_text = tk.Text(ref_frame, height=6, bg='#374151', fg='white',
                          font=('Arial', 8), relief=tk.FLAT, wrap=tk.WORD)
        ref_text.pack(fill=tk.X, padx=5, pady=5)
        ref_text.insert('1.0', 
                       "• Force Resign: Both teams resign immediately\n"
                       "• Switch Teams: Swap winning/losing roles\n"
                       "• Force Queue: Command both to queue now\n\n"
                       "Commands are sent to all connected bots\n"
                       "through the Command Center.")
        ref_text.config(state=tk.DISABLED)
        
        # Bottom panel - Command Log
        log_frame = ttk.Frame(self.root)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        ttk.Label(log_frame, text="📜 Command History", style='Header.TLabel').pack(anchor=tk.W)
        
        # Log area
        log_text_frame = tk.Frame(log_frame, bg='#1a202c', relief=tk.SUNKEN, bd=2)
        log_text_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_text_frame, height=8,
                                                   bg='#1a202c', fg='#a0aec0',
                                                   font=('Courier New', 9),
                                                   relief=tk.FLAT)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_text.insert('1.0', 'Command history will appear here...\n')
        self.log_text.config(state=tk.DISABLED)
        
    def connect_to_cc(self):
        """Connect to Command Center in background thread."""
        try:
            self.cc_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.cc_socket.connect((self.host, self.port))
            
            # Register as GUI client
            registration = {
                'type': 'REGISTER',
                'bot_id': 'GUI_Monitor',
                'is_winning_team': False,
                'is_gui': True
            }
            self.cc_socket.sendall(json.dumps(registration).encode())
            
            # Wait for ACK
            data = self.cc_socket.recv(4096)
            response = json.loads(data.decode())
            
            if response.get('type') == 'REGISTER_ACK':
                self.connected = True
                self.log("Connected to Command Center!")
                
                # Start receive loop
                receive_thread = threading.Thread(target=self.receive_loop, daemon=True)
                receive_thread.start()
            else:
                self.log("Failed to register with Command Center")
                
        except Exception as e:
            self.log(f"Failed to connect: {e}")
            self.connected = False
            
    def receive_loop(self):
        """Receive messages from Command Center."""
        while self.running and self.connected:
            try:
                data = self.cc_socket.recv(4096)
                if not data:
                    self.connected = False
                    self.log("Connection closed by server")
                    break
                    
                # For now, just log received messages
                # In full implementation, this would update bot state
                
            except Exception as e:
                if self.running:
                    self.log(f"Receive error: {e}")
                    self.connected = False
                break
                
    def send_command(self, command_type, **kwargs):
        """Send a command to the Command Center."""
        if not self.command_center:
            messagebox.showerror("Error", "Command Center not available")
            return False
            
        try:
            # Call command center methods directly
            message = {
                'type': f'GUI_{command_type}',
                'timestamp': time.time(),
                **kwargs
            }
            
            # Process through command center
            self.command_center.process_message('GUI_Monitor', message)
            
            # Log command
            self.log(f"Sent: {command_type}")
            return True
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send command: {e}")
            return False
            
    def cmd_resign(self):
        """Force Resign command."""
        if messagebox.askyesno("Confirm", "Force both teams to resign?"):
            self.send_command('RESIGN', reason='manual_gui_command')
            
    def cmd_switch_teams(self):
        """Switch Teams command."""
        if messagebox.askyesno("Confirm", "Switch winning/losing team roles?"):
            self.send_command('SWITCH_TEAMS')
            
    def cmd_force_queue(self):
        """Force Queue command."""
        if messagebox.askyesno("Confirm", "Force both teams to queue now?"):
            self.send_command('FORCE_QUEUE')
            
    def log(self, message):
        """Add message to log."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_msg = f"[{timestamp}] {message}\n"
        
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert('1.0', log_msg)
        self.log_text.config(state=tk.DISABLED)
        
    def update_status_display(self):
        """Update the bot status display."""
        # Get current bot status from command center
        if self.command_center:
            self.bots = self.command_center.get_bot_status_for_gui()
        
        self.bot_text.config(state=tk.NORMAL)
        self.bot_text.delete('1.0', tk.END)
        
        if not self.bots:
            self.bot_text.insert('1.0', 'No bots connected\n\n')
            self.bot_text.insert(tk.END, 'Waiting for Leader bots to connect...')
        else:
            for bot_id, bot_info in self.bots.items():
                team = "Winning" if bot_info.get('is_winning_team') else "Losing"
                wins = bot_info.get('consecutive_wins', 0)
                boxes = bot_info.get('strongboxes_earned', 0)
                in_match = "Yes" if bot_info.get('in_match') else "No"
                map_id = bot_info.get('current_map_id', 'N/A')
                
                self.bot_text.insert(tk.END, f"{'='*40}\n")
                self.bot_text.insert(tk.END, f"{bot_id} ({team} Team)\n")
                self.bot_text.insert(tk.END, f"{'='*40}\n")
                self.bot_text.insert(tk.END, f"  Consecutive Wins: {wins}\n")
                self.bot_text.insert(tk.END, f"  Strongboxes:      {boxes}\n")
                self.bot_text.insert(tk.END, f"  In Match:         {in_match}\n")
                self.bot_text.insert(tk.END, f"  Map ID:           {map_id}\n\n")
        
        self.bot_text.config(state=tk.DISABLED)
        
    def update_loop(self):
        """Main update loop for GUI."""
        # Update connection status
        if self.connected:
            self.status_label.config(text="🟢 Connected", foreground='#10b981')
        else:
            self.status_label.config(text="🔴 Disconnected", foreground='#ef4444')
            
        # Update bot display
        self.update_status_display()
        
        # Schedule next update
        self.root.after(1000, self.update_loop)
        
    def run(self):
        """Start the GUI main loop."""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
        
    def on_closing(self):
        """Handle window closing."""
        self.running = False
        self.root.destroy()




def main():
    """Main entry point - supports both headless and GUI modes."""
    parser = argparse.ArgumentParser(
        description='Codex Arena Bot Command Center (Unified)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Headless server (default)
  %(prog)s --gui                     # With graphical interface
  %(prog)s --gui --port 8888         # GUI with custom port
  %(prog)s --host 0.0.0.0            # Listen on all interfaces
        """
    )
    
    parser.add_argument(
        '--host',
        default='127.0.0.1',
        help='Host address to bind to (default: 127.0.0.1)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=12345,
        help='Port to listen on (default: 12345)'
    )
    
    parser.add_argument(
        '--gui',
        action='store_true',
        help='Launch with graphical interface (default: headless server)'
    )
    
    args = parser.parse_args()
    
    if args.gui:
        # GUI mode
        if not TKINTER_AVAILABLE:
            print("ERROR: tkinter not available!")
            print("GUI mode requires tkinter. Install python3-tk or run without --gui flag.")
            return 1
            
        print("=" * 60)
        print("Codex Arena Bot - Command Center with GUI")
        print("=" * 60)
        print()
        print("Starting Command Center server...")
        
        # Create command center in background thread
        command_center = CommandCenter(host=args.host, port=args.port)
        
        def run_cc():
            command_center.run()
        
        cc_thread = threading.Thread(target=run_cc, daemon=True)
        cc_thread.start()
        
        # Give server time to start
        time.sleep(1)
        
        print("Starting GUI...")
        print()
        
        # Create and run GUI
        gui = CommandCenterGUI(host=args.host, port=args.port, command_center=command_center)
        try:
            gui.run()
        finally:
            command_center.shutdown()
            
    else:
        # Headless server mode
        print("=" * 60)
        print("Codex Arena Bot - Command Center (Headless)")
        print("=" * 60)
        print()
        print("Starting server...")
        print(f"Host: {args.host}")
        print(f"Port: {args.port}")
        print()
        
        command_center = CommandCenter(host=args.host, port=args.port)
        command_center.run()

if __name__ == '__main__':
    main()
