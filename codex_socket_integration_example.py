"""
Example Integration of Socket Mode into Codex_Arena_Bot.py

This file demonstrates how to add optional socket communication to the existing
Codex Arena Bot without breaking the current shared memory implementation.

INSTRUCTIONS:
1. This is a reference implementation showing the changes needed
2. The actual integration is OPTIONAL - the bot works fine with ShMem only
3. Socket mode is useful for multi-machine setups and monitoring

KEY CHANGES TO MAKE IN Codex_Arena_Bot.py:
"""

# ============================================================================
# CHANGE 1: Add imports at the top of the file (after existing imports)
# ============================================================================

from codex_socket_client import (
    enable_socket_mode,
    disable_socket_mode,
    is_socket_mode_enabled,
    send_sync_signal_socket,
    check_sync_signal_socket,
    update_bot_state_socket
)


# ============================================================================
# CHANGE 2: Add socket configuration to CodexConfig class
# ============================================================================

class CodexConfig:
    """Configuration and state tracking for the Codex Arena bot."""
    def __init__(self):
        # ... existing configuration fields ...
        self.is_winning_team = True
        self.consecutive_wins = 0
        # ... etc ...
        
        # NEW: Socket mode configuration
        self.use_socket_mode = False  # Toggle to enable socket communication
        self.command_center_host = "127.0.0.1"  # Command Center address
        self.command_center_port = 12345  # Command Center port
        self.socket_bot_id = ""  # Bot ID for socket mode (e.g., "Leader1")


# ============================================================================
# CHANGE 3: Modify send_sync_signal to support both ShMem and Socket modes
# ============================================================================

def send_sync_signal(signal_type: str, param1: float = 0.0):
    """Send synchronization signal to other accounts.
    Supports both shared memory and socket communication modes."""
    
    # If socket mode is enabled and connected, use socket
    if config.use_socket_mode and is_socket_mode_enabled():
        send_sync_signal_socket(signal_type, param1)
        return
    
    # Otherwise, use existing ShMem code
    from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    my_email = get_my_email()
    
    if not config.partner_email or not config.partner_email.strip():
        return
    
    # ... rest of existing ShMem implementation ...
    if config.first_queue_completed and signal_type not in ["MAP_VERIFY", "WIN_COUNT"]:
        return
    
    signal_value = 0.0
    if signal_type == "READY_TO_QUEUE":
        signal_value = SIGNAL_READY_TO_QUEUE
    elif signal_type == "QUEUE_NOW":
        signal_value = SIGNAL_QUEUE_NOW
    elif signal_type == "MATCH_START":
        signal_value = SIGNAL_MATCH_START
    elif signal_type == "MATCH_END":
        signal_value = SIGNAL_MATCH_END
    elif signal_type == "MAP_VERIFY":
        signal_value = SIGNAL_MAP_VERIFY
    elif signal_type == "WIN_COUNT":
        signal_value = SIGNAL_WIN_COUNT
    
    params = (signal_value, param1, 0.0, 0.0)
    
    try:
        GLOBAL_CACHE.ShMem.SendMessage(my_email, config.partner_email.strip(), SYNC_QUEUE_COMMAND, params)
    except Exception as e:
        Py4GW.Console.Log(BOT_NAME, f"Failed to send sync signal: {e}", Py4GW.Console.MessageType.Warning)


# ============================================================================
# CHANGE 4: Modify check_sync_signal to support both modes
# ============================================================================

def check_sync_signal() -> tuple[str, int]:
    """Check for synchronization signals from other accounts.
    Supports both shared memory and socket communication modes."""
    
    # If socket mode is enabled and connected, use socket
    if config.use_socket_mode and is_socket_mode_enabled():
        return check_sync_signal_socket()
    
    # Otherwise, use existing ShMem code
    from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    my_email = get_my_email()
    
    # ... rest of existing ShMem implementation ...
    if config.first_queue_completed:
        # (existing message clearing code for MAP_VERIFY and WIN_COUNT)
        pass
    
    msg_index, msg = GLOBAL_CACHE.ShMem.PreviewNextMessage(my_email, include_running=False)
    
    if msg and msg.Command == SYNC_QUEUE_COMMAND:
        signal_type = ""
        param_value = 0
        
        if len(msg.Params) == 0:
            return ("", 0)
        
        signal_type = get_signal_type_name(msg.Params[0])
        
        if (msg.Params[0] == SIGNAL_MAP_VERIFY or msg.Params[0] == SIGNAL_WIN_COUNT) and len(msg.Params) > 1:
            param_value = int(msg.Params[1])
        
        if signal_type and signal_type != "UNKNOWN":
            GLOBAL_CACHE.ShMem.MarkMessageAsFinished(my_email, msg_index)
            return (signal_type, param_value)
    
    return ("", 0)


# ============================================================================
# CHANGE 5: Add socket connection at bot startup (in create_bot_routine)
# ============================================================================

