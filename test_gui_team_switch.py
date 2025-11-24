#!/usr/bin/env python3
"""
Test script to verify the GUI receives team switch updates from Command Center.

This script simulates two bots connecting, then sends a team switch command
via the GUI interface to verify the GUI properly detects and displays the change.

Usage:
    1. Start the Command Center in one terminal:
       python codex_command_center.py
    
    2. Run this test script in another terminal:
       python test_gui_team_switch.py
"""

import time
import socket
import json
from codex_socket_client import SocketClient


def test_gui_team_switch():
    """Test that GUI receives and displays team switch updates."""
    
    print("=" * 60)
    print("Testing GUI Team Switch Detection")
    print("=" * 60)
    print()
    
    # Create two bot clients
    print("1. Connecting two test bots to Command Center...")
    
    bot1 = SocketClient(
        bot_id="TestBot1",
        is_winning_team=True,
        host="127.0.0.1",
        port=12345
    )
    
    bot2 = SocketClient(
        bot_id="TestBot2",
        is_winning_team=False,
        host="127.0.0.1",
        port=12345
    )
    
    if not bot1.connect():
        print("   ✗ Failed to connect Bot1!")
        return False
    print("   ✓ Bot1 connected (Winning team)")
    
    if not bot2.connect():
        print("   ✗ Failed to connect Bot2!")
        bot1.disconnect()
        return False
    print("   ✓ Bot2 connected (Losing team)")
    
    # Send initial state updates
    print("\n2. Sending initial state updates...")
    bot1.update_state(consecutive_wins=3, strongboxes_earned=0, in_match=False, current_map_id=796)
    bot2.update_state(consecutive_wins=0, strongboxes_earned=0, in_match=False, current_map_id=796)
    time.sleep(0.5)
    print("   ✓ Initial states sent")
    
    # Create a GUI client to send the switch teams command
    print("\n3. Connecting GUI client to send switch teams command...")
    gui_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    gui_socket.connect(("127.0.0.1", 12345))
    
    # Register as GUI
    registration = {
        'type': 'REGISTER',
        'bot_id': 'GUI_Test',
        'is_winning_team': False,
        'is_gui': True
    }
    gui_socket.sendall((json.dumps(registration) + '\n').encode())
    
    # Wait for ACK
    buffer = b''
    while b'\n' not in buffer:
        data = gui_socket.recv(4096)
        if not data:
            print("   ✗ Connection closed before registration ACK")
            return False
        buffer += data
    
    message_data, _ = buffer.split(b'\n', 1)
    response = json.loads(message_data.decode())
    
    if response.get('type') != 'REGISTER_ACK':
        print("   ✗ Failed to register GUI")
        return False
    print("   ✓ GUI client connected")
    
    # Send switch teams command
    print("\n4. Sending SWITCH_TEAMS command from GUI...")
    switch_cmd = {
        'type': 'GUI_SWITCH_TEAMS',
        'timestamp': time.time()
    }
    gui_socket.sendall((json.dumps(switch_cmd) + '\n').encode())
    print("   ✓ Switch teams command sent")
    
    # Listen for state updates on GUI socket
    print("\n5. Waiting for bot state updates on GUI client...")
    gui_socket.settimeout(5.0)
    
    updates_received = {}
    buffer = b''
    
    try:
        while len(updates_received) < 2:
            data = gui_socket.recv(4096)
            if not data:
                break
            
            buffer += data
            
            while b'\n' in buffer:
                message_data, buffer = buffer.split(b'\n', 1)
                if message_data:
                    try:
                        message = json.loads(message_data.decode())
                        if message.get('type') == 'BOT_STATE_UPDATE':
                            bot_id = message.get('bot_id')
                            bot_state = message.get('bot_state')
                            updates_received[bot_id] = bot_state
                            
                            team = "Winning" if bot_state.get('is_winning_team') else "Losing"
                            print(f"   ✓ Received update for {bot_id}: {team} team")
                    except json.JSONDecodeError:
                        pass
    except socket.timeout:
        pass
    
    gui_socket.close()
    
    # Verify the updates
    print("\n6. Verifying team switch results...")
    
    success = True
    
    if 'TestBot1' not in updates_received:
        print("   ✗ No update received for TestBot1")
        success = False
    elif updates_received['TestBot1'].get('is_winning_team') == False:
        print("   ✓ TestBot1 switched to Losing team (was Winning)")
    else:
        print("   ✗ TestBot1 still showing as Winning team")
        success = False
    
    if 'TestBot2' not in updates_received:
        print("   ✗ No update received for TestBot2")
        success = False
    elif updates_received['TestBot2'].get('is_winning_team') == True:
        print("   ✓ TestBot2 switched to Winning team (was Losing)")
    else:
        print("   ✗ TestBot2 still showing as Losing team")
        success = False
    
    # Verify bots received the CMD_SWITCH_TEAMS command
    print("\n7. Checking if bots received CMD_SWITCH_TEAMS...")
    
    bot1_received = False
    bot2_received = False
    
    # Check bot1's messages
    for _ in range(5):
        msg = bot1.get_next_message(timeout=0.2)
        if msg and msg.get('type') == 'CMD_SWITCH_TEAMS':
            new_role = msg.get('new_role')
            print(f"   ✓ TestBot1 received CMD_SWITCH_TEAMS: {new_role}")
            bot1_received = True
            break
    
    # Check bot2's messages
    for _ in range(5):
        msg = bot2.get_next_message(timeout=0.2)
        if msg and msg.get('type') == 'CMD_SWITCH_TEAMS':
            new_role = msg.get('new_role')
            print(f"   ✓ TestBot2 received CMD_SWITCH_TEAMS: {new_role}")
            bot2_received = True
            break
    
    if not bot1_received:
        print("   ✗ TestBot1 did not receive CMD_SWITCH_TEAMS")
        success = False
    
    if not bot2_received:
        print("   ✗ TestBot2 did not receive CMD_SWITCH_TEAMS")
        success = False
    
    # Cleanup
    print("\n8. Cleaning up...")
    bot1.disconnect()
    bot2.disconnect()
    print("   ✓ Test bots disconnected")
    
    # Final result
    print("\n" + "=" * 60)
    if success:
        print("TEST PASSED ✓")
        print("The GUI properly receives team switch updates!")
    else:
        print("TEST FAILED ✗")
        print("Some issues were detected.")
    print("=" * 60)
    
    return success


if __name__ == '__main__':
    print("\nMake sure the Command Center is running first!")
    print("Start it with: python codex_command_center.py")
    print()
    print("Press Enter to start the test...")
    input()
    
    result = test_gui_team_switch()
    exit(0 if result else 1)
