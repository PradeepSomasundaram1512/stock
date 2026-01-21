"""
Simple Discord Test Script
"""
import os
from pathlib import Path

# Load .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✓ .env file loaded")
except ImportError:
    print("⚠️  python-dotenv not installed. Install: pip install python-dotenv")
    print("Trying to use environment variables directly...")

# Check configuration
discord_enabled = os.getenv('DISCORD_ENABLED', 'false').lower() == 'true'
discord_webhook = os.getenv('DISCORD_WEBHOOK_URL', '')

print(f"\nDiscord Enabled: {discord_enabled}")
print(f"Webhook URL set: {bool(discord_webhook)}")

if discord_webhook:
    print(f"Webhook URL: {discord_webhook[:50]}...")

if not discord_enabled:
    print("\n❌ Discord is not enabled in .env")
    print("Set: DISCORD_ENABLED=true")
    exit(1)

if not discord_webhook:
    print("\n❌ Discord webhook URL is not set in .env")
    print("Set: DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...")
    exit(1)

# Try to send test message
print("\n" + "="*70)
print("SENDING TEST MESSAGE TO DISCORD")
print("="*70)

try:
    import requests

    payload = {
        "content": "🎉 **TEST MESSAGE FROM AI TRADING BOT**\n\nIf you see this, Discord integration is working perfectly! ✅"
    }

    response = requests.post(discord_webhook, json=payload)

    if response.status_code == 204:
        print("\n✅ SUCCESS! Discord message sent!")
        print("Check your Discord channel - you should see the test message.")
    else:
        print(f"\n❌ Failed to send Discord message")
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text}")

except ImportError:
    print("\n❌ 'requests' library not installed")
    print("Install: pip install requests")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
