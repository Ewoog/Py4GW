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
    time.sleep(1)
    
    # Wait for partner's ready signal
    print("[Leader1] Waiting for partner to be ready...")
    timeout = TIMEOUT_SECONDS
    start = time.time()
    while time.time() - start < timeout:
        msg = client.get_next_message(timeout=0.5)
        if msg and msg.get('type') == 'READY_TO_QUEUE':
            print("[Leader1] Partner is ready!")
            break
    
    print("[Leader1] Sending QUEUE_NOW signal...")
    client.send_signal("QUEUE_NOW")
    time.sleep(1)
    
    print("[Leader1] Entering match...")
    client.update_state(in_match=True, current_map_id=829)
    time.sleep(1)
    
    print("[Leader1] Sending MATCH_START signal...")
    client.send_signal("MATCH_START")
    time.sleep(1)
    
    print("[Leader1] Sending MAP_VERIFY signal (map 829)...")
    client.send_signal("MAP_VERIFY", param1=829.0)
    
    # Wait for partner's map verify
    print("[Leader1] Waiting for partner's map verification...")
    timeout = TIMEOUT_SECONDS
    start = time.time()
    while time.time() - start < timeout:
        msg = client.get_next_message(timeout=0.5)
        if msg and msg.get('type') == 'MAP_VERIFY':
            partner_map = int(msg.get('param1', 0))
            print(f"[Leader1] Partner is on map {partner_map}")
            if partner_map == 829:
                print("[Leader1] Maps match! No desync detected.")
            else:
                print("[Leader1] DESYNC! Maps don't match!")
            break
    
    # Simulate winning
    time.sleep(2)
    print("[Leader1] Match won! Updating state...")
    client.update_state(consecutive_wins=1, in_match=False)
    time.sleep(1)
    
    print("[Leader1] Sending WIN_COUNT signal (1 win)...")
    client.send_signal("WIN_COUNT", param1=1.0)
    time.sleep(2)
    
    print("[Leader1] Disconnecting...")
    client.disconnect()
    print("[Leader1] Test complete!")


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
    
    # Wait for partner's ready and queue signals
    print("[Leader2] Waiting for partner signals...")
    queue_received = False
    timeout = TIMEOUT_SECONDS
    start = time.time()
    while time.time() - start < timeout:
        msg = client.get_next_message(timeout=0.5)
        if msg:
            msg_type = msg.get('type')
            if msg_type == 'READY_TO_QUEUE':
                print("[Leader2] Partner is ready!")
            elif msg_type == 'QUEUE_NOW':
                print("[Leader2] Received QUEUE_NOW from partner!")
                queue_received = True
                break
    
    if queue_received:
        time.sleep(1)
        print("[Leader2] Entering match...")
        client.update_state(in_match=True, current_map_id=829)
        time.sleep(1)
        
        # Wait for match start and map verify
        print("[Leader2] Waiting for match signals...")
        timeout = TIMEOUT_SECONDS
        start = time.time()
        while time.time() - start < timeout:
            msg = client.get_next_message(timeout=0.5)
            if msg:
                msg_type = msg.get('type')
                if msg_type == 'MATCH_START':
                    print("[Leader2] Received MATCH_START from partner!")
                elif msg_type == 'MAP_VERIFY':
                    partner_map = int(msg.get('param1', 0))
                    print(f"[Leader2] Partner is on map {partner_map}")
                    print("[Leader2] Sending our MAP_VERIFY...")
                    client.send_signal("MAP_VERIFY", param1=829.0)
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
    
    time.sleep(2)
    print("[Leader2] Disconnecting...")
    client.disconnect()
    print("[Leader2] Test complete!")


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
    
    # Wait for both to complete
    leader1_thread.join()
    leader2_thread.join()
    
    print("\n" + "=" * 60)
    print("Test completed successfully!")
    print("=" * 60)
    print("\nCheck the Command Center output to see the communication log.")


if __name__ == '__main__':
    main()
