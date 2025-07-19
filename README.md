# 🤖 Telegram News Bot

Հայերեն լրատվական կայքերից հոդվածներ հավաքող և Telegram-ում ծանուցումներ ուղարկող բոտ:

## ✨ Հնարավորություններ

- 📰 Հոդվածների ավտոմատ հավաքագրում հայերեն կայքերից
- 🔔 Telegram ծանուցումներ բանալի բառերի համապատասխանության դեպքում
- 📊 Վիճակագրություն և բանալի բառերի կառավարում
- 🔑 Բանալի բառերի ավելացում/ջնջում Telegram-ից
- 🔇 Ծանուցումների դադարեցում/ակտիվացում

## 🚀 Render-ում Deploy

### 1. Telegram Bot Ստեղծում

1. **Bot Token ստանալու համար:**
   - Գնացեք [@BotFather](https://t.me/botfather) Telegram-ում
   - Ուղարկեք `/newbot` հրամանը
   - Հետևեք հրահանգներին
   - Պահպանեք bot token-ը

2. **Chat ID ստանալու համար:**
   - Ուղարկեք հաղորդագրություն ձեր bot-ին
   - Գնացեք: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Գտեք `"chat" -> "id"` դաշտը

### 2. Render-ում Կարգավորում

1. **Նոր Worker Service ստեղծել:**
   - Գնացեք [Render Dashboard](https://dashboard.render.com)
   - Սեղմեք "New +" -> "Worker Service"
   - Կապակցեք ձեր GitHub repository-ն
   - Ընտրեք `telegram-bot` directory-ը

2. **Environment Variables ավելացնել:**
   ```
   TELEGRAM_BOT_TOKEN = ձեր_bot_token_ը
   TELEGRAM_CHAT_ID = ձեր_chat_id_ն
   DATABASE_URL = ձեր_django_database_url_ը (ավտոմատ կսահմանվի)
   DJANGO_SETTINGS_MODULE = beackkayq.settings
   DJANGO_API_URL = https://beackkayq.onrender.com
   ```

3. **Build Settings:**
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python start_telegram_bot.py`

### 3. Deploy

```bash
# Commit և push
git add .
git commit -m "Add Telegram bot deployment"
git push origin main
```

## 📱 Bot Հրամաններ

| Հրաման | Նկարագրություն |
|--------|----------------|
| `/start` | Բոլոր հրամանները |
| `/stats` | Վիճակագրություն |
| `/keywords` | Ընթացիկ բանալի բառեր |
| `/pause` | Ծանուցումները դադարեցնել |
| `/resume` | Ծանուցումները ակտիվացնել |
| `/add_keyword [բառ]` | Բանալի բառ ավելացնել |
| `/remove_keyword [բառ]` | Բանալի բառ ջնջել |
| `/help` | Օգնություն |

## 📁 Ֆայլերի Կառուցվածք

```
telegram-bot/
├── telegram_bot.py          # Հիմնական bot կոդ
├── start_telegram_bot.py    # Bot-ը սկսելու script
├── render.yaml             # Render կոնֆիգուրացիա
├── requirements.txt        # Python dependencies
└── README.md              # Այս ֆայլը
```

## 🔧 Troubleshooting

### Սովորական Սխալներ

1. **Bot Token Error:**
   - Ստուգեք, թե արդյոք bot token-ը ճիշտ է
   - Համոզվեք, որ bot-ը ակտիվ է

2. **Chat ID Error:**
   - Ստուգեք, թե արդյոք chat ID-ն ճիշտ է
   - Համոզվեք, որ դուք ուղարկել եք հաղորդագրություն bot-ին

3. **API Connection Error:**
   - Ստուգեք, թե արդյոք Django backend-ը աշխատում է
   - Ստուգեք `DJANGO_API_URL` environment variable-ը

### Logs Ստուգել

Render-ում:
1. Գնացեք ձեր worker service
2. Սեղմեք "Logs" tab
3. Ստուգեք error messages-երը

---

**Հաջողություն deployment-ի հետ! 🚀** 