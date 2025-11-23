#!/usr/bin/env python3
"""
Codex Arena Bot Command Center

This script runs outside of Py4GW and acts as a command center to receive and send
commands to the Leader bots using TCP sockets. It provides centralized coordination,
monitoring, and control for the Codex Arena multiboxing setup.

Features:
- Central hub for leader-to-leader communication
- Real-time monitoring of bot states
- Command routing and synchronization
- Event logging and diagnostics
- Web dashboard for monitoring (optional future enhancement)

Usage:
    python codex_command_center.py [--host HOST] [--port PORT]
    
    Default: HOST=127.0.0.1, PORT=12345
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
                
                # Broadcast state update to GUI clients
                self._broadcast_bot_state_to_gui(sender_id, bot_state)
                
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
                
                # Broadcast state update to GUI clients
                self._broadcast_bot_state_to_gui(client_id, bot_state)
        
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
    
    def _broadcast_bot_state_to_gui(self, bot_id: str, bot_state: BotState):
        """
        Broadcast bot state update to all GUI clients.
        Note: This method assumes the caller already holds self.lock!
        """
        # Create state update message
        state_message = {
            'type': 'BOT_STATE_UPDATE',
            'bot_id': bot_id,
            'bot_state': bot_state.to_dict(),
            'timestamp': time.time()
        }
        
        # Send to all GUI clients
        for client_id in list(self.clients.keys()):
            if client_id.startswith('GUI_'):
                self._send_to_client_unlocked(client_id, state_message)
            
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


def main():
    """Main entry point for the command center."""
    parser = argparse.ArgumentParser(
        description='Codex Arena Bot Command Center',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Start with default settings (127.0.0.1:12345)
  %(prog)s --host 0.0.0.0 --port 8888  # Listen on all interfaces, port 8888
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
    
    args = parser.parse_args()
    
    # Create and run the command center
    command_center = CommandCenter(host=args.host, port=args.port)
    command_center.run()


if __name__ == '__main__':
    main()
