#!/usr/bin/env python3
"""
Test script for the Codex Arena Bot Command Center.

This script creates two simulated Leader bots and tests their communication
through the Command Center.

Usage:
    1. Start the Command Center in one terminal:
       python codex_command_center.py
    
    2. Run this test script in another terminal:
       python test_command_center.py
"""

import time
import threading
from codex_socket_client import SocketClient


# Test configuration constants
TIMEOUT_SECONDS = 10  # Standard timeout for waiting on messages


def simulate_winning_leader():
    """Simulate the winning team leader bot."""
    client = SocketClient(
        bot_id="TestLeader1",
        is_winning_team=True,
        host="127.0.0.1",
        port=12345
    )
    
    print("[Leader1] Connecting to Command Center...")
    if not client.connect():
        print("[Leader1] Failed to connect!")
        return
    
    print("[Leader1] Connected successfully!")
    
    # Simulate a match cycle
    time.sleep(2)
    
    print("[Leader1] Sending READY_TO_QUEUE signal...")
    client.send_signal("READY_TO_QUEUE")
    
    # Wait for Command Center to tell us to queue
    print("[Leader1] Waiting for Command Center to coordinate queue...")
    timeout = TIMEOUT_SECONDS
    start = time.time()
    queue_command_received = False
    while time.time() - start < timeout:
        msg = client.get_next_message(timeout=0.5)
        if msg and msg.get('type') == 'CMD_QUEUE_NOW':
            print("[Leader1] ✓ Received CMD_QUEUE_NOW from Command Center!")
            queue_command_received = True
            break
    
    if not queue_command_received:
        print("[Leader1] Timeout waiting for queue command!")
        return
    
    print("[Leader1] Entering match...")
    client.update_state(in_match=True, current_map_id=829)
    time.sleep(1)
    
    print("[Leader1] Sending MATCH_START signal...")
    client.send_signal("MATCH_START")
    time.sleep(1)
    
    print("[Leader1] Sending MAP_VERIFY signal (map 829)...")
    client.send_signal("MAP_VERIFY", param1=829.0)
    
    # Wait for Command Center's match confirmation or resign command
    print("[Leader1] Waiting for Command Center's match verification...")
    timeout = TIMEOUT_SECONDS
    start = time.time()
    while time.time() - start < timeout:
        msg = client.get_next_message(timeout=0.5)
        if msg:
            msg_type = msg.get('type')
            if msg_type == 'CMD_MATCH_CONFIRMED':
                map_id = msg.get('map_id', 0)
                print(f"[Leader1] ✓ Command Center confirmed match (Map ID: {map_id})")
                break
            elif msg_type == 'CMD_RESIGN':
                reason = msg.get('reason', 'unknown')
                map_ids = msg.get('map_ids', [])
                print(f"[Leader1] ✗ Command Center ordered RESIGN - {reason}: maps {map_ids}")
                print("[Leader1] Would resign here in real scenario")
                break
    
    # Simulate winning
    time.sleep(2)
    print("[Leader1] Match won! Updating state...")
    client.update_state(consecutive_wins=1, in_match=False)
    time.sleep(1)
    
    print("[Leader1] Sending WIN_COUNT signal (1 win)...")
    client.send_signal("WIN_COUNT", param1=1.0)
    time.sleep(2)
    
    print("[Leader1] Test complete! Staying connected for monitoring...")
    print("[Leader1] Press Ctrl+C to stop the test and disconnect.")
    
    # Keep the leader connected indefinitely
    try:
        while True:
            time.sleep(10)
            # Periodically update state to show activity
            client.update_state(consecutive_wins=1, strongboxes_earned=0, in_match=False, current_map_id=796)
    except KeyboardInterrupt:
        print("\n[Leader1] Disconnecting...")
        client.disconnect()
        print("[Leader1] Disconnected.")


