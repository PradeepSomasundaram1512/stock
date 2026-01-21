"""
Test New Features
Quick tests for Multi-Timeframe, WhatsApp, and Voice alerts
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

# Load .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Environment variables may not load.")
    print("Install: pip install python-dotenv")

def test_multitimeframe():
    """Test multi-timeframe analysis"""
    print("\n" + "="*70)
    print("TESTING MULTI-TIMEFRAME ANALYSIS")
    print("="*70)

    try:
        from enhancements.multi_timeframe import get_mtf_analyzer

        analyzer = get_mtf_analyzer()
        result = analyzer.analyze('AAPL')

        print(analyzer.format_report(result))
        print("✅ Multi-timeframe analysis working!")

    except Exception as e:
        print(f"❌ Multi-timeframe test failed: {e}")
        import traceback
        traceback.print_exc()


def test_whatsapp():
    """Test WhatsApp alerts"""
    print("\n" + "="*70)
    print("TESTING WHATSAPP ALERTS")
    print("="*70)

    try:
        from notifications.whatsapp_notifier import get_whatsapp_notifier

        notifier = get_whatsapp_notifier()

        if not notifier.enabled:
            print("⚠️  WhatsApp is disabled. Enable in .env:")
            print("   WHATSAPP_ENABLED=true")
            print("   YOUR_WHATSAPP_NUMBER=whatsapp:+1234567890")
            return

        message = "🎉 Test alert from your AI Trading Bot!\n\nAll systems operational. Ready to trade! 📈"
        success = notifier.send_whatsapp(message)

        if success:
            print("✅ WhatsApp message sent! Check your phone.")
        else:
            print("❌ WhatsApp message failed. Check configuration.")

    except Exception as e:
        print(f"❌ WhatsApp test failed: {e}")
        import traceback
        traceback.print_exc()


def test_voice():
    """Test voice alerts"""
    print("\n" + "="*70)
    print("TESTING VOICE ALERTS")
    print("="*70)

    try:
        from notifications.voice_notifier import get_voice_notifier

        notifier = get_voice_notifier()

        if not notifier.enabled:
            print("⚠️  Voice is disabled. Enable in .env:")
            print("   VOICE_ENABLED=true")
            return

        print("Speaking test message...")
        notifier.speak("Voice alert system is working. All systems operational.", async_mode=False)
        print("✅ Voice alert spoken! Did you hear it?")

    except Exception as e:
        print(f"❌ Voice test failed: {e}")
        import traceback
        traceback.print_exc()


def test_discord():
    """Test Discord alerts"""
    print("\n" + "="*70)
    print("TESTING DISCORD ALERTS")
    print("="*70)

    try:
        from notifications.discord_notifier import get_discord_notifier

        notifier = get_discord_notifier()

        if not notifier.enabled:
            print("⚠️  Discord is disabled. Enable in .env:")
            print("   DISCORD_ENABLED=true")
            print("   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...")
            return

        message = "🎉 Test alert from your AI Trading Bot!\n\nAll systems operational. Ready to trade! 📈"
        success = notifier.send_discord(content=message)

        if success:
            print("✅ Discord message sent! Check your Discord channel.")
        else:
            print("❌ Discord message failed. Check configuration.")

    except Exception as e:
        print(f"❌ Discord test failed: {e}")
        import traceback
        traceback.print_exc()


def test_all():
    """Test all new features"""
    print("\n🚀 TESTING ALL NEW FEATURES")
    print("="*70)

    test_multitimeframe()
    test_voice()
    test_whatsapp()
    test_discord()

    print("\n" + "="*70)
    print("✅ ALL TESTS COMPLETE!")
    print("="*70)
    print("\nIf all tests passed, your system is ready to trade!")
    print("Run: python automated_trader.py")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Test new trading features")
    parser.add_argument('test', choices=['all', 'mtf', 'whatsapp', 'voice', 'discord'],
                       default='all', nargs='?',
                       help='Which test to run (default: all)')

    args = parser.parse_args()

    if args.test == 'mtf':
        test_multitimeframe()
    elif args.test == 'whatsapp':
        test_whatsapp()
    elif args.test == 'voice':
        test_voice()
    elif args.test == 'discord':
        test_discord()
    else:
        test_all()
