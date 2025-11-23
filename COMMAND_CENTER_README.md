# Codex Arena Bot - Command Center

## Overview

The Command Center is an external socket-based coordination system for the Codex Arena Bot. It runs outside of Py4GW and provides centralized control, monitoring, and communication between the Leader bots.

## Architecture

### Components

1. **Command Center** (`codex_command_center.py`)
   - Standalone Python script that runs outside Py4GW
   - TCP socket server listening for bot connections
   - Routes messages between Leaders
   - Monitors bot health and status
   - Provides real-time logging and diagnostics

2. **Socket Client** (`codex_socket_client.py`)
   - Client library integrated into Codex_Arena_Bot.py
   - Connects to the Command Center
   - Sends/receives commands via TCP sockets
   - Can be used alongside or instead of shared memory (ShMem)

3. **Modified Bot** (optional integration in `Codex_Arena_Bot.py`)
   - Can use either ShMem (default) or Socket communication
   - Socket mode provides better monitoring and control
   - Compatible with existing functionality

## Why Use Command Center?

### Benefits

1. **Centralized Monitoring**
   - See status of all Leaders in one place
   - Real-time logging of all bot activities
   - Track wins, strongboxes, and match states

2. **Better Coordination**
   - Guaranteed message delivery between Leaders
   - No message stacking issues
   - Easier debugging of synchronization problems

3. **External Control**
   - Command Center runs independently of game client
   - Can restart bots without losing coordination state
   - Better for multi-machine setups

4. **Diagnostics**
   - Complete communication log
   - Heartbeat monitoring to detect disconnections
   - Status dashboard (future: web interface)

### Use Cases

- **Multi-Machine Setup**: Run Leaders on different computers
- **Remote Monitoring**: Monitor bots from another location
- **Advanced Automation**: Build custom control logic outside Py4GW
- **Debugging**: Trace all communication between Leaders
- **Production Use**: More reliable than shared memory for long-running sessions

## Setup Instructions

### Quick Start (Single Machine)

1. **Start the Command Center**
   ```bash
   python codex_command_center.py
   ```
   
   This starts the server on `127.0.0.1:12345` (localhost, default port).

2. **Enable Socket Mode in Bots** (Optional)
   
   The Codex Arena Bot can continue to use shared memory (default) or optionally use socket communication. To enable socket mode, you would modify `Codex_Arena_Bot.py` to import and use the socket client.

3. **Monitor the Output**
   
   The Command Center will display:
   - Connection status of each Leader
   - Real-time message routing
   - Bot states (wins, strongboxes, map IDs)
   - Periodic status summaries

### Advanced Setup (Multi-Machine)

1. **Choose a Host Machine**
   - Select one machine to run the Command Center
   - Note its IP address (e.g., 192.168.1.100)

2. **Start Command Center on Host**
   ```bash
   python codex_command_center.py --host 0.0.0.0 --port 12345
   ```
   
   Using `0.0.0.0` allows connections from other machines on the network.

3. **Configure Firewall**
   - Open port 12345 (or your chosen port) on the host machine
   - Allow incoming TCP connections

4. **Connect Bots from Other Machines**
   
   When enabling socket mode in the bots, use the host's IP:
   ```python
   enable_socket_mode(
       bot_id="Leader1",
       is_winning_team=True,
       host="192.168.1.100",  # Command Center host
       port=12345
   )
   ```

## Command Center Usage

### Starting the Server

**Default (localhost only):**
```bash
python codex_command_center.py
```

**Custom host/port:**
```bash
python codex_command_center.py --host 0.0.0.0 --port 8888
```

**Help:**
```bash
python codex_command_center.py --help
```

### Command Center Output

The Command Center provides several types of output:

1. **Connection Messages**
   ```
   [INFO] New connection from ('127.0.0.1', 54321)
   [INFO] Registered Leader1 (Winning team) from ('127.0.0.1', 54321)
   ```

2. **Message Routing**
   ```
   [INFO] Routing READY_TO_QUEUE from Leader1 to Leader2
   [INFO] Routing WIN_COUNT from Leader1 to Leader2
   ```

3. **Status Updates**
   ```
   [INFO] Status update from Leader1: Wins=3, Boxes=0, InMatch=True
   ```