def simulate_losing_leader():
    """Simulate the losing team leader bot."""
    client = SocketClient(
        bot_id="TestLeader2",
        is_winning_team=False,
        host="127.0.0.1",
        port=12345
    )
    
    print("[Leader2] Connecting to Command Center...")
    if not client.connect():
        print("[Leader2] Failed to connect!")
        return
    
    print("[Leader2] Connected successfully!")
    
    # Wait a bit for Leader1 to start
    time.sleep(3)
    
    print("[Leader2] Sending READY_TO_QUEUE signal...")
    client.send_signal("READY_TO_QUEUE")
    
    # Wait for Command Center to tell us to queue
    print("[Leader2] Waiting for Command Center to coordinate queue...")
    queue_command_received = False
    timeout = TIMEOUT_SECONDS
    start = time.time()
    while time.time() - start < timeout:
        msg = client.get_next_message(timeout=0.5)
        if msg and msg.get('type') == 'CMD_QUEUE_NOW':
            print("[Leader2] ✓ Received CMD_QUEUE_NOW from Command Center!")
            queue_command_received = True
            break
    
    if not queue_command_received:
        print("[Leader2] Timeout waiting for queue command!")
        return
    
    time.sleep(1)
    print("[Leader2] Entering match...")
    client.update_state(in_match=True, current_map_id=829)
    time.sleep(1)
    
    # Wait for match start from partner (informational)
    print("[Leader2] Waiting for match signals...")
    timeout = TIMEOUT_SECONDS
    start = time.time()
    match_start_received = False
    while time.time() - start < timeout and not match_start_received:
        msg = client.get_next_message(timeout=0.5)
        if msg and msg.get('type') == 'MATCH_START':
            print("[Leader2] Received MATCH_START from partner!")
            match_start_received = True
            break
    
    # Send our map verification
    print("[Leader2] Sending MAP_VERIFY signal (map 829)...")
    client.send_signal("MAP_VERIFY", param1=829.0)
    
    # Wait for Command Center's match confirmation or resign command
    print("[Leader2] Waiting for Command Center's match verification...")
    timeout = TIMEOUT_SECONDS
    start = time.time()
    while time.time() - start < timeout:
        msg = client.get_next_message(timeout=0.5)
        if msg:
            msg_type = msg.get('type')
            if msg_type == 'CMD_MATCH_CONFIRMED':
                map_id = msg.get('map_id', 0)
                print(f"[Leader2] ✓ Command Center confirmed match (Map ID: {map_id})")
                break
            elif msg_type == 'CMD_RESIGN':
                reason = msg.get('reason', 'unknown')
                map_ids = msg.get('map_ids', [])
                print(f"[Leader2] ✗ Command Center ordered RESIGN - {reason}: maps {map_ids}")
                print("[Leader2] Would resign here in real scenario")
                break
    
    # Simulate losing
    time.sleep(2)
    print("[Leader2] Match lost. Updating state...")
    client.update_state(in_match=False, current_map_id=796)
    time.sleep(1)
    
    # Wait for partner's win count
    print("[Leader2] Waiting for partner's WIN_COUNT...")
    timeout = TIMEOUT_SECONDS
    start = time.time()
    while time.time() - start < timeout:
        msg = client.get_next_message(timeout=0.5)
        if msg and msg.get('type') == 'WIN_COUNT':
            partner_wins = int(msg.get('param1', 0))
            print(f"[Leader2] Partner has {partner_wins} consecutive wins!")
            break
    
    print("[Leader2] Test complete! Staying connected for monitoring...")
    print("[Leader2] Press Ctrl+C to stop the test and disconnect.")
    
    # Keep the leader connected indefinitely
    try:
        while True:
            time.sleep(10)
            # Periodically update state to show activity
            client.update_state(consecutive_wins=0, strongboxes_earned=0, in_match=False, current_map_id=796)
    except KeyboardInterrupt:
        print("\n[Leader2] Disconnecting...")
        client.disconnect()
        print("[Leader2] Disconnected.")


def main():
    """Run the test."""
    print("=" * 60)
    print("Codex Arena Bot Command Center - Test Script")
    print("=" * 60)
    print()
    print("Make sure the Command Center is running first!")
    print("Start it with: python codex_command_center.py")
    print()
    print("Press Enter to start the test...")
    input()
    
    print("\n" + "=" * 60)
    print("Starting test with two simulated Leader bots...")
    print("=" * 60 + "\n")
    
    # Start both leaders in separate threads
    leader1_thread = threading.Thread(target=simulate_winning_leader, daemon=True)
    leader2_thread = threading.Thread(target=simulate_losing_leader, daemon=True)
    
    leader1_thread.start()
    leader2_thread.start()
    
    # Keep main thread alive and wait for Ctrl+C
    print("\n" + "=" * 60)
    print("Test running - Both Leaders are connected and active")
    print("=" * 60)
    print("\nBoth Leaders will stay connected to the Command Center.")
    print("Watch the Command Center terminal for real-time status updates.")
    print("\nPress Ctrl+C to stop the test and disconnect both Leaders.")
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("Shutting down test...")
        print("=" * 60)
        print("\nWaiting for Leaders to disconnect gracefully...")
        time.sleep(2)  # Give threads time to handle KeyboardInterrupt
        print("Test shutdown complete.")



if __name__ == '__main__':
    main()
