#!/usr/bin/env python3
"""
Command Center GUI - Tkinter-based interface for monitoring and controlling Codex Arena bots.

This provides a visual dashboard with:
- Real-time bot status display
- Manual control buttons (Resign, Switch Teams, Force Queue)
- Command history log
- Connection status

Requirements:
- Python 3 with tkinter (usually included)
- Command Center running on localhost:12345

Usage:
    1. Start the Command Center server:
       python codex_command_center.py
    
    2. Start the GUI:
       python codex_command_center_gui_tk.py
"""

try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext, messagebox
except ImportError:
    print("Error: tkinter not found. Please install python3-tk")
    print("On Ubuntu/Debian: sudo apt-get install python3-tk")
    print("On Windows: tkinter is included with Python")
    exit(1)

import socket
import json
import time
import threading
from datetime import datetime


class CommandCenterGUI:
    """Tkinter GUI for Command Center control and monitoring."""
    
    def __init__(self, host='127.0.0.1', port=12345):
        self.host = host
        self.port = port
        self.cc_socket = None
        self.connected = False
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
        
        # Try to connect
        self.connect_thread = threading.Thread(target=self.connect_to_cc, daemon=True)
        self.connect_thread.start()
        
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
        if not self.connected or not self.cc_socket:
            messagebox.showerror("Error", "Not connected to Command Center")
            return False
            
        try:
            message = {
                'type': f'GUI_{command_type}',
                'timestamp': time.time(),
                **kwargs
            }
            
            self.cc_socket.sendall(json.dumps(message).encode())
            
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
        if self.cc_socket:
            try:
                self.cc_socket.close()
            except:
                pass
        self.root.destroy()


def main():
    """Main entry point."""
    print("=" * 60)
    print("Codex Arena Bot - Command Center GUI (Tkinter)")
    print("=" * 60)
    print()
    print("Starting GUI...")
    print("Make sure Command Center is running:")
    print("  python codex_command_center.py")
    print()
    
    gui = CommandCenterGUI()
    gui.run()


if __name__ == '__main__':
    main()