def create_bot_routine(bot: Botting) -> None:
    """Setup the bot routine."""
    
    # NEW: Try to connect to Command Center if socket mode is enabled
    if config.use_socket_mode and config.socket_bot_id:
        Py4GW.Console.Log(BOT_NAME, 
                         f"Attempting to connect to Command Center at {config.command_center_host}:{config.command_center_port}...",
                         Py4GW.Console.MessageType.Info)
        
        if enable_socket_mode(
            bot_id=config.socket_bot_id,
            is_winning_team=config.is_winning_team,
            host=config.command_center_host,
            port=config.command_center_port
        ):
            Py4GW.Console.Log(BOT_NAME, "Successfully connected to Command Center!", 
                             Py4GW.Console.MessageType.Success)
        else:
            Py4GW.Console.Log(BOT_NAME, "Failed to connect to Command Center. Falling back to ShMem mode.",
                             Py4GW.Console.MessageType.Warning)
            config.use_socket_mode = False
    
    # Existing bot routine setup
    bot.States.AddHeader(f"{BOT_NAME}")
    for _ in range(100):
        run_codex_match(bot)


# ============================================================================
# CHANGE 6: Add periodic state updates in match logic (optional but recommended)
# ============================================================================

def winning_team_logic(bot: Botting) -> Generator:
    """Logic for the winning team - win matches continuously."""
    from Py4GWCoreLib.Routines import Routines
    from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    
    while bot.config.fsm_running:
        # Send current win count to partner team
        send_sync_signal("WIN_COUNT", float(config.consecutive_wins))
        
        # NEW: Also update Command Center with current state (if socket mode)
        if config.use_socket_mode and is_socket_mode_enabled():
            update_bot_state_socket(
                consecutive_wins=config.consecutive_wins,
                strongboxes_earned=config.strongboxes_earned,
                in_match=config.in_match,
                current_map_id=GLOBAL_CACHE.Map.GetMapID()
            )
        
        # ... rest of existing winning team logic ...
        # (existing code continues unchanged)


# ============================================================================
# CHANGE 7: Add socket mode controls to GUI (_draw_settings function)
# ============================================================================

def _draw_settings():
    """Custom settings panel for the bot."""
    import PyImGui
    
    # ... existing GUI code ...
    
    # NEW: Socket Mode Configuration Section
    PyImGui.separator()
    if PyImGui.collapsing_header("Socket Mode (Command Center)", False):
        PyImGui.text_wrapped("Optional: Connect to external Command Center for monitoring and coordination.")
        
        new_socket_mode = PyImGui.checkbox("Enable Socket Mode", config.use_socket_mode)
        if new_socket_mode != config.use_socket_mode:
            config.use_socket_mode = new_socket_mode
            if new_socket_mode:
                Py4GW.Console.Log(BOT_NAME, "Socket mode enabled. Restart bot to connect.", 
                                 Py4GW.Console.MessageType.Info)
            else:
                Py4GW.Console.Log(BOT_NAME, "Socket mode disabled.", 
                                 Py4GW.Console.MessageType.Info)
                if is_socket_mode_enabled():
                    disable_socket_mode()
        
        if config.use_socket_mode:
            PyImGui.text("Bot ID:")
            config.socket_bot_id = PyImGui.input_text("##socket_bot_id", config.socket_bot_id, 256)
            
            PyImGui.text("Command Center Host:")
            config.command_center_host = PyImGui.input_text("##cc_host", config.command_center_host, 256)
            
            PyImGui.text("Command Center Port:")
            new_port = PyImGui.input_int("##cc_port", config.command_center_port)
            if 1 <= new_port <= 65535:
                config.command_center_port = new_port
            
            # Show connection status
            if is_socket_mode_enabled():
                PyImGui.text_colored("Status: CONNECTED", (0, 1, 0, 1))
            else:
                PyImGui.text_colored("Status: DISCONNECTED", (1, 0, 0, 1))
    
    # ... rest of existing GUI code ...


# ============================================================================
# CHANGE 8: Clean up socket connection on bot stop (optional)
# ============================================================================

# Add to bot shutdown/cleanup code if it exists
def cleanup_on_stop():
    """Clean up resources when bot stops."""
    if config.use_socket_mode and is_socket_mode_enabled():
        Py4GW.Console.Log(BOT_NAME, "Disconnecting from Command Center...", 
                         Py4GW.Console.MessageType.Info)
        disable_socket_mode()


# ============================================================================
# SUMMARY OF CHANGES
# ============================================================================

"""
Summary:
1. Import socket client functions
2. Add socket config fields to CodexConfig
3. Modify send_sync_signal to check socket mode first
4. Modify check_sync_signal to check socket mode first
5. Connect to Command Center at bot startup
6. Optionally send state updates during match
7. Add socket mode controls to GUI
8. Disconnect on bot stop

The integration is designed to be:
- OPTIONAL: Works with or without socket mode
- BACKWARD COMPATIBLE: Existing ShMem code unchanged
- FAIL-SAFE: Falls back to ShMem if socket connection fails
- NON-BREAKING: Can be enabled/disabled via GUI

This allows users to:
- Use ShMem only (default, works as before)
- Use Socket only (for multi-machine setups)
- Use both (socket for monitoring, ShMem for reliability)
"""
