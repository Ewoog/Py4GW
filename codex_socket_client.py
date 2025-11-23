"""
Socket Client for Codex Arena Bot

This module provides socket-based communication with the external Command Center.
It can be used as an alternative to the shared memory (ShMem) communication system.

Usage in Codex_Arena_Bot.py:
    from codex_socket_client import SocketClient, enable_socket_mode
    
    # Enable socket mode (this will replace ShMem calls)
    enable_socket_mode(bot_id="Leader1", is_winning_team=True, host="127.0.0.1", port=12345)
"""

import socket
import json
import threading
import time
import logging
from typing import Optional, Dict, Callable
from queue import Queue, Empty


# Configuration constants
DEFAULT_HEARTBEAT_INTERVAL = 5  # seconds - interval between heartbeat messages
DEFAULT_REGISTRATION_TIMEOUT = 5.0  # seconds - timeout for registration


class SocketClient:
    """Socket client for communicating with the Command Center."""
    
    def __init__(self, bot_id: str, is_winning_team: bool, host='127.0.0.1', port=12345,
                 heartbeat_interval=DEFAULT_HEARTBEAT_INTERVAL,
                 registration_timeout=DEFAULT_REGISTRATION_TIMEOUT):
        self.bot_id = bot_id
        self.is_winning_team = is_winning_team
        self.host = host
        self.port = port
        self.heartbeat_interval = heartbeat_interval
        self.registration_timeout = registration_timeout
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.running = False
        
        # Thread for receiving messages
        self.receive_thread: Optional[threading.Thread] = None
        self.heartbeat_thread: Optional[threading.Thread] = None
        
        # Message queue for incoming messages
        self.message_queue = Queue()
        
        # Callbacks for different message types
        self.callbacks: Dict[str, Callable] = {}
        
        # Setup logging
        self.logger = logging.getLogger(f'SocketClient-{bot_id}')
        
        # Bot state to send to command center
        self.state = {
            'consecutive_wins': 0,
            'strongboxes_earned': 0,
            'in_match': False,
            'current_map_id': 0
        }
        
    def connect(self) -> bool:
        """Connect to the Command Center."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            self.running = True
            
            # Send registration message
            self.send_message({
                'type': 'REGISTER',
                'bot_id': self.bot_id,
                'is_winning_team': self.is_winning_team
            })
            
            # Wait for registration acknowledgment
            self.socket.settimeout(self.registration_timeout)
            data = self.socket.recv(4096)
            response = json.loads(data.decode())
            
            if response.get('type') == 'REGISTER_ACK':
                self.logger.info(f"Connected to Command Center at {self.host}:{self.port}")
                self.socket.settimeout(None)  # Reset to blocking mode
                
                # Start receive and heartbeat threads
                self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
                self.receive_thread.start()
                
                self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
                self.heartbeat_thread.start()
                
                return True
            else:
                self.logger.error("Registration failed")
                self.disconnect()
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to connect to Command Center: {e}")
            self.connected = False
            return False
            
    def disconnect(self):
        """Disconnect from the Command Center."""
        self.running = False
        self.connected = False
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
            
        self.logger.info("Disconnected from Command Center")
        
    def send_message(self, message: Dict):
        """Send a message to the Command Center."""
        if not self.connected or not self.socket:
            self.logger.warning("Cannot send message: not connected")
            return False
            
        try:
            data = json.dumps(message).encode() + b'\n'  # Add newline delimiter
            self.socket.sendall(data)
            return True
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            self.disconnect()
            return False
            
    def send_signal(self, signal_type: str, param1: float = 0.0):
        """Send a synchronization signal to the Command Center."""
        message = {
            'type': signal_type,
            'param1': param1,
            'timestamp': time.time()
        }
        return self.send_message(message)
        
    def update_state(self, **kwargs):
        """Update bot state and send to Command Center."""
        self.state.update(kwargs)
        
        message = {
            'type': 'STATUS_UPDATE',
            **self.state,
            'timestamp': time.time()
        }
        return self.send_message(message)
        
    def register_callback(self, message_type: str, callback: Callable):
        """Register a callback for a specific message type."""
        self.callbacks[message_type] = callback
        
    def get_next_message(self, timeout: Optional[float] = None) -> Optional[Dict]:
        """Get the next message from the queue."""
        try:
            return self.message_queue.get(timeout=timeout)
        except Empty:
            return None
            
    def _receive_loop(self):
        """Continuously receive messages from the Command Center."""
        buffer = b''
        while self.running and self.connected:
            try:
                data = self.socket.recv(4096)
                if not data:
                    self.logger.warning("Connection closed by server")
                    self.disconnect()
                    break
                
                # Add received data to buffer
                buffer += data
                
                # Process all complete messages (delimited by newline)
                while b'\n' in buffer:
                    message_data, buffer = buffer.split(b'\n', 1)
                    if message_data:  # Skip empty lines
                        try:
                            message = json.loads(message_data.decode())
                            
                            # Put message in queue
                            self.message_queue.put(message)
                            
                            # Call registered callback if exists
                            msg_type = message.get('type')
                            if msg_type in self.callbacks:
                                try:
                                    self.callbacks[msg_type](message)
                                except Exception as e:
                                    self.logger.error(f"Error in callback for {msg_type}: {e}")
                        except json.JSONDecodeError as e:
                            self.logger.error(f"Invalid JSON received: {e}")
                            self.logger.error(f"Data: {message_data}")
                        
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error in receive loop: {e}")
                    self.disconnect()
                break
                
    def _heartbeat_loop(self):
        """Send periodic heartbeats to keep connection alive."""
        while self.running and self.connected:
            time.sleep(self.heartbeat_interval)
            self.send_message({'type': 'HEARTBEAT'})


# Global socket client instance
_global_client: Optional[SocketClient] = None
_socket_mode_enabled = False


def enable_socket_mode(bot_id: str, is_winning_team: bool, host='127.0.0.1', port=12345) -> bool:
    """
    Enable socket mode for the bot.
    
    This should be called once during bot initialization to connect to the Command Center.
    
    Args:
        bot_id: Unique identifier for this bot (e.g., "Leader1", "Leader2")
        is_winning_team: Whether this is the winning team leader
        host: Command Center host address
        port: Command Center port
        
    Returns:
        True if connection successful, False otherwise
    """
    global _global_client, _socket_mode_enabled
    
    _global_client = SocketClient(bot_id, is_winning_team, host, port)
    if _global_client.connect():
        _socket_mode_enabled = True
        return True
    else:
        _global_client = None
        _socket_mode_enabled = False
        return False


def disable_socket_mode():
    """Disable socket mode and disconnect from Command Center."""
    global _global_client, _socket_mode_enabled
    
    if _global_client:
        _global_client.disconnect()
        _global_client = None
        
    _socket_mode_enabled = False


def is_socket_mode_enabled() -> bool:
    """Check if socket mode is enabled."""
    return _socket_mode_enabled and _global_client is not None and _global_client.connected


def get_client() -> Optional[SocketClient]:
    """Get the global socket client instance."""
    return _global_client


def send_sync_signal_socket(signal_type: str, param1: float = 0.0):
    """
    Send synchronization signal via socket (alternative to ShMem).
    
    This function can replace send_sync_signal() when socket mode is enabled.
    """
    if not is_socket_mode_enabled():
        return
        
    _global_client.send_signal(signal_type, param1)


def check_sync_signal_socket() -> tuple[str, int]:
    """
    Check for synchronization signals via socket (alternative to ShMem).
    
    This function can replace check_sync_signal() when socket mode is enabled.
    
    Returns:
        Tuple of (signal_type, param_value)
    """
    if not is_socket_mode_enabled():
        return ("", 0)
        
    message = _global_client.get_next_message(timeout=0.1)
    
    if message:
        signal_type = message.get('type', '')
        param1 = message.get('param1', 0.0)
        return (signal_type, int(param1))
    
    return ("", 0)


def update_bot_state_socket(**kwargs):
    """
    Update bot state and send to Command Center.
    
    Args:
        consecutive_wins: Current consecutive wins
        strongboxes_earned: Total strongboxes earned
        in_match: Whether currently in a match
        current_map_id: Current map ID
    """
    if not is_socket_mode_enabled():
        return
        
    _global_client.update_state(**kwargs)
