# Codex Arena Bot - Command Center Quick Start Guide

This guide will help you get started with the Command Center in 5 minutes.

## What is the Command Center?

The Command Center is an optional external coordination and monitoring system for the Codex Arena Bot. It provides:

- **Intelligent Coordination**: Actively coordinates queue timing and verifies map synchronization
- **Automatic Desync Detection**: Detects when leaders are in different matches and commands resign
- **Web GUI**: Beautiful interface with manual control buttons
- **Real-time Monitoring**: Live bot status, wins, strongboxes, match states
- **Manual Commands**: Force resign, switch teams, force queue via GUI
- **Complete Logs**: All coordination decisions and commands logged
- **Multi-machine Support**: Run Leaders on different computers

## Do I Need It?

**No, it's completely optional!** The Codex Arena Bot works perfectly with its built-in shared memory system. Use the Command Center if you want:

- Intelligent coordination (CC decides when to queue and verifies maps)
- Automatic desync detection and resolution
- Manual control via beautiful web GUI
- Better monitoring and debugging
- To run Leaders on different computers
- Enhanced visibility during development

## Quick Start (5 Minutes)

### Step 1: Start the Command Center

Open a terminal/command prompt and run:

```bash
python codex_command_center.py
```

You should see:
```
INFO - Command Center started on 127.0.0.1:12345
INFO - Waiting for Leader bots to connect...
INFO - Command Center is running. Press Ctrl+C to stop.
```

**That's it!** The Command Center is now running and ready to coordinate your bots.

### Step 2: (Optional) Start the GUI

For manual control and visual monitoring, open a second terminal:

**Option A - Tkinter GUI (Recommended - No dependencies):**
```bash
python codex_command_center_gui_tk.py
```

**Option B - Web GUI (Requires Flask):**
```bash
pip install flask  # Install Flask if needed
python codex_command_center_gui.py
# Then open browser to http://localhost:5000
```

The Tkinter GUI provides:
- 📊 Real-time bot status display
- 🎮 Manual control buttons (Resign, Switch Teams, Force Queue)
- 📜 Command history log
- 🟢 Live connection status
- Works without any external dependencies!

### Step 3: Start Your Codex Bots (Normal Operation)

The bots work normally with shared memory. The Command Center is ready if you want to integrate socket mode later.

### Step 4 (Optional): Test the System

If you want to see the Command Center in action:

1. Keep the Command Center running in the first terminal
2. Open a second terminal and run:
   ```bash
   python test_command_center.py
   ```
3. Press Enter when prompted
4. Watch both terminals - you'll see real-time communication logs!
5. Both test Leaders will stay connected indefinitely
6. Press Ctrl+C to stop the test and disconnect

You'll see messages like:
```
INFO - Registered TestLeader1 (Winning team)
INFO - Registered TestLeader2 (Losing team)  
INFO - Routing READY_TO_QUEUE from TestLeader1 to TestLeader2
INFO - Routing MAP_VERIFY from TestLeader1 to TestLeader2
INFO - Status update from TestLeader1: Wins=1, Boxes=0, InMatch=False
```

The test Leaders remain connected and send periodic heartbeats and status updates until you press Ctrl+C.

## What Next?

### Just Monitoring (No Bot Changes)

The Command Center can run alongside your bots without any integration. You can use it to:
- Log network traffic for debugging
- Monitor system health
- Prepare for future multi-machine setups

### Full Integration (Optional)

If you want bots to communicate through the Command Center, see:
- `codex_socket_integration_example.py` - Example integration code
- `COMMAND_CENTER_README.md` - Complete documentation

The integration is designed to be:
- **Non-breaking**: Works alongside existing shared memory
- **Optional**: Can enable/disable via bot GUI
- **Fail-safe**: Falls back to shared memory if connection fails

## Common Questions

**Q: Will this break my existing setup?**  
A: No! The Command Center is completely separate. Your bots continue to work with shared memory.

**Q: Do I need to modify the bot code?**  
A: Not required. Integration is optional and shown in the example file.

**Q: Can I run this on a different computer?**  
A: Yes! Use `--host 0.0.0.0` and configure your firewall. See the full README for details.

**Q: What if the Command Center crashes?**  
A: The bots are unaffected and continue using shared memory (unless you integrated socket mode).

**Q: How do I stop the Command Center?**  
A: Press Ctrl+C in the terminal where it's running.

## Troubleshooting

**"Address already in use" error**  
- Another program is using port 12345
- Use a different port: `python codex_command_center.py --port 8888`

**Test script can't connect**  
- Make sure the Command Center is running first
- Check that you're using the same port in both

**Want more details?**  
- See `COMMAND_CENTER_README.md` for complete documentation
- See `CODEX_BOT_README.md` for bot-specific information

## Files Reference

- `codex_command_center.py` - The Command Center server (run this)
- `codex_socket_client.py` - Client library (for integration)
- `test_command_center.py` - Test script (verify it works)
- `codex_socket_integration_example.py` - Integration guide
- `COMMAND_CENTER_README.md` - Full documentation
- `CODEX_BOT_README.md` - Bot documentation

## Summary

1. **Start Command Center**: `python codex_command_center.py`
2. **Test (Optional)**: `python test_command_center.py`
3. **Use Normally**: Bots work as before, Command Center provides monitoring
4. **Integrate (Optional)**: Follow examples to enable socket communication

That's it! The Command Center is a monitoring tool that enhances the bot without being required.
