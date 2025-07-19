# Fix for missing imghdr module in newer Python versions
import sys
if sys.version_info >= (3, 11):
    import types
    imghdr = types.ModuleType('imghdr')
    imghdr.what = lambda file, h=None: None
    sys.modules['imghdr'] = imghdr

import asyncio
import logging
import os
from telegram import Bot, Update
import requests
import json

logger = logging.getLogger(__name__)

# API configuration
API_BASE_URL = os.environ.get('DJANGO_API_URL', "https://beackkayq.onrender.com")

class TelegramNotifier:
    def __init__(self):
        # Get bot token and chat ID from environment variables
        self.bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.environ.get('TELEGRAM_CHAT_ID')

        # Ավելացրեք .strip() մեթոդը ցանկացած ավելորդ բացատներից ազատվելու համար
        if self.bot_token:
            self.bot_token = self.bot_token.strip()
        if self.chat_id:
            self.chat_id = self.chat_id.strip()
        
        if not self.bot_token:
            # Սա կօգնի ավելի պարզ տեսնել, թե արդյոք թոքենը գոյություն ունի
            logger.error("❌ TELEGRAM_BOT_TOKEN environment variable is not set or is empty.")
            raise ValueError("TELEGRAM_BOT_TOKEN is not set")
        if not self.chat_id:
            logger.error("❌ TELEGRAM_CHAT_ID environment variable is not set or is empty.")
            raise ValueError("TELEGRAM_CHAT_ID is not set")
            
        # Ավելացրեք այս տողերը՝ թոքենը լոգերում տեսնելու համար (մասնակի, անվտանգության համար)
        logger.info(f"✅ Bot Token loaded. Partial: {self.bot_token[:4]}...{self.bot_token[-4:]}")
        logger.info(f"✅ Chat ID loaded: {self.chat_id}")
            
        self.bot = Bot(token=self.bot_token)
        
        # Notification settings (stored in memory for now)
        self.notifications_paused = False
    
    async def send_article_notification(self, article, keywords=None):
        """Send a notification about a new article to Telegram"""
        # Check if notifications are paused
        if self.notifications_paused:
            logger.info("🔇 Ծանուցումները դադարեցված են")
            return
            
        try:
            # Extract source name from URL
            source_name = self._extract_source_name(article.get('source_url') or article.get('link'))
            
            # Format the message (plain text to avoid formatting issues)
            message = f"📰 Նոր հոդված\n\n"
            message += f"🌐 Կայք: {source_name}\n"
            message += f"📰 Վերնագիր: {article.get('title')}\n"
            message += f"🔗 Հղում: {article.get('link')}\n"
            
            if keywords and len(keywords) > 0:
                keywords_text = ', '.join(keywords)
                message += f"🔑 Բանալի բառեր ({len(keywords)}): {keywords_text}\n"
                logger.info(f"📤 Ուղարկվում է {len(keywords)} բանալի բառ: {', '.join(keywords)}")
            else:
                logger.info("📤 Բանալի բառեր չկան")
            
            # Handle created_at field - could be string or datetime
            created_at = article.get('created_at')
            if created_at:
                if isinstance(created_at, str):
                    time_str = created_at
                else:
                    time_str = created_at.strftime('%Y-%m-%d %H:%M:%S')
                message += f"⏰ Ժամանակ: {time_str}"
            
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                disable_web_page_preview=False
            )
            
            logger.info(f"✅ Telegram ծանուցումը ուղարկվեց: {article.get('title', '')[:50]}...")
            
        except Exception as e:
            logger.error(f"❌ Telegram ծանուցման սխալ: {e}")

    async def get_stats_data(self):
        """Get statistics data via API - Now fully async"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                # Try to get stats from API
                async with session.get(f"{API_BASE_URL}/api/stats/", timeout=10) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Failed to get stats from /api/stats/: Status {response.status}")

                # If /api/stats/ doesn't exist, try to gather from articles and keywords APIs
                async with session.get(f"{API_BASE_URL}/api/articles/", timeout=10) as articles_response:
                    articles_data = []
                    if articles_response.status == 200:
                        articles_data = await articles_response.json()
                    else:
                        logger.warning(f"Failed to get articles from /api/articles/: Status {articles_response.status}")

                    total_articles = len(articles_data) if isinstance(articles_data, list) else 0

                async with session.get(f"{API_BASE_URL}/api/keywords/", timeout=10) as keywords_response:
                    total_keywords = 0
                    if keywords_response.status == 200:
                        keywords_list = await keywords_response.json()
                        total_keywords = len(keywords_list) if isinstance(keywords_list, list) else 0
                    else:
                        logger.warning(f"Failed to get keywords from /api/keywords/: Status {keywords_response.status}")

                # Note: For articles_24h, articles_week and top_sources calculation
                # you'll need the /api/stats/ endpoint to provide this data,
                # or you'll need to filter it from the complete data received from the API.
                # Without timestamps, these will be 0 as they are now.
                return {
                    'articles_24h': 0,  # API needs to provide this
                    'articles_week': 0,  # API needs to provide this
                    'total_articles': total_articles,
                    'total_keywords': total_keywords,
                    'top_sources': []  # API needs to provide this
                }

        except aiohttp.ClientError as e:
            logger.error(f"API request failed with client error: {e}")
            return {
                'articles_24h': 0, 'articles_week': 0, 'total_articles': 0,
                'total_keywords': 0, 'top_sources': []
            }
        except Exception as e:
            logger.error(f"An unexpected error occurred during API stats request: {e}")
            return {
                'articles_24h': 0, 'articles_week': 0, 'total_articles': 0,
                'total_keywords': 0, 'top_sources': []
            }

    async def handle_stats_command(self, update, context):
        """Handle /stats command - Now fully async"""
        try:
            stats_data = await self.get_stats_data()
            
            stats_message = f"""📊 Վիճակագրություն

