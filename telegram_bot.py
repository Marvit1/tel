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
import sys
import django
from telegram import Bot, Update
from django.utils import timezone
from datetime import timedelta
from asgiref.sync import sync_to_async

# Setup Django environment - For Render deployment
current_dir = os.path.dirname(os.path.abspath(__file__))

# For Render deployment, we need to find the backend directory
# Try different possible paths
possible_backend_paths = [
    os.path.join(current_dir, '..', 'backend'),  # ../backend
    os.path.join(current_dir, '..', 'Scrap123', 'backend'),  # ../Scrap123/backend
    os.path.join(current_dir, '..', '..', 'backend'),  # ../../backend
]

backend_path = None
for path in possible_backend_paths:
    if os.path.exists(path):
        backend_path = os.path.abspath(path)
        break

# Log the paths for debugging
logger = logging.getLogger(__name__)
logger.info(f"Current directory: {current_dir}")

if backend_path:
    logger.info(f"Found backend path: {backend_path}")
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
        logger.info(f"Added {backend_path} to sys.path")
else:
    logger.warning("⚠️ Backend path not found locally - this is normal for Render deployment")
    logger.info("Will use Django settings from environment variables")

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'beackkayq.settings')
logger.info(f"Django settings module: {os.environ.get('DJANGO_SETTINGS_MODULE')}")

try:
    django.setup()
    logger.info("✅ Django setup completed successfully")
except Exception as e:
    logger.error(f"❌ Django setup failed: {e}")
    # For Render deployment, we might need to continue anyway
    logger.warning("⚠️ Continuing without Django setup - will use API calls instead")
    # Don't raise the exception for now

from django.conf import settings
import requests
import json

logger = logging.getLogger(__name__)

# API configuration
API_BASE_URL = os.environ.get('DJANGO_API_URL', "https://beackkayq.onrender.com")

