# Codex Arena Bot - Command Center Quick Start Guide

This guide will help you get started with the Command Center in 5 minutes.

## What is the Command Center?

The Command Center is an optional external monitoring and coordination system for the Codex Arena Bot. It provides:

- Real-time visibility into bot states
- Message routing between Leaders
- Complete communication logs
- Support for multi-machine setups

## Do I Need It?

**No, it's completely optional!** The Codex Arena Bot works perfectly with its built-in shared memory system. Use the Command Center if you want:

- Better monitoring and debugging
- To run Leaders on different computers
- Enhanced visibility during development
- Complete communication logs

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

**That's it!** The Command Center is now running and ready to monitor your bots.

### Step 2: Start Your Codex Bots (Normal Operation)

The bots work normally with shared memory. The Command Center is ready if you want to integrate socket mode later.

### Step 3 (Optional): Test the System

If you want to see the Command Center in action:

1. Keep the Command Center running in the first terminal
2. Open a second terminal and run:
   ```bash
   python test_command_center.py
   ```
3. Press Enter when prompted
4. Watch the Command Center terminal for real-time communication logs!

You'll see messages like:
```
INFO - Registered TestLeader1 (Winning team)
INFO - Registered TestLeader2 (Losing team)  
INFO - Routing READY_TO_QUEUE from TestLeader1 to TestLeader2
INFO - Routing MAP_VERIFY from TestLeader1 to TestLeader2
```

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
