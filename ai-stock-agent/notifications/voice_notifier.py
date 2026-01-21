"""
Voice Alert System
Speaks alerts out loud using text-to-speech
"""

import os
import logging
from typing import List, Dict, Any
from datetime import datetime
import threading

logger = logging.getLogger(__name__)

# Voice Configuration
VOICE_ENABLED = os.getenv('VOICE_ENABLED', 'false').lower() == 'true'
VOICE_RATE = int(os.getenv('VOICE_RATE', '150'))
VOICE_VOLUME = float(os.getenv('VOICE_VOLUME', '1.0'))

class VoiceNotifier:
    """Send voice alerts using text-to-speech"""

    def __init__(self):
        """Initialize voice notifier"""
        self.enabled = VOICE_ENABLED
        self.engine = None

        if self.enabled:
            try:
                import pyttsx3
                self.engine = pyttsx3.init()
                self.engine.setProperty('rate', VOICE_RATE)
                self.engine.setProperty('volume', VOICE_VOLUME)
                logger.info("Voice alerts enabled")
            except ImportError:
                logger.warning("pyttsx3 not installed. Run: pip install pyttsx3")
                self.enabled = False
            except Exception as e:
                logger.error(f"Error initializing voice engine: {e}")
                self.enabled = False
        else:
            logger.info("Voice alerts disabled")

    def speak(self, text: str, async_mode: bool = True) -> bool:
        """Speak text out loud"""
        if not self.enabled:
            logger.info(f"[VOICE DISABLED] Would say: {text}")
            return False

        try:
            if async_mode:
                thread = threading.Thread(target=self._speak_sync, args=(text,))
                thread.daemon = True
                thread.start()
            else:
                self._speak_sync(text)
            return True
        except Exception as e:
            logger.error(f"Failed to speak: {e}")
            return False

    def _speak_sync(self, text: str):
        """Internal method to speak synchronously"""
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            logger.error(f"Error in speech synthesis: {e}")

    def announce_target_hit(self, ticker: str, profit_pct: float) -> bool:
        """Announce when price target is hit"""
        ticker_spoken = " ".join(ticker)
        text = f"Target hit! {ticker_spoken} reached your price target. Profit is {profit_pct:.1f} percent. Consider taking profits now!"
        return self.speak(text)

    def announce_stop_loss(self, ticker: str, loss_pct: float) -> bool:
        """Announce when stop loss is hit"""
        ticker_spoken = " ".join(ticker)
        text = f"Stop loss alert! {ticker_spoken} hit your stop loss. Loss is {abs(loss_pct):.1f} percent. Exit position immediately!"
        return self.speak(text)

_voice_notifier = None

def get_voice_notifier():
    global _voice_notifier
    if _voice_notifier is None:
        _voice_notifier = VoiceNotifier()
    return _voice_notifier
