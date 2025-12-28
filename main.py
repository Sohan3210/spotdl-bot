import telebot
import subprocess
import os
import re
import glob
import time
import sys
import threading
import random
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    print("❌ Error: BOT_TOKEN not found in .env file!")
    print("💡 For Render: Set BOT_TOKEN in Environment Variables")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# Rate limiting and concurrency control
download_lock = threading.Semaphore(1)
last_download_time = 0
MIN_DOWNLOAD_INTERVAL = 2

# Storage for reminder users
reminder_users = set()

# Interesting facts database
INTERESTING_FACTS = [
    "🎵 Did you know? The most expensive music video ever made cost $7 million - Michael Jackson's 'Scream'",
    "🧠 Did you know? Listening to music releases dopamine in your brain - the same chemical released when you eat chocolate!",
    "🎸 Did you know? The electric guitar was invented in 1931, but didn't become popular until the 1950s",
    "🎼 Did you know? Mozart wrote his first symphony when he was just 8 years old!",
    "🎧 Did you know? The world's longest song is 'The Rise and Fall of Bossanova' - it's 13 hours long!",
    "🎹 Did you know? Freddie Mercury of Queen could play piano backwards with his left hand!",
    "🥁 Did you know? The human heart beats in rhythm - it's like having a drummer inside you!",
    "🎤 Did you know? Your voice is unique - no two people have the exact same voice!",
    "🎵 Did you know? Cows produce more milk when they listen to slow music!",
    "🧬 Did you know? Music can help plants grow faster according to scientific studies!",
]

# Helper functions
def is_spotify_url(url):
    return bool(re.match(r'(https?://)?(open\.)?spotify\.com/(track|album|playlist)/', url))

