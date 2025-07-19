#!/usr/bin/env python
"""
Start Telegram Bot
This script starts the Telegram bot server.
"""

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Start the Telegram bot"""
    try:
        logger.info("🤖 Telegram բոտը սկսվում է...")
        
        from telegram_bot import TelegramNotifier
        notifier = TelegramNotifier()
        notifier.start_bot_server()
        
    except KeyboardInterrupt:
        logger.info("🛑 Telegram բոտը կանգնեցված է")
    except Exception as e:
        # Safe error message formatting
        try:
            error_msg = str(e)
        except:
            error_msg = "Unknown error occurred"
        
        logger.error(f"❌ Սխալ: {error_msg}")

if __name__ == '__main__':
    main() 