class TelegramNotifier:
    def __init__(self):
        # Get bot token and chat ID from environment variables or Django settings
        try:
            self.bot_token = os.environ.get('TELEGRAM_BOT_TOKEN') or settings.TELEGRAM_BOT_TOKEN
            self.chat_id = os.environ.get('TELEGRAM_CHAT_ID') or settings.TELEGRAM_CHAT_ID
        except:
            self.bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
            self.chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is not set")
        if not self.chat_id:
            raise ValueError("TELEGRAM_CHAT_ID is not set")
            
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
            source_name = self._extract_source_name(article.source_url or article.link)
            
            # Format the message (plain text to avoid formatting issues)
            message = f"📰 Նոր հոդված\n\n"
            message += f"🌐 Կայք: {source_name}\n"
            message += f"📰 Վերնագիր: {article.title}\n"
            message += f"🔗 Հղում: {article.link}\n"
            
            if keywords and len(keywords) > 0:
                keywords_text = ', '.join(keywords)
                message += f"🔑 Բանալի բառեր ({len(keywords)}): {keywords_text}\n"
                logger.info(f"📤 Ուղարկվում է {len(keywords)} բանալի բառ: {', '.join(keywords)}")
            else:
                logger.info("📤 Բանալի բառեր չկան")
            
            message += f"⏰ Ժամանակ: {article.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
            
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                disable_web_page_preview=False
            )
            
            logger.info(f"✅ Telegram ծանուցումը ուղարկվեց: {article.title[:50]}...")
            
        except Exception as e:
            logger.error(f"❌ Telegram ծանուցման սխալ: {e}")

    async def get_stats_data(self):
        """Get statistics data via API - Now fully async"""
        try:
            # Use aiohttp for async HTTP requests
            import aiohttp
            async with aiohttp.ClientSession() as session:
                # Try to get stats from API
                async with session.get(f"{API_BASE_URL}/api/stats/", timeout=10) as response:
                    if response.status == 200:
                        return await response.json()
        except Exception as e:
            logger.warning(f"API stats request failed: {e}")
        
        # Try to get stats from articles endpoint
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{API_BASE_URL}/api/articles/", timeout=10) as response:
                    if response.status == 200:
                        articles_data = await response.json()
                        total_articles = len(articles_data) if isinstance(articles_data, list) else 0
                        
                        # Get keywords count
                        async with session.get(f"{API_BASE_URL}/api/keywords/", timeout=10) as keywords_response:
                            total_keywords = len(await keywords_response.json()) if keywords_response.status == 200 else 0
                        
                        return {
                            'articles_24h': 0,  # We can't calculate this without timestamps
                            'articles_week': 0,  # We can't calculate this without timestamps
                            'total_articles': total_articles,
                            'total_keywords': total_keywords,
                            'top_sources': []
                        }
        except Exception as e:
            logger.warning(f"API articles/keywords request failed: {e}")
        
        # Fallback to Django models if available
        try:
            from main.models import NewsArticle, Keyword
            from django.db.models import Count
            
            # Use sync_to_async for Django ORM calls
            @sync_to_async
            def get_django_stats():
                last_24h = timezone.now() - timedelta(hours=24)
                last_week = timezone.now() - timedelta(days=7)
                
                articles_24h = NewsArticle.objects.filter(created_at__gte=last_24h).count()
                articles_week = NewsArticle.objects.filter(created_at__gte=last_week).count()
                total_articles = NewsArticle.objects.count()
                total_keywords = Keyword.objects.count()
                
                # Get most active sources
                top_sources = list(NewsArticle.objects.filter(created_at__gte=last_week)
                                  .values('source_url')
                                  .annotate(count=Count('id'))
                                  .order_by('-count')[:5])
                
                return {
                    'articles_24h': articles_24h,
                    'articles_week': articles_week,
                    'total_articles': total_articles,
                    'total_keywords': total_keywords,
                    'top_sources': top_sources
                }
            
            return await get_django_stats()
        except Exception as e:
            logger.error(f"All methods failed: {e}")
            return {
                'articles_24h': 0,
                'articles_week': 0,
                'total_articles': 0,
                'total_keywords': 0,
                'top_sources': []
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

            await update.message.reply_text(stats_message)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Սխալ: {str(e)}")

    async def get_keywords_data(self):
        """Get keywords data via API - Now fully async"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{API_BASE_URL}/api/keywords/", timeout=10) as response:
                    if response.status == 200:
                        return await response.json()
        except Exception as e:
            logger.warning(f"API keywords request failed: {e}")
        
        # Fallback to Django models if available
        try:
            from main.models import Keyword
            
            @sync_to_async
            def get_django_keywords():
                return list(Keyword.objects.all())
            
            return await get_django_keywords()
        except Exception as e:
            logger.error(f"Both API and Django models failed: {e}")
            return []

    async def handle_keywords_command(self, update, context):
        """Handle /keywords command - Now fully async"""
        try:
            keywords = await self.get_keywords_data()
            
            if not keywords:
                await update.message.reply_text("❌ Բանալի բառեր չկան")
                return
            
            keywords_text = "🔑 Ընթացիկ բանալի բառեր:\n\n"
            for i, keyword in enumerate(keywords, 1):
                keyword_text = keyword.word if hasattr(keyword, 'word') else keyword
                keywords_text += f"{i}. {keyword_text}\n"
            
            keywords_text += f"\n📝 Ընդհանուր: {len(keywords)} բանալի բառ"
            
            await update.message.reply_text(keywords_text)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Սխալ: {str(e)}")

    async def handle_pause_command(self, update, context):
        """Handle /pause command - Now async"""
        self.notifications_paused = True
        await update.message.reply_text("🔇 Ծանուցումները դադարեցվել են\n\nԱկտիվացնելու համար օգտագործեք /resume")

    async def handle_resume_command(self, update, context):
        """Handle /resume command - Now async"""
        self.notifications_paused = False
        await update.message.reply_text("🔔 Ծանուցումները ակտիվացվել են")

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
        except Exception as e:
            logger.warning(f"API add keyword request failed: {e}")
        
        # Fallback to Django models if available
        try:
            from main.models import Keyword
            
            @sync_to_async
            def add_django_keyword():
                return Keyword.objects.get_or_create(word=keyword_text)
            
            return await add_django_keyword()
        except Exception as e:
            logger.error(f"Both API and Django models failed: {e}")
            return None, False

    async def handle_add_keyword_command(self, update, context):
        """Handle /add_keyword command - Now fully async"""
        try:
            if not context.args:
                await update.message.reply_text("❌ Գրեք բանալի բառը\n\nՕրինակ: /add_keyword Հայաստան")
                return
            
            keyword_text = " ".join(context.args).strip()
            keyword_obj, created = await self.add_keyword(keyword_text)
            
            if created:
                await update.message.reply_text(f"✅ Ավելացվել է բանալի բառ: {keyword_text}")
            else:
                await update.message.reply_text(f"🔄 Արդեն գոյություն ունի: {keyword_text}")
                
        except Exception as e:
            await update.message.reply_text(f"❌ Սխալ: {str(e)}")

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
        except Exception as e:
            logger.warning(f"API remove keyword request failed: {e}")
        
        # Fallback to Django models if available
        try:
            from main.models import Keyword
            
            @sync_to_async
            def remove_django_keyword():
                return Keyword.objects.filter(word=keyword_text).delete()[0]
            
            return await remove_django_keyword()
        except Exception as e:
            logger.error(f"Both API and Django models failed: {e}")
            return 0

    async def handle_remove_keyword_command(self, update, context):
        """Handle /remove_keyword command - Now fully async"""
        try:
            if not context.args:
                await update.message.reply_text("❌ Գրեք բանալի բառը\n\nՕրինակ: /remove_keyword Հայաստան")
                return
            
            keyword_text = " ".join(context.args).strip()
            deleted_count = await self.remove_keyword(keyword_text)
            
            if deleted_count > 0:
                await update.message.reply_text(f"🗑️ Ջնջվել է բանալի բառ: {keyword_text}")
            else:
                await update.message.reply_text(f"❌ Բանալի բառը չգտնվեց: {keyword_text}")
                
        except Exception as e:
            await update.message.reply_text(f"❌ Սխալ: {str(e)}")

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

        await update.message.reply_text(help_text)

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
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run the async function
            loop.run_until_complete(self.send_article_notification(article, keywords))
            
        except Exception as e:
            logger.error(f"❌ Telegram sync ծանուցման սխալ: {e}")
        finally:
            try:
                loop.close()
            except:
                pass

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
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(async_func(update, context))
                    finally:
                        loop.close()
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