def is_youtube_url(url):
    return bool(re.match(r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/', url))

def get_spotify_type(url):
    if '/track/' in url:
        return 'track', '🎵'
    elif '/album/' in url:
        return 'album', '💿'
    elif '/playlist/' in url:
        return 'playlist', '📋'
    return None, None

def download_with_spotdl(url):
    global last_download_time
    
    with download_lock:
        time_since_last = time.time() - last_download_time
        if time_since_last < MIN_DOWNLOAD_INTERVAL:
            time.sleep(MIN_DOWNLOAD_INTERVAL - time_since_last)
        
        try:
            os.makedirs('downloads', exist_ok=True)
            
            result = subprocess.run(
                [sys.executable, '-m', 'spotdl', url, 
                 '--output', 'downloads',
                 '--format', 'm4a',
                 '--bitrate', 'disable',
                 '--threads', '3'],
                capture_output=True,
                text=True,
                timeout=240
            )
            
            last_download_time = time.time()
            
            if result.returncode == 0:
                files = glob.glob('downloads/*.m4a')
                if files:
                    return {'success': True, 'files': files}
            
            return {'success': False, 'error': result.stderr or 'Download failed'}
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Timeout (4 min)'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

def cleanup_old_files():
    try:
        current_time = time.time()
        for filename in os.listdir('downloads'):
            file_path = os.path.join('downloads', filename)
            if os.path.isfile(file_path):
                if current_time - os.path.getctime(file_path) > 600:
                    os.remove(file_path)
                    print(f"🗑️ Cleaned: {filename}")
    except:
        pass

def get_storage_usage():
    try:
        if not os.path.exists('downloads'):
            os.makedirs('downloads', exist_ok=True)
        stat = os.statvfs('downloads')
        free_mb = (stat.f_bavail * stat.f_frsize) / (1024 * 1024)
        return free_mb
    except:
        return 500

def send_hourly_reminders():
    while True:
        try:
            time.sleep(3600)
            
            if not reminder_users:
                continue
            
            current_time = datetime.now().strftime("%I:%M %p")
            
            for chat_id in list(reminder_users):
                try:
                    fact = random.choice(INTERESTING_FACTS)
                    reminder_text = f"⏰ *Hourly Reminder* - {current_time}\n\n{fact}\n\n🎵 *Ahmed Sohan's Music Bot*\n💻 @ahmed.sohan123"
                    bot.send_message(chat_id, reminder_text, parse_mode='Markdown')
                    print(f"✅ Sent reminder to {chat_id}")
                    time.sleep(0.1)
                except Exception as e:
                    print(f"❌ Failed to send reminder to {chat_id}: {e}")
                    reminder_users.discard(chat_id)
        except Exception as e:
            print(f"❌ Reminder thread error: {e}")
            time.sleep(60)

# Bot commands
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = """🎵 *SpotDL Music Downloader Bot*

💻 *Developer:* Ahmed Sohan
📘 *Facebook:* @ahmed.sohan123

Send me:
• 🎵 Spotify track link
• 💿 Spotify album link  
• 📋 Spotify playlist link
• 🎥 YouTube link
• 🔍 Song name (search)

*Commands:*
/start - Show this message
/help - Get help
/info - Bot information
/reminder - Toggle hourly reminders

*Quality:* Best Available M4A 🎧

Just send a link to begin! 🚀"""
    
    bot.reply_to(message, welcome_text, parse_mode='Markdown')
    print(f"👤 New user: {message.from_user.first_name}")

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = """ℹ️ *How to use:*

*For Spotify:*
1. Copy Spotify link
2. Send it to me
3. Wait for download
4. Receive best quality M4A! 🎧

*For YouTube:*
1. Copy YouTube link
2. Send it to me
3. Get best quality M4A

*Search:*
Type: "Song Name Artist"

*Features:*
✅ Best quality M4A (up to 256kbps AAC)
✅ Album artwork
✅ Complete metadata
✅ Fast downloads

*Note:* 
⚠️ Max 50 MB per file
⚠️ One download at a time
⚠️ Please wait between requests

*Examples:*
• https://open.spotify.com/track/...
• https://youtube.com/watch?v=...
• Shape of You Ed Sheeran"""
    
    bot.reply_to(message, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['info'])
def send_info(message):
    info_text = """🤖 *Bot Information*

💻 *Developer*
Name: Ahmed Sohan
Facebook: @ahmed.sohan123

*Bot Specs:*
• Quality: Best M4A (AAC ~256kbps)
• Format: M4A
• Hosted: Render.com 24/7

*Powered by:*
• spotDL - Music downloader
• yt-dlp - YouTube downloader
• pyTelegramBotAPI

⚠️ *Disclaimer:*
Only download content you have rights to.
Respect copyright laws and support artists!

🎵 Enjoy high quality music! 🎵"""
    
    bot.reply_to(message, info_text, parse_mode='Markdown')

@bot.message_handler(commands=['reminder'])
def toggle_reminder(message):
    chat_id = message.chat.id
    
    if chat_id in reminder_users:
        reminder_users.discard(chat_id)
        response = """⏰ *Hourly Reminders OFF*

You will no longer receive hourly reminders.

To turn them back on, send /reminder again."""
    else:
        reminder_users.add(chat_id)
        response = """⏰ *Hourly Reminders ON!*

You'll receive:
• Hourly time check
• Interesting facts
• Music & science trivia

You'll get your first reminder in 1 hour!

To turn off, send /reminder again."""
    
    bot.reply_to(message, response, parse_mode='Markdown')
    print(f"🔔 Reminder toggled for {message.from_user.first_name}: {'ON' if chat_id in reminder_users else 'OFF'}")

# Handle Spotify URLs
@bot.message_handler(func=lambda m: is_spotify_url(m.text))
def handle_spotify(message):
    url = message.text.strip()
    type_name, emoji = get_spotify_type(url)
    
    if not type_name:
        bot.reply_to(message, "❌ Invalid Spotify link")
        return
    
    free_mb = get_storage_usage()
    if free_mb < 50:
        bot.reply_to(message, "⚠️ Low storage! Please try again in a moment.")
        cleanup_old_files()
        return
    
    if type_name in ['playlist', 'album']:
        status = bot.send_message(message.chat.id, 
            f"{emoji} Downloading {type_name}...\n\n⏳ This may take a while. Songs will be sent one at a time.")
    else:
        status = bot.send_message(message.chat.id, 
            f"{emoji} Downloading {type_name}...\n\n⏳ Please wait, processing...")
    
    cleanup_old_files()
    result = download_with_spotdl(url)
    
    if result['success']:
        try:
            files = result['files']
            total_files = len(files)
            
            if total_files == 0:
                bot.edit_message_text("❌ No files downloaded", message.chat.id, status.message_id)
                return
            
            if total_files > 1:
                bot.edit_message_text(
                    f"✅ Downloaded {total_files} tracks!\n📤 Sending one at a time...",
                    message.chat.id, 
                    status.message_id
                )
            else:
                bot.edit_message_text(
                    f"✅ Downloaded! (Best Quality)\n📤 Uploading...",
                    message.chat.id, 
                    status.message_id
                )
            
            sent_count = 0
            for i, file_path in enumerate(files, 1):
                try:
                    file_size = os.path.getsize(file_path)
                    
                    if file_size > 50 * 1024 * 1024:
                        print(f"⚠️ Skipped (too large): {os.path.basename(file_path)}")
                        os.remove(file_path)
                        continue
                    
                    with open(file_path, 'rb') as audio:
                        if total_files > 1:
                            caption = f"{emoji} Track {i}/{total_files} - Best Quality M4A\n\n💻 @ahmed.sohan123"
                        else:
                            caption = f"{emoji} Best Quality M4A\n\n💻 @ahmed.sohan123"
                        
                        bot.send_audio(
                            message.chat.id, 
                            audio, 
                            caption=caption,
                            performer="SpotDL Bot"
                        )
                    
                    os.remove(file_path)
                    sent_count += 1
                    print(f"✅ Sent {i}/{total_files}: {os.path.basename(file_path)}")
                    
                    if i < total_files and total_files > 3:
                        time.sleep(0.5)
                        
                except Exception as e:
                    print(f"❌ Error sending file: {e}")
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    continue
            
            bot.delete_message(message.chat.id, status.message_id)
            
            if total_files > 1:
                completion_msg = f"✅ {emoji} Completed!\n\nSent: {sent_count}/{total_files} tracks\n\n💻 @ahmed.sohan123"
                bot.send_message(message.chat.id, completion_msg)
                
        except Exception as e:
            bot.edit_message_text(f"❌ Error: {str(e)}", message.chat.id, status.message_id)
            for file_path in result.get('files', []):
                if os.path.exists(file_path):
                    os.remove(file_path)
    else:
        bot.edit_message_text(
            f"❌ Download failed!\n\n{result['error']}\n\n💡 Try:\n• Check the link\n• Try again in a moment",
            message.chat.id, 
            status.message_id
        )

# Handle YouTube URLs
@bot.message_handler(func=lambda m: is_youtube_url(m.text))
def handle_youtube(message):
    url = message.text.strip()
    
    free_mb = get_storage_usage()
    if free_mb < 50:
        bot.reply_to(message, "⚠️ Low storage! Please try again in a moment.")
        cleanup_old_files()
        return
    
    status = bot.send_message(message.chat.id, 
        "🎵 Downloading from YouTube...\n\n⚡ Fast mode!")
    cleanup_old_files()
    result = download_with_spotdl(url)
    
    if result['success']:
        try:
            files = result['files']
            if not files:
                bot.edit_message_text("❌ No files downloaded", message.chat.id, status.message_id)
                return
            
            file_path = files[0]
            file_size = os.path.getsize(file_path)
            
            if file_size > 50 * 1024 * 1024:
                bot.edit_message_text(
                    f"❌ File too large: {file_size/(1024*1024):.1f} MB\n"
                    f"Telegram limit: 50 MB",
                    message.chat.id,
                    status.message_id
                )
                os.remove(file_path)
                return
            
            bot.edit_message_text(
                f"✅ Downloaded! (Best Quality M4A)\n📤 Uploading...",
                message.chat.id, 
                status.message_id
            )
            
            with open(file_path, 'rb') as audio:
                bot.send_audio(
                    message.chat.id, 
                    audio, 
                    caption=f"🎵 Best Quality M4A\n\n💻 @ahmed.sohan123"
                )
            
            bot.delete_message(message.chat.id, status.message_id)
            os.remove(file_path)
        except Exception as e:
            bot.edit_message_text(f"❌ Error: {str(e)}", message.chat.id, status.message_id)
            for file_path in result.get('files', []):
                if os.path.exists(file_path):
                    os.remove(file_path)
    else:
        bot.edit_message_text(
            f"❌ Download failed!\n\n{result['error']}", 
            message.chat.id, 
            status.message_id
        )

# Handle text search
@bot.message_handler(func=lambda m: True)
def handle_search(message):
    query = message.text.strip()
    
    if len(query) < 3:
        bot.reply_to(message, "❌ Query too short (minimum 3 characters)")
        return
    
    free_mb = get_storage_usage()
    if free_mb < 100:
        bot.reply_to(message, "⚠️ Low storage! Please try again in a moment.")
        cleanup_old_files()
        return
    
    status = bot.send_message(message.chat.id, 
        f"🔍 Searching for '{query}'...\n\n⚡ Fast mode!")
    cleanup_old_files()
    result = download_with_spotdl(query)
    
    if result['success']:
        try:
            files = result['files']
            if not files:
                bot.edit_message_text("❌ No results found", message.chat.id, status.message_id)
                return
                
            file_path = files[0]
            file_size = os.path.getsize(file_path)
            
            if file_size > 50 * 1024 * 1024:
                bot.edit_message_text(
                    f"❌ File too large: {file_size/(1024*1024):.1f} MB",
                    message.chat.id,
                    status.message_id
                )
                os.remove(file_path)
                return
            
            bot.edit_message_text(
                f"✅ Found! (Best Quality M4A)\n📤 Uploading...",
                message.chat.id, 
                status.message_id
            )
            
            with open(file_path, 'rb') as audio:
                bot.send_audio(
                    message.chat.id, 
                    audio, 
                    caption=f"🎵 Best Quality M4A\n\n💻 @ahmed.sohan123"
                )
            
            bot.delete_message(message.chat.id, status.message_id)
            os.remove(file_path)
        except Exception as e:
            bot.edit_message_text(f"❌ Error: {str(e)}", message.chat.id, status.message_id)
            if os.path.exists(file_path):
                os.remove(file_path)
    else:
        bot.edit_message_text(
            f"❌ Not found: '{query}'\n\n💡 Try:\n• More specific keywords\n• Include artist name\n• Use direct Spotify/YouTube link",
            message.chat.id,
            status.message_id
        )

# Start bot
if __name__ == '__main__':
    print("=" * 50)
    print("🎵 SpotDL Music Downloader Bot")
    print("=" * 50)
    print("💻 Developer: Ahmed Sohan")
    print("📘 Facebook: @ahmed.sohan123")
    print("🎧 Quality: Best M4A (AAC ~256kbps)")
    print("☁️  Hosted on: Render.com")
    print("=" * 50)
    print("🚀 Bot is running...")
    print("⏰ Hourly reminder system active")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    # Start hourly reminder thread
    reminder_thread = threading.Thread(target=send_hourly_reminders, daemon=True)
    reminder_thread.start()
    
    # Auto cleanup on startup
    cleanup_old_files()
    
    try:
        print("🔄 Starting infinity polling with auto-reconnect...")
        bot.infinity_polling(
            timeout=20,
            long_polling_timeout=20,
            skip_pending=True
        )
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("🔄 Bot will auto-restart...")