4. **Periodic Status Dashboard** (every 10 seconds)
   ```
   ============================================================
   COMMAND CENTER STATUS
   ============================================================
   Leader1 (Winning Team):
     Address: ('127.0.0.1', 54321)
     Status: IN MATCH
     Map ID: 829
     Consecutive Wins: 3
     Strongboxes: 0
     Last Signal: MAP_VERIFY
     Uptime: 325s
   ------------------------------------------------------------
   Leader2 (Losing Team):
     Address: ('127.0.0.1', 54322)
     Status: IN MATCH
     Map ID: 829
     Consecutive Wins: 0
     Strongboxes: 0
     Last Signal: READY_TO_QUEUE
     Uptime: 324s
   ------------------------------------------------------------
   ============================================================
   ```

5. **Heartbeat Monitoring**
   ```
   [WARNING] Client Leader2 heartbeat timeout, disconnecting
   ```

### Log Files

All output is also saved to `codex_command_center.log` in the same directory.

## Integration with Codex Arena Bot

### Current Implementation (Shared Memory)

The Codex Arena Bot currently uses Py4GW's shared memory system:

```python
# Current code in Codex_Arena_Bot.py
GLOBAL_CACHE.ShMem.SendMessage(my_email, partner_email, SYNC_QUEUE_COMMAND, params)
```

### Optional Socket Integration

To use the Command Center, you can modify the bot to support socket mode:

#### Option 1: Add Socket Support (Recommended for Testing)

Add this to the imports section of `Codex_Arena_Bot.py`:

```python
from codex_socket_client import (
    enable_socket_mode,
    is_socket_mode_enabled,
    send_sync_signal_socket,
    check_sync_signal_socket,
    update_bot_state_socket
)
```

Add configuration in the `CodexConfig` class:

```python
class CodexConfig:
    def __init__(self):
        # ... existing config ...
        self.use_socket_mode = False  # Toggle for socket communication
        self.command_center_host = "127.0.0.1"
        self.command_center_port = 12345
        self.socket_bot_id = ""  # e.g., "Leader1"
```

Add connection logic at bot startup:

```python
# In create_bot_routine or appropriate initialization location
if config.use_socket_mode and config.socket_bot_id:
    Py4GW.Console.Log(BOT_NAME, 
                     f"Connecting to Command Center at {config.command_center_host}:{config.command_center_port}...",
                     Py4GW.Console.MessageType.Info)
    
    if enable_socket_mode(
        bot_id=config.socket_bot_id,
        is_winning_team=config.is_winning_team,
        host=config.command_center_host,
        port=config.command_center_port
    ):
        Py4GW.Console.Log(BOT_NAME, "Connected to Command Center!", 
                         Py4GW.Console.MessageType.Success)
    else:
        Py4GW.Console.Log(BOT_NAME, "Failed to connect to Command Center, using ShMem instead",
                         Py4GW.Console.MessageType.Warning)
        config.use_socket_mode = False
```

Modify signal functions to support both modes:

```python
def send_sync_signal(signal_type: str, param1: float = 0.0):
    """Send synchronization signal - supports both ShMem and Socket modes."""
    
    if config.use_socket_mode and is_socket_mode_enabled():
        # Use socket communication
        send_sync_signal_socket(signal_type, param1)
        # Also update state if needed
        if signal_type == "WIN_COUNT":
            update_bot_state_socket(consecutive_wins=int(param1))
    else:
        # Use existing ShMem code
        from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
        my_email = get_my_email()
        
        if not config.partner_email or not config.partner_email.strip():
            return
        
        # ... existing ShMem code ...
```

#### Option 2: Keep Current Implementation (Default)

The bot works perfectly with shared memory. The Command Center is **completely optional** and provides additional monitoring capabilities without requiring changes to the core bot logic.

### Hybrid Mode (Best of Both Worlds)

You can run both systems simultaneously:
- Use ShMem for actual communication (proven, reliable)
- Use Socket mode for monitoring and diagnostics (visibility)

In this mode, signals are sent via both channels, and the Command Center provides real-time visibility without affecting the core bot operation.

## Message Types

### Bot to Command Center

1. **REGISTER** - Initial registration
   ```json
   {
     "type": "REGISTER",
     "bot_id": "Leader1",
     "is_winning_team": true
   }
   ```

2. **HEARTBEAT** - Keep-alive signal (every 5 seconds)
   ```json
   {
     "type": "HEARTBEAT"
   }
   ```

