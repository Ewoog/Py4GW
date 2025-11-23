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


class SignalType(Enum):
    """Signal types for bot communication."""
    READY_TO_QUEUE = 1.0
    QUEUE_NOW = 2.0
    MATCH_START = 3.0
    MATCH_END = 4.0
    MAP_VERIFY = 11.0
    WIN_COUNT = 12.0
    HEARTBEAT = 99.0  # Keep-alive signal
    STATUS_UPDATE = 100.0  # General status update


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
    
    def __init__(self, host='127.0.0.1', port=12345, buffer_size=4096):
        self.host = host
        self.port = port
        self.buffer_size = buffer_size
        self.server_socket: Optional[socket.socket] = None
        self.running = False
        self.lock = threading.Lock()
        
        # Connected clients: {client_id: (socket, address, BotState)}
        self.clients: Dict[str, Tuple[socket.socket, tuple, BotState]] = {}
        
        # Message queue for routing
        self.message_queue: List[Dict] = []
        
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
            data = client_socket.recv(self.buffer_size)
            if not data:
                self.logger.warning(f"Client {address} disconnected before registration")
                return
                
            message = json.loads(data.decode())
            
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
                
                # Now handle regular messages
                while self.running:
                    data = client_socket.recv(self.buffer_size)
                    if not data:
                        self.logger.info(f"{client_id} disconnected")
                        break
                        
                    message = json.loads(data.decode())
                    self.process_message(client_id, message)
                    
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
                
            elif msg_type in ['READY_TO_QUEUE', 'QUEUE_NOW', 'MATCH_START', 'MATCH_END', 'MAP_VERIFY', 'WIN_COUNT']:
                # Route synchronization signals to partner
                self.route_signal(sender_id, message)
                
            else:
                self.logger.warning(f"Unknown message type from {sender_id}: {msg_type}")
                
    def route_signal(self, sender_id: str, message: Dict):
        """Route a signal from one Leader to its partner."""
        msg_type = message.get('type')
        
        with self.lock:
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
                self.send_to_client(partner_id, message)
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
            data = json.dumps(message).encode()
            client_socket.sendall(data)
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
                
    def monitor_heartbeats(self):
        """Monitor client heartbeats and disconnect stale connections."""
        while self.running:
            time.sleep(5)  # Check every 5 seconds
            
            current_time = time.time()
            stale_clients = []
            
            with self.lock:
                for client_id, (_, _, bot_state) in self.clients.items():
                    if current_time - bot_state.last_heartbeat > 30:  # 30 second timeout
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
            time.sleep(10)  # Print status every 10 seconds
            
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