🕐 Վերջին 24 ժամ: {stats_data['articles_24h']} հոդված
📅 Վերջին շաբաթ: {stats_data['articles_week']} հոդված  
📰 Ընդհանուր: {stats_data['total_articles']} հոդված
🔑 Բանալի բառեր: {stats_data['total_keywords']} հատ

🔔 Ծանուցումներ: {'🔇 Դադարեցված' if self.notifications_paused else '🔔 Ակտիվ'}

🌐 Ամենաակտիվ կայքեր (վերջին շաբաթ):"""

            for source in stats_data['top_sources']:
                source_name = self._extract_source_name(source['source_url'])
                stats_message += f"\n  • {source_name}: {source['count']} հոդված"

            await self.bot.send_message(chat_id=update.message.chat_id, text=stats_message)
            
        except Exception as e:
            # Safe error message formatting
            try:
                error_msg = str(e)
            except:
                error_msg = "Unknown error occurred"
            
            logger.error(f"❌ Սխալ: {error_msg}")
            await self.bot.send_message(chat_id=update.message.chat_id, text=f"❌ Սխալ: {error_msg}")

    async def get_keywords_data(self):
        """Get keywords data via API - Now fully async"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{API_BASE_URL}/api/keywords/", timeout=10) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Failed to get keywords from /api/keywords/: Status {response.status}")
                        return []
        except aiohttp.ClientError as e:
            logger.error(f"API keywords request failed with client error: {e}")
            return []
        except Exception as e:
            logger.error(f"An unexpected error occurred during API keywords request: {e}")
            return []

    async def handle_keywords_command(self, update, context):
        """Handle /keywords command - Now fully async"""
        try:
            keywords = await self.get_keywords_data()
            
            if not keywords:
                await self.bot.send_message(chat_id=update.message.chat_id, text="❌ Բանալի բառեր չկան")
                return
            
            keywords_text = "🔑 Ընթացիկ բանալի բառեր:\n\n"
            for i, keyword in enumerate(keywords, 1):
                # Handle both dictionary and object formats
                if isinstance(keyword, dict):
                    keyword_text = keyword.get('word', str(keyword))
                else:
                    keyword_text = keyword.word if hasattr(keyword, 'word') else str(keyword)
                keywords_text += f"{i}. {keyword_text}\n"
            
            keywords_text += f"\n📝 Ընդհանուր: {len(keywords)} բանալի բառ"
            
            await self.bot.send_message(chat_id=update.message.chat_id, text=keywords_text)
            
        except Exception as e:
            # Safe error message formatting
            try:
                error_msg = str(e)
            except:
                error_msg = "Unknown error occurred"
            
            logger.error(f"❌ Սխալ: {error_msg}")
            await self.bot.send_message(chat_id=update.message.chat_id, text=f"❌ Սխալ: {error_msg}")

    async def handle_pause_command(self, update, context):
        """Handle /pause command - Now async"""
        self.notifications_paused = True
        await self.bot.send_message(chat_id=update.message.chat_id, text="🔇 Ծանուցումները դադարեցվել են\n\nԱկտիվացնելու համար օգտագործեք /resume")

    async def handle_resume_command(self, update, context):
        """Handle /resume command - Now async"""
        self.notifications_paused = False
        await self.bot.send_message(chat_id=update.message.chat_id, text="🔔 Ծանուցումները ակտիվացվել են")

    async def add_keyword(self, keyword_text):
        """Add keyword via API - Now fully async"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{API_BASE_URL}/api/keywords/",
                    json={'word': keyword_text},
                    timeout=10
                ) as response:
                    if response.status == 201:
                        return await response.json(), True
                    elif response.status == 200:
                        return await response.json(), False  # Already exists
                    else:
                        logger.error(f"Failed to add keyword via API: Status {response.status}")
                        return None, False
        except aiohttp.ClientError as e:
            logger.error(f"API add keyword request failed with client error: {e}")
            return None, False
        except Exception as e:
            logger.error(f"An unexpected error occurred during API add keyword request: {e}")
            return None, False

    async def handle_add_keyword_command(self, update, context):
        """Handle /add_keyword command - Now fully async"""
        try:
            if not context.args:
                await self.bot.send_message(chat_id=update.message.chat_id, text="❌ Գրեք բանալի բառը\n\nՕրինակ: /add_keyword Հայաստան")
                return
            
            keyword_text = " ".join(context.args).strip()
            keyword_obj, created = await self.add_keyword(keyword_text)
            
            if created:
                await self.bot.send_message(chat_id=update.message.chat_id, text=f"✅ Ավելացվել է բանալի բառ: {keyword_text}")
            else:
                await self.bot.send_message(chat_id=update.message.chat_id, text=f"🔄 Արդեն գոյություն ունի: {keyword_text}")
                
        except Exception as e:
            # Safe error message formatting
            try:
                error_msg = str(e)
            except:
                error_msg = "Unknown error occurred"
            
            logger.error(f"❌ Սխալ: {error_msg}")
            await self.bot.send_message(chat_id=update.message.chat_id, text=f"❌ Սխալ: {error_msg}")

    async def remove_keyword(self, keyword_text):
        """Remove keyword via API - Now fully async"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    f"{API_BASE_URL}/api/keywords/{keyword_text}/",
                    timeout=10
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get('deleted_count', 0)
                    else:
                        logger.error(f"Failed to remove keyword via API: Status {response.status}")
                        return 0
        except aiohttp.ClientError as e:
            logger.error(f"API remove keyword request failed with client error: {e}")
            return 0
        except Exception as e:
            logger.error(f"An unexpected error occurred during API remove keyword request: {e}")
            return 0

    async def handle_remove_keyword_command(self, update, context):
        """Handle /remove_keyword command - Now fully async"""
        try:
            if not context.args:
                await self.bot.send_message(chat_id=update.message.chat_id, text="❌ Գրեք բանալի բառը\n\nՕրինակ: /remove_keyword Հայաստան")
                return
            
            keyword_text = " ".join(context.args).strip()
            deleted_count = await self.remove_keyword(keyword_text)
            
            if deleted_count > 0:
                await self.bot.send_message(chat_id=update.message.chat_id, text=f"🗑️ Ջնջվել է բանալի բառ: {keyword_text}")
            else:
                await self.bot.send_message(chat_id=update.message.chat_id, text=f"❌ Բանալի բառը չգտնվեց: {keyword_text}")
                
        except Exception as e:
            # Safe error message formatting
            try:
                error_msg = str(e)
            except:
                error_msg = "Unknown error occurred"
            
            logger.error(f"❌ Սխալ: {error_msg}")
            await self.bot.send_message(chat_id=update.message.chat_id, text=f"❌ Սխալ: {error_msg}")

    async def handle_help_command(self, update, context):
        """Handle /help command - Now async"""
        help_text = """🤖 Telegram բոտի հրամաններ:

📊 /stats - վիճակագրություն
🔑 /keywords - ընթացիկ բանալի բառեր  
🔇 /pause - ծանուցումները դադարեցնել
🔔 /resume - ծանուցումները ակտիվացնել

Բանալի բառերի կառավարում:
➕ /add_keyword [բառ] - բանալի բառ ավելացնել
🗑️ /remove_keyword [բառ] - բանալի բառ ջնջել

ℹ️ /help - այս ցուցակը

Օրինակ:
/add_keyword Հայաստան
/remove_keyword տնտեսություն"""

        await self.bot.send_message(chat_id=update.message.chat_id, text=help_text)

    def _extract_source_name(self, url):
        """Extract a readable source name from URL"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Map known domains to Armenian names
            domain_names = {
                'armenpress.am': 'Armenpress',
                'news.am': 'News.am',
                'panorama.am': 'Panorama.am',
                'asbarez.com': 'Asbarez',
                'aysor.am': 'Aysor',
                'lurer.com': 'Lurer',
                'tert.am': 'Tert.am',
                'armtimes.com': 'Armtimes',
                'yerkir.am': 'Yerkir',
                'armlur.am': 'Armlur',
                'mamul.am': 'Mamul',
                'past.am': 'Past.am',
                'armday.am': 'Armday',
                'hayeli.am': 'Hayeli',
                'blognews.am': 'Blognews',
                'slaq.am': 'Slaq',
                'irakanum.am': 'Irakanum',
                'norlur.am': 'Norlur',
                'newday.am': 'Newday',
                'politik.am': 'Politik',
                'pastinfo.am': 'Pastinfo',
                'hayacq.am': 'Hayacq',
                'yerevan-today.com': 'Yerevan Today',
                'armeniatoday.news': 'Armenia Today',
                'armlife.am': 'Armlife',
                '168.am': '168.am',
                '7or.am': '7or.am'
            }
            
            return domain_names.get(domain, domain.title())
        except:
            return url
    
    def send_article_sync(self, article, keywords=None):
        """Synchronous wrapper for sending article notifications"""
        loop = None
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run the async function
            loop.run_until_complete(self.send_article_notification(article, keywords))
            
        except Exception as e:
            logger.error(f"❌ Telegram sync ծանուցման սխալ: {e}")
        finally:
            if loop and not loop.is_closed():
                try:
                    loop.close()
                except Exception as close_error:
                    logger.error(f"❌ Failed to close loop in send_article_sync: {close_error}")

    def start_bot_server(self):
        """Start the Telegram bot server to handle commands"""
        try:
            # Use v13.x (sync) approach
            from telegram.ext import Updater, CommandHandler
            
            updater = Updater(token=self.bot_token, use_context=True)
            dispatcher = updater.dispatcher
            
            # For v13.x, we need sync wrappers for async functions
            def sync_wrapper(async_func):
                def wrapper(update, context):
                    loop = None
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(async_func(update, context))
                    except Exception as e:
                        # Safe error message formatting
                        try:
                            error_msg = str(e)
                        except:
                            error_msg = "Unknown error occurred"
                        
                        logger.error(f"❌ Handler error in {async_func.__name__}: {error_msg}")
                        # Don't try to send error message from sync wrapper to avoid Message object issues
                    finally:
                        if loop and not loop.is_closed():
                            try:
                                loop.close()
                            except Exception as close_error:
                                logger.error(f"❌ Failed to close loop: {close_error}")
                return wrapper
            
            # Add command handlers with sync wrappers
            dispatcher.add_handler(CommandHandler("stats", sync_wrapper(self.handle_stats_command)))
            dispatcher.add_handler(CommandHandler("keywords", sync_wrapper(self.handle_keywords_command)))
            dispatcher.add_handler(CommandHandler("pause", sync_wrapper(self.handle_pause_command)))
            dispatcher.add_handler(CommandHandler("resume", sync_wrapper(self.handle_resume_command)))
            dispatcher.add_handler(CommandHandler("add_keyword", sync_wrapper(self.handle_add_keyword_command)))
            dispatcher.add_handler(CommandHandler("remove_keyword", sync_wrapper(self.handle_remove_keyword_command)))
            dispatcher.add_handler(CommandHandler("help", sync_wrapper(self.handle_help_command)))
            dispatcher.add_handler(CommandHandler("start", sync_wrapper(self.handle_help_command)))
            
            # Start the bot
            logger.info("🤖 Telegram բոտ սերվերը սկսվում է...")
            updater.start_polling()
            updater.idle()
            
        except Exception as e:
            logger.error(f"❌ Telegram բոտ սերվերի սխալ: {e}")