3. **STATUS_UPDATE** - Bot state update
   ```json
   {
     "type": "STATUS_UPDATE",
     "consecutive_wins": 3,
     "strongboxes_earned": 0,
     "in_match": true,
     "current_map_id": 829
   }
   ```

4. **Synchronization Signals**
   - READY_TO_QUEUE
   - QUEUE_NOW
   - MATCH_START
   - MATCH_END
   - MAP_VERIFY (with map_id as param1)
   - WIN_COUNT (with win count as param1)

### Command Center to Bot

1. **REGISTER_ACK** - Registration acknowledgment
   ```json
   {
     "type": "REGISTER_ACK",
     "message": "Registration successful"
   }
   ```

2. **Routed Signals** - Signals forwarded from partner
   - All synchronization signals are routed to the partner bot

## Troubleshooting

### Connection Issues

**Problem**: Bots can't connect to Command Center

**Solutions**:
1. Ensure Command Center is running before starting bots
2. Check firewall settings
3. Verify host/port configuration matches
4. For multi-machine: use correct IP address, not 127.0.0.1
5. Check network connectivity: `ping <command_center_ip>`

### Message Routing Problems

**Problem**: Messages not being routed between Leaders

**Solutions**:
1. Check that both Leaders are connected (look for "Registered" messages)
2. Verify one bot is marked as winning team, one as losing team
3. Check Command Center logs for routing messages
4. Ensure bots are sending signals in socket mode

### Heartbeat Timeouts

**Problem**: "heartbeat timeout" messages in Command Center

**Solutions**:
1. Check bot is still running
2. Verify network stability
3. Look for exceptions in bot console
4. Restart the affected bot

### High Latency

**Problem**: Slow message delivery

**Solutions**:
1. Check network latency between machines
2. Reduce other network traffic
3. Consider running Command Center on same machine as one Leader
4. Check system resource usage (CPU, memory)

## Future Enhancements

Potential improvements for the Command Center:

1. **Web Dashboard**
   - HTML/JavaScript interface for monitoring
   - Real-time graphs of wins and progression
   - Control panel for sending commands

2. **Database Logging**
   - Store all events in SQLite/PostgreSQL
   - Historical analysis of bot performance
   - Statistics and reports

3. **Alert System**
   - Email/SMS notifications for important events
   - Webhook integration (Discord, Slack, etc.)
   - Desync detection and automatic recovery

4. **Advanced Features**
   - Auto-restart failed bots
   - Load balancing across multiple teams
   - Session recording and playback
   - Configuration management

5. **Security**
   - Authentication for bot connections
   - Encrypted communication (TLS/SSL)
   - Access control and permissions

## Comparison: ShMem vs Socket Mode

| Feature | Shared Memory (ShMem) | Socket Mode |
|---------|----------------------|-------------|
| **Setup Complexity** | Simple (built-in) | Moderate (requires Command Center) |
| **Same Machine** | Excellent | Good |
| **Multi-Machine** | Not supported | Excellent |
| **Monitoring** | Limited | Comprehensive |
| **Debugging** | Difficult | Easy (full logs) |
| **Reliability** | Very high | High (network dependent) |
| **Latency** | Very low | Low (network dependent) |
| **External Control** | No | Yes |
| **Message History** | No | Yes (logged) |
| **Scalability** | Limited to local | Excellent |

## Best Practices

1. **Development/Testing**: Use Socket mode for better visibility
2. **Production (Same Machine)**: Use ShMem for performance
3. **Production (Multi-Machine)**: Use Socket mode (only option)
4. **Debugging Issues**: Always use Socket mode for diagnostics
5. **Hybrid Monitoring**: Run both modes for critical sessions

## Security Considerations

### Current Implementation

- No authentication required
- No encryption
- Suitable for local network or localhost only

### For Production Use

If exposing the Command Center over the internet:

1. Use SSH tunneling
2. VPN for network access
3. Implement authentication (future enhancement)
4. Use TLS/SSL (future enhancement)

### Example: SSH Tunnel

On the client machine:
```bash
ssh -L 12345:localhost:12345 user@command_center_host
```

Then connect to `localhost:12345` instead of the remote host.

## Support and Contribution

For issues or enhancements:
1. Check this documentation first
2. Review Command Center logs
3. Test with simple scenarios (2 bots, localhost)
4. Report issues with full logs and configuration

## License

Same as Py4GW project.
