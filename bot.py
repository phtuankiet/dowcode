import discord
import json
import os
import asyncio
import aiofiles
from datetime import datetime
from discord.ext import commands, tasks
import gc
import threading
import time
import requests
import re
from discord.ui import Button, View, Modal, TextInput
from discord import app_commands
from urllib.parse import urlparse
import random
import string
import hashlib
import base64
import datetime
from bs4 import BeautifulSoup
from main.fb import *
from main import *

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

active_senders = {}

def clr():
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')

def extract_keys(html):
    soup = BeautifulSoup(html, 'html.parser')
    code_div = soup.find('div', class_='plaintext')
    if code_div:
        keys = [line.strip() for line in code_div.get_text().split('\n') if line.strip()]
        return keys
    return []

def decode_ascii_payload(payload_array):
    try:
        decoded_string = ''.join(chr(code) for code in payload_array)
        if not decoded_string.endswith('}'):
            open_braces = decoded_string.count('{')
            close_braces = decoded_string.count('}')
            if open_braces > close_braces:
                decoded_string += '}' * (open_braces - close_braces)
        return json.loads(decoded_string)
    except Exception as e:
        return f"Lỗi decode ASCII payload: {e}"

def checkkey():
    url = 'https://anotepad.com/notes/aey9nt33'
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print("Không thể lấy dữ liệu từ anotepad:", e)
        os.kill(os.getpid(), 9)
    md5_list = extract_keys(response.text)
    key = input("Nhập Key Để Tiếp Tục:\n").strip()
    hashed = hashlib.md5(key.encode()).hexdigest()
    if hashed in md5_list:
        print("Key Đúng")
    else:
        print("Key Saii. Thoát chương trình.")
        os.kill(os.getpid(), 9)

def load_config():
    if os.path.exists('config.json'):
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def save_config(config):
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

def create_initial_config():
    token = input("Nhập Token Bot Discord Của Bạn > ")
    owner_id = input("Nhập Owner ID > ")
    prefix = input("Nhập Prefix Cho Bot > ")
    config = {
        "tokenbot": token,
        "prefix": prefix,
        "ownerVIP": owner_id,
        "ownerID": [owner_id]
    }
    save_config(config)
    return config

checkkey()
config = load_config()
if config:
    choice = input("Bạn Có Muốn Sử Dụng Lại Token Và Owner ID Và Prefix Cũ Không (Y/N) > ").lower()
    if choice != 'y':
        config = create_initial_config()
else:
    config = create_initial_config()

bot = commands.Bot(command_prefix=config['prefix'], intents=intents)

if not os.path.exists('data'):
    os.makedirs('data')

@tasks.loop(minutes=5)
async def cleanup_memory():
    gc.collect()
    print(f"Memory cleanup completed at {datetime.datetime.now()}")

@tasks.loop(seconds=30)
async def heartbeat():
    try:
        await bot.change_presence(activity=discord.Game("Bot Active"))
    except:
        pass

def safe_thread_wrapper(func, *args):
    try:
        func(*args)
    except Exception as e:
        print(f"Thread error: {e}")
        folder_name = args[-1] if args else "unknown"
        folder_path = os.path.join("data", folder_name)
        if os.path.exists(folder_path):
            import shutil
            shutil.rmtree(folder_path)

def get_guid():
    section_length = int(time.time() * 1000)
    
    def replace_func(c):
        nonlocal section_length
        r = (section_length + random.randint(0, 15)) % 16
        section_length //= 16
        return hex(r if c == "x" else (r & 7) | 8)[2:]

    return "".join(replace_func(c) if c in "xy" else c for c in "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx")

def get_info_from_uid(cookie, uid):
    user_id, fb_dtsg, jazoest, clientRevision, a, req = get_uid_fbdtsg(cookie)
    if user_id and fb_dtsg:
        fb = facebook(cookie)
        if fb.user_id and fb.fb_dtsg:
            return fb.get_info(uid)
    return {"name": "User", "id": uid}

def get_uid_fbdtsg(ck):
    try:
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
            'Connection': 'keep-alive',
            'Cookie': ck,
            'Host': 'www.facebook.com',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (like Gecko) Chrome/122.0.0.0 Safari/537.36'
        }
        
        try:
            response = requests.get('https://www.facebook.com/', headers=headers, timeout=30)
            
            if response.status_code != 200:
                print(f"Status Code >> {response.status_code}")
                return None, None, None, None, None, None
                
            html_content = response.text
            
            user_id = None
            fb_dtsg = None
            jazoest = None
            
            script_tags = re.findall(r'<script id="__eqmc" type="application/json[^>]*>(.*?)</script>', html_content)
            for script in script_tags:
                try:
                    json_data = json.loads(script)
                    if 'u' in json_data:
                        user_param = re.search(r'__user=(\d+)', json_data['u'])
                        if user_param:
                            user_id = user_param.group(1)
                            break
                except:
                    continue
            
            fb_dtsg_match = re.search(r'"f":"([^"]+)"', html_content)
            if fb_dtsg_match:
                fb_dtsg = fb_dtsg_match.group(1)
            
            jazoest_match = re.search(r'jazoest=(\d+)', html_content)
            if jazoest_match:
                jazoest = jazoest_match.group(1)
            
            revision_match = re.search(r'"server_revision":(\d+),"client_revision":(\d+)', html_content)
            rev = revision_match.group(1) if revision_match else ""
            
            a_match = re.search(r'__a=(\d+)', html_content)
            a = a_match.group(1) if a_match else "1"
            
            req = "1b"
                
            return user_id, fb_dtsg, rev, req, a, jazoest
                
        except requests.exceptions.RequestException as e:
            print(f"Lỗi Kết Nối Khi Lấy UID/FB_DTSG: {e}")
            return get_uid_fbdtsg(ck)
            
    except Exception as e:
        print(f"Lỗi: {e}")
        return None, None, None, None, None, None

def comment_group_post(cookie, group_id, post_id, message, uidtag=None, nametag=None):
    try:
        user_id, fb_dtsg, jazoest, rev, a, req = get_uid_fbdtsg(cookie)
        
        if not all([user_id, fb_dtsg, jazoest]):
            return False
            
        pstid_enc = base64.b64encode(f"feedback:{post_id}".encode()).decode()
        
        client_mutation_id = str(round(random.random() * 19))
        session_id = get_guid()
        crt_time = int(time.time() * 1000)
        
        variables = {
            "feedLocation": "DEDICATED_COMMENTING_SURFACE",
            "feedbackSource": 110,
            "groupID": group_id,
            "input": {
                "client_mutation_id": client_mutation_id,
                "actor_id": user_id,
                "attachments": None,
                "feedback_id": pstid_enc,
                "formatting_style": None,
                "message": {
                    "ranges": [],
                    "text": message
                },
                "attribution_id_v2": f"SearchCometGlobalSearchDefaultTabRoot.react,comet.search_results.default_tab,tap_search_bar,{crt_time},775647,391724414624676,,",
                "vod_video_timestamp": None,
                "is_tracking_encrypted": True,
                "tracking": [],
                "feedback_source": "DEDICATED_COMMENTING_SURFACE",
                "session_id": session_id
            },
            "inviteShortLinkKey": None,
            "renderLocation": None,
            "scale": 3,
            "useDefaultActor": False,
            "focusCommentID": None,
            "__relay_internal__pv__IsWorkUserrelayprovider": False
        }
        
        if uidtag and nametag:
            name_position = message.find(nametag)
            if name_position != -1:
                variables["input"]["message"]["ranges"] = [
                    {
                        "entity": {
                            "id": uidtag
                        },
                        "length": len(nametag),
                        "offset": name_position
                    }
                ]
            
        payload = {
            'av': user_id,
            '__crn': 'comet.fbweb.CometGroupDiscussionRoute',
            'fb_dtsg': fb_dtsg,
            'jazoest': jazoest,
            'fb_api_caller_class': 'RelayModern',
            'fb_api_req_friendly_name': 'useCometUFICreateCommentMutation',
            'variables': json.dumps(variables),
            'server_timestamps': 'true',
            'doc_id': '10047708791980503'
        }
        
        headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'identity',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Cookie': cookie,
            'Origin': 'https://www.facebook.com',
            'Referer': f'https://www.facebook.com/groups/{group_id}',
            'User-Agent': 'python-http/0.27.0'
        }
        
        response = requests.post('https://www.facebook.com/api/graphql', data=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            return True
        else:
            return False
    except Exception as e:
        print(f"Lỗi khi gửi bình luận: {e}")
        return False

def restore_tasks():
    if not os.path.exists('data'):
        return
    for folder in os.listdir('data'):
        folder_path = f"data/{folder}"
        if os.path.isdir(folder_path) and os.path.exists(f"{folder_path}/luutru.txt"):
            try:
                with open(f"{folder_path}/luutru.txt", "r", encoding="utf-8") as f:
                    content = f.read().strip()
                parts = content.split(" | ")
                if len(parts) >= 4:
                    cookie = parts[0]
                    task_type = parts[3]
                    if task_type == "treo_media" and len(parts) >= 6:
                        idbox = parts[1]
                        delay = parts[2]
                        media_url = parts[5]
                        if os.path.exists(f"{folder_path}/messages.txt"):
                            with open(f"{folder_path}/messages.txt", "r", encoding="utf-8") as msg_f:
                                message = msg_f.read()
                            for file in os.listdir(folder_path):
                                if file not in ['luutru.txt', 'messages.txt']:
                                    local_file_path = os.path.join(folder_path, file)
                                    thread = threading.Thread(target=safe_thread_wrapper, args=(start_treo_media_func, cookie, idbox, local_file_path, message, delay, folder))
                                    thread.daemon = True
                                    thread.start()
                                    break
                    elif task_type == "treo_contact" and len(parts) >= 6:
                        idbox = parts[1]
                        delay = parts[2]
                        uid_contact = parts[5]
                        if os.path.exists(f"{folder_path}/messages.txt"):
                            with open(f"{folder_path}/messages.txt", "r", encoding="utf-8") as msg_f:
                                message = msg_f.read()
                            thread = threading.Thread(target=safe_thread_wrapper, args=(start_treo_contact_func, cookie, idbox, uid_contact, message, delay, folder))
                            thread.daemon = True
                            thread.start()
                    elif task_type == "treo_normal":
                        idbox = parts[1]
                        delay = parts[2]
                        if os.path.exists(f"{folder_path}/message.txt"):
                            with open(f"{folder_path}/message.txt", "r", encoding="utf-8") as msg_f:
                                message = msg_f.read()
                            thread = threading.Thread(target=safe_thread_wrapper, args=(start_treo_mess_func, cookie, idbox, message, delay, folder))
                            thread.daemon = True
                            thread.start()
                    elif task_type == "nhay_normal":
                        idbox = parts[1]
                        delay = parts[2]
                        thread = threading.Thread(target=safe_thread_wrapper, args=(start_nhay_func, cookie, idbox, delay, folder))
                        thread.daemon = True
                        thread.start()
                    elif task_type == "nhay_tag" and len(parts) >= 6:
                        idbox = parts[1]
                        delay = parts[2]
                        uid_tag = parts[5]
                        thread = threading.Thread(target=safe_thread_wrapper, args=(start_nhay_tag_func, cookie, idbox, uid_tag, delay, folder))
                        thread.daemon = True
                        thread.start()
                    elif task_type == "nhay_top_tag" and len(parts) >= 7:
                        group_id = parts[1]
                        post_id = parts[2]
                        uid_tag = parts[3]
                        delay = parts[4]
                        thread = threading.Thread(target=safe_thread_wrapper, args=(start_nhay_top_tag_func, cookie, group_id, post_id, uid_tag, delay, folder))
                        thread.daemon = True
                        thread.start()
                    elif task_type == "treoso":
                        idbox = parts[1]
                        delay = parts[2]
                        thread = threading.Thread(target=safe_thread_wrapper, args=(start_treoso_func, cookie, idbox, delay, folder))
                        thread.daemon = True
                        thread.start()
                    print(f"Đã Khôi Phục Task: {folder} - {task_type}")
            except Exception as e:
                print(f"Lỗi khi khôi phục task {folder}: {e}")

def start_treo_media_func(cookie, idbox, file_path, ngon, delay_str, folder_name):
    delay = float(delay_str)
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            fb = facebook(cookie)
            if fb.user_id and fb.fb_dtsg:
                sender = MessageSender(fbTools({
                    "FacebookID": fb.user_id,
                    "fb_dtsg": fb.fb_dtsg,
                    "clientRevision": fb.rev,
                    "jazoest": fb.jazoest,
                    "cookieFacebook": cookie
                }), {
                    "FacebookID": fb.user_id,
                    "fb_dtsg": fb.fb_dtsg,
                    "clientRevision": fb.rev,
                    "jazoest": fb.jazoest,
                    "cookieFacebook": cookie
                }, fb)
                
                active_senders[folder_name] = sender
                sender.get_last_seq_id()
                
                if not sender.connect_mqtt():
                    print("Failed to connect MQTT, retrying...")
                    retry_count += 1
                    time.sleep(10)
                    continue
                
                running = True
                while running:
                    try:
                        folder_path = os.path.join("data", folder_name)
                        if not os.path.exists(folder_path):
                            running = False
                            break
                        sender.send_message_with_attachment(ngon, idbox, file_path)
                        time.sleep(delay)
                    except Exception as e:
                        print(f"Error during sending message with media: {e}")
                        if "connection" in str(e).lower():
                            break
                        time.sleep(10)
                
                if folder_name in active_senders:
                    active_senders[folder_name].stop()
                    del active_senders[folder_name]
                break
                
        except Exception as e:
            print(f"Error initializing Facebook API: {e}")
            retry_count += 1
            time.sleep(10)

def start_treo_contact_func(cookie, idbox, contact_uid, ngon, delay_str, folder_name):
    delay = float(delay_str)
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            fb = facebook(cookie)
            if fb.user_id and fb.fb_dtsg:
                sender = MessageSender(fbTools({
                    "FacebookID": fb.user_id,
                    "fb_dtsg": fb.fb_dtsg,
                    "clientRevision": fb.rev,
                    "jazoest": fb.jazoest,
                    "cookieFacebook": cookie
                }), {
                    "FacebookID": fb.user_id,
                    "fb_dtsg": fb.fb_dtsg,
                    "clientRevision": fb.rev,
                    "jazoest": fb.jazoest,
                    "cookieFacebook": cookie
                }, fb)
                
                active_senders[folder_name] = sender
                sender.get_last_seq_id()
                
                if not sender.connect_mqtt():
                    print("Failed to connect MQTT, retrying...")
                    retry_count += 1
                    time.sleep(10)
                    continue
                
                running = True
                while running:
                    try:
                        folder_path = os.path.join("data", folder_name)
                        if not os.path.exists(folder_path):
                            running = False
                            break
                        sender.share_contact(ngon, contact_uid, idbox)
                        time.sleep(delay)
                    except Exception as e:
                        print(f"Error during sharing contact: {e}")
                        if "connection" in str(e).lower():
                            break
                        time.sleep(10)
                
                if folder_name in active_senders:
                    active_senders[folder_name].stop()
                    del active_senders[folder_name]
                break
                
        except Exception as e:
            print(f"Error initializing Facebook API: {e}")
            retry_count += 1
            time.sleep(10)

def start_treo_mess_func(cookie, idbox, ngon, delay_str, folder_name):
    delay = float(delay_str)
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            fb = facebook(cookie)
            if fb.user_id and fb.fb_dtsg:
                sender = MessageSender(fbTools({
                    "FacebookID": fb.user_id,
                    "fb_dtsg": fb.fb_dtsg,
                    "clientRevision": fb.rev,
                    "jazoest": fb.jazoest,
                    "cookieFacebook": cookie
                }), {
                    "FacebookID": fb.user_id,
                    "fb_dtsg": fb.fb_dtsg,
                    "clientRevision": fb.rev,
                    "jazoest": fb.jazoest,
                    "cookieFacebook": cookie
                }, fb)
                
                active_senders[folder_name] = sender
                sender.get_last_seq_id()
                
                if not sender.connect_mqtt():
                    print("Failed to connect MQTT, retrying...")
                    retry_count += 1
                    time.sleep(10)
                    continue
                    
                running = True
                while running:
                    try:
                        folder_path = os.path.join("data", folder_name)
                        if not os.path.exists(folder_path):
                            running = False
                            break
                        sender.send_message(ngon, idbox)
                        time.sleep(delay)
                    except Exception as e:
                        print(f"Error during sending message: {e}")
                        if "connection" in str(e).lower():
                            break
                        time.sleep(10)
                
                if folder_name in active_senders:
                    active_senders[folder_name].stop()
                    del active_senders[folder_name]
                break
                
        except Exception as e:
            print(f"Error initializing Facebook API: {e}")
            retry_count += 1
            time.sleep(10)

def start_nhay_func(cookie, idbox, delay_str, folder_name):
    delay = float(delay_str)
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            fb = facebook(cookie)
            if fb.user_id and fb.fb_dtsg:
                sender = MessageSender(fbTools({
                    "FacebookID": fb.user_id,
                    "fb_dtsg": fb.fb_dtsg,
                    "clientRevision": fb.rev,
                    "jazoest": fb.jazoest,
                    "cookieFacebook": cookie
                }), {
                    "FacebookID": fb.user_id,
                    "fb_dtsg": fb.fb_dtsg,
                    "clientRevision": fb.rev,
                    "jazoest": fb.jazoest,
                    "cookieFacebook": cookie
                }, fb)
                
                active_senders[folder_name] = sender
                sender.get_last_seq_id()
                
                if not sender.connect_mqtt():
                    print("Failed to connect MQTT, retrying...")
                    retry_count += 1
                    time.sleep(10)
                    continue
                
                running = True
                while running:
                    try:
                        folder_path = os.path.join("data", folder_name)
                        if not os.path.exists(folder_path):
                            running = False
                            break
                        current_dir = os.path.dirname(os.path.abspath(__file__))
                        nhay_path = os.path.join(current_dir, "nhay.txt")
                        with open(nhay_path, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                        for line in lines:
                            folder_path = os.path.join("data", folder_name)
                            if not os.path.exists(folder_path):
                                running = False
                                break
                            msg = line.strip()
                            if msg:
                                sender.send_typing_indicator(idbox)
                                sender.send_message(msg, idbox)
                                time.sleep(delay)
                    except Exception as e:
                        print(f"Error During Nhây Message: {e}")
                        if "connection" in str(e).lower():
                            break
                        time.sleep(10)
                
                if folder_name in active_senders:
                    active_senders[folder_name].stop()
                    del active_senders[folder_name]
                break
                
        except Exception as e:
            print(f"Error Initializing Facebook API: {e}")
            retry_count += 1
            time.sleep(10)

def start_nhay_tag_func(cookie, idbox, uid_tag, delay_str, folder_name):
    delay = float(delay_str)
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            fb = facebook(cookie)
            if fb.user_id and fb.fb_dtsg:
                uid = uid_tag
                user_info = fb.get_info(uid)
                ten = user_info.get("name", "User")
                facebook_data = {
                    "FacebookID": fb.user_id,
                    "fb_dtsg": fb.fb_dtsg,
                    "clientRevision": fb.rev,
                    "jazoest": fb.jazoest,
                    "cookieFacebook": cookie
                }
                sender = MessageSender(fbTools(facebook_data), facebook_data, fb)
                
                active_senders[folder_name] = sender
                sender.get_last_seq_id()
                
                if not sender.connect_mqtt():
                    print("Failed to connect MQTT, retrying...")
                    retry_count += 1
                    time.sleep(10)
                    continue
                
                running = True
                while running:
                    try:
                        folder_path = os.path.join("data", folder_name)
                        if not os.path.exists(folder_path):
                            running = False
                            break
                        current_dir = os.path.dirname(os.path.abspath(__file__))
                        nhay_path = os.path.join(current_dir, "nhay.txt")
                        with open(nhay_path, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                        for line in lines:
                            folder_path = os.path.join("data", folder_name)
                            if not os.path.exists(folder_path):
                                running = False
                                break
                            msg = line.strip()
                            if msg:
                                msg_with_tag = random.choice([f"{ten} {msg}", f"{msg} {ten}"])
                                mention = {"id": uid, "tag": ten}
                                sender.send_typing_indicator(idbox)
                                sender.send_message(text=msg_with_tag, mention=mention, thread_id=idbox)
                                time.sleep(delay)
                    except Exception as e:
                        print(f"Error During Nhây Tag Message: {e}")
                        if "connection" in str(e).lower():
                            break
                        time.sleep(10)
                
                if folder_name in active_senders:
                    active_senders[folder_name].stop()
                    del active_senders[folder_name]
                break
                
        except Exception as e:
            print(f"Error Initializing Facebook API: {e}")
            retry_count += 1
            time.sleep(10)

def start_nhay_top_tag_func(cookie, group_id, post_id, uid_tag, delay_str, folder_name):
    delay = float(delay_str)
    folder_path = os.path.join("data", folder_name)
    user_info = get_info_from_uid(cookie, uid_tag)
    ten_tag = user_info.get("name", "User")
    running = True
    
    while running:
        if not os.path.exists(folder_path):
            break
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            nhay_path = os.path.join(current_dir, "nhay.txt")
            with open(nhay_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for line in lines:
                if not os.path.exists(folder_path):
                    running = False
                    break
                msg = line.strip()
                if msg:
                    msg_with_tag = random.choice([f"{ten_tag} {msg}", f"{msg} {ten_tag}"])
                    comment_group_post(cookie, group_id, post_id, msg_with_tag, uid_tag, ten_tag)
                    time.sleep(delay)
        except Exception as e:
            print(f"Error in start_nhay_top_tag_func: {e}")
            time.sleep(10)

def start_treoso_func(cookie, idbox, delay_str, folder_name):
    delay = float(delay_str)
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            fb = facebook(cookie)
            if fb.user_id and fb.fb_dtsg:
                sender = MessageSender(fbTools({
                    "FacebookID": fb.user_id,
                    "fb_dtsg": fb.fb_dtsg,
                    "clientRevision": fb.rev,
                    "jazoest": fb.jazoest,
                    "cookieFacebook": cookie
                }), {
                    "FacebookID": fb.user_id,
                    "fb_dtsg": fb.fb_dtsg,
                    "clientRevision": fb.rev,
                    "jazoest": fb.jazoest,
                    "cookieFacebook": cookie
                }, fb)
                
                active_senders[folder_name] = sender
                sender.get_last_seq_id()
                
                if not sender.connect_mqtt():
                    print("Failed to connect MQTT, retrying...")
                    retry_count += 1
                    time.sleep(10)
                    continue
                
                running = True
                while running:
                    try:
                        folder_path = os.path.join("data", folder_name)
                        if not os.path.exists(folder_path):
                            running = False
                            break
                        current_dir = os.path.dirname(os.path.abspath(__file__))
                        nhay_path = os.path.join(current_dir, "so.txt")
                        with open(nhay_path, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                        for line in lines:
                            folder_path = os.path.join("data", folder_name)
                            if not os.path.exists(folder_path):
                                running = False
                                break
                            msg = line.strip()
                            if msg:
                                sender.send_typing_indicator(idbox)
                                sender.send_message(msg, idbox)
                                time.sleep(delay)
                    except Exception as e:
                        print(f"Error During Nhây Message: {e}")
                        if "connection" in str(e).lower():
                            break
                        time.sleep(10)
                
                if folder_name in active_senders:
                    active_senders[folder_name].stop()
                    del active_senders[folder_name]
                break
                
        except Exception as e:
            print(f"Error Initializing Facebook API: {e}")
            retry_count += 1
            time.sleep(10)

@bot.event
async def on_ready():
    print(f'{bot.user} Đã Online!')
    cleanup_memory.start()
    heartbeat.start()
    restore_tasks()

@bot.event
async def on_disconnect():
    print("Bot disconnected, attempting to reconnect...")

@bot.event
async def on_resumed():
    print("Bot connection resumed")

def check_owner():
    def predicate(ctx):
        return str(ctx.author.id) in config['ownerID']
    return commands.check(predicate)

def check_ownervip():
    def predicate(ctx):
        return str(ctx.author.id) in config['ownerVIP']
    return commands.check(predicate)

@bot.command()
@check_ownervip()
async def add(ctx, member: discord.Member = None):
    if member is None and len(ctx.message.content.split()) > 1:
        try:
            user_id = ctx.message.content.split()[1]
            if user_id.startswith('<@') and user_id.endswith('>'):
                user_id = user_id[2:-1].replace('!', '')
            config['ownerID'].append(user_id)
            save_config(config)
            await ctx.send(f"Đã Thêm <@{user_id}> Vào Danh Sách Owner!")
        except:
            await ctx.send("Lỗi Khi Thêm User!")
    elif member:
        config['ownerID'].append(str(member.id))
        save_config(config)
        await ctx.send(f"Đã Thêm {member.mention} Vào Danh Sách Owner!")

@bot.command()
@check_ownervip()
async def remove(ctx, member: discord.Member = None):
    if member is None and len(ctx.message.content.split()) > 1:
        try:
            user_id = ctx.message.content.split()[1]
            if user_id.startswith('<@') and user_id.endswith('>'):
                user_id = user_id[2:-1].replace('!', '')
            if user_id in config['ownerID']:
                config['ownerID'].remove(user_id)
                save_config(config)
                embed = discord.Embed(
                    title=f"✅ Xóa Thành Công <@{user_id}> Khỏi Danh Sách Owner ✅",
                    color=0x00FF00
                )
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    description=f"❌ <@{user_id}> Không Nằm Trong Danh Sách Owner ❌",
                    color=0xFF0000
                )
                await ctx.send(embed=embed)
        except:
            await ctx.send("Lỗi Khi Xóa User!")
    elif member:
        user_id = str(member.id)
        if user_id in config['ownerID']:
            config['ownerID'].remove(user_id)
            save_config(config)
            embed = discord.Embed(
                title=f"✅ Xóa Thành Công {member.mention} Khỏi Danh Sách Owner ✅",
                color=0x00FF00
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                description=f"❌ {member.mention} Không Nằm Trong Danh Sách Owner ❌",
                color=0xFF0000
            )
            await ctx.send(embed=embed)

class TreoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Treo Ảnh/Video", style=discord.ButtonStyle.primary)
    async def treo_media(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = TreoMediaModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Treo Share Contact", style=discord.ButtonStyle.secondary)
    async def treo_contact(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = TreoContactModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Treo Normal", style=discord.ButtonStyle.success)
    async def treo_normal(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = TreoNormalModal()
        await interaction.response.send_modal(modal)

class TreoMediaModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Treo Ảnh/Video", timeout=None)
        self.cookies = discord.ui.TextInput(
            label="Nhập Cookies",
            style=discord.TextStyle.paragraph,
            required=True
        )
        self.add_item(self.cookies)
        self.idbox = discord.ui.TextInput(
            label="Nhập ID Box",
            required=True
        )
        self.add_item(self.idbox)
        self.media_url = discord.ui.TextInput(
            label="Nhập Link Tải Ảnh/Video",
            required=True
        )
        self.add_item(self.media_url)
        self.message = discord.ui.TextInput(
            label="Nhập Ngôn",
            style=discord.TextStyle.paragraph,
            required=True
        )
        self.add_item(self.message)
        self.delay = discord.ui.TextInput(
            label="Nhập Delay",
            required=True
        )
        self.add_item(self.delay)

    def download_media(self, url, folder_path):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0'
            }
            response = requests.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            if "Content-Disposition" in response.headers:
                content_disposition = response.headers["Content-Disposition"]
                filename = re.findall("filename=(.+)", content_disposition)[0].strip('"')
            else:
                filename = os.path.basename(urlparse(url).path)
                if not filename:
                    content_type = response.headers.get('Content-Type', '').split('/')[1]
                    if content_type:
                        filename = f"media_{int(time.time())}.{content_type}"
                    else:
                        filename = f"media_{int(time.time())}"
            local_file_path = os.path.join(folder_path, filename)
            with open(local_file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return local_file_path
        except Exception as e:
            print(f"Error downloading media: {e}")
            return None

    async def on_submit(self, interaction: discord.Interaction):
        try:
            folder_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
            folder_path = f"data/{folder_id}"
            os.makedirs(folder_path)
            with open(f"{folder_path}/luutru.txt", "w", encoding="utf-8") as f:
                f.write(f"{self.cookies.value} | {self.idbox.value} | {self.delay.value} | treo_media | {interaction.user.id} | {self.media_url.value}")
            with open(f"{folder_path}/messages.txt", "w", encoding="utf-8") as f:
                f.write(self.message.value)
            local_file_path = self.download_media(self.media_url.value, folder_path)
            if not local_file_path:
                embed = discord.Embed(
                    title="❌ Lỗi Khi Tải Ảnh/Video",
                    description="Không Thể Tải File Từ Url Đã Cung Cấp",
                    color=0xFF0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            thread = threading.Thread(target=safe_thread_wrapper, args=(start_treo_media_func, self.cookies.value, self.idbox.value, local_file_path, self.message.value, self.delay.value, folder_id))
            thread.daemon = True
            thread.start()
            embed = discord.Embed(
                title="✅ Tạo Tasks Thành Công ✅",
                description=f"ID Tasks: {folder_id}",
                color=0x00FF00
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Lỗi Tạo Tasks ❌",
                description=f"Lỗi: {str(e)}",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

class TreoContactModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Treo Share Contact", timeout=None)
        self.cookies = discord.ui.TextInput(
            label="Nhập Cookies",
            style=discord.TextStyle.paragraph,
            required=True
        )
        self.add_item(self.cookies)
        self.idbox = discord.ui.TextInput(
            label="Nhập ID Box",
            required=True
        )
        self.add_item(self.idbox)
        self.delay = discord.ui.TextInput(
            label="Nhập Delay",
            required=True
        )
        self.add_item(self.delay)
        self.uid_contact = discord.ui.TextInput(
            label="Nhập UID Contact",
            required=True
        )
        self.add_item(self.uid_contact)
        self.message = discord.ui.TextInput(
            label="Nhập Ngôn",
            style=discord.TextStyle.paragraph,
            required=True
        )
        self.add_item(self.message)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            folder_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
            folder_path = f"data/{folder_id}"
            os.makedirs(folder_path)
            with open(f"{folder_path}/luutru.txt", "w", encoding="utf-8") as f:
                f.write(f"{self.cookies.value} | {self.idbox.value} | {self.delay.value} | treo_contact | {interaction.user.id} | {self.uid_contact.value}")
            with open(f"{folder_path}/messages.txt", "w", encoding="utf-8") as f:
                f.write(self.message.value)
            thread = threading.Thread(target=safe_thread_wrapper, args=(start_treo_contact_func, self.cookies.value, self.idbox.value, self.uid_contact.value, self.message.value, self.delay.value, folder_id))
            thread.daemon = True
            thread.start()
            embed = discord.Embed(
                title="✅ Tạo Tasks Thành Công ✅",
                description=f"ID Tasks: {folder_id}",
                color=0x00FF00
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Lỗi Tạo Tasks ❌",
                description=f"Lỗi: {str(e)}",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

class TreoNormalModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Treo Normal", timeout=None)
        self.cookies = discord.ui.TextInput(
            label="Nhập Cookies",
            style=discord.TextStyle.paragraph,
            required=True
        )
        self.add_item(self.cookies)
        self.idbox = discord.ui.TextInput(
            label="Nhập ID Box",
            required=True
        )
        self.add_item(self.idbox)
        self.delay = discord.ui.TextInput(
            label="Nhập Delay",
            required=True
        )
        self.add_item(self.delay)
        self.message = discord.ui.TextInput(
            label="Nhập Ngôn",
            style=discord.TextStyle.paragraph,
            required=True
        )
        self.add_item(self.message)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            folder_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
            folder_path = f"data/{folder_id}"
            os.makedirs(folder_path)
            with open(f"{folder_path}/luutru.txt", "w", encoding="utf-8") as f:
                f.write(f"{self.cookies.value} | {self.idbox.value} | {self.delay.value} | treo_normal | {interaction.user.id}")
            with open(f"{folder_path}/message.txt", "w", encoding="utf-8") as f:
                f.write(self.message.value)
            thread = threading.Thread(target=safe_thread_wrapper, args=(start_treo_mess_func, self.cookies.value, self.idbox.value, self.message.value, self.delay.value, folder_id))
            thread.daemon = True
            thread.start()
            embed = discord.Embed(
                title="✅ Tạo Tasks Thành Công ✅",
                description=f"ID Tasks: {folder_id}",
                color=0x00FF00
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Lỗi Tạo Tasks ❌",
                description=f"Lỗi: {str(e)}",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.command()
@check_owner()
async def treo(ctx):
    embed = discord.Embed(
        title="Chọn Chức Năng Treo Bên Dưới",
        description="Button Treo Ảnh/Video Là Treo Gửi Ảnh Hoặc Video\nButton Treo Share Contact Là Treo + Share Contact Của UID\nButton Treo Normal Là Button Gửi Tin Nhắn Kiểu Bình Thường",
        color=0xFFC0CB
    )
    view = TreoView()
    await ctx.send(embed=embed, view=view)

class NhayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Nhây", style=discord.ButtonStyle.primary)
    async def nhay_normal(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = NhayModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Nhây Tag", style=discord.ButtonStyle.secondary)
    async def nhay_tag(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = NhayTagModal()
        await interaction.response.send_modal(modal)

class NhayModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Nhây Thường", timeout=None)
        self.cookies = discord.ui.TextInput(
            label="Nhập Cookies",
            style=discord.TextStyle.paragraph,
            required=True
        )
        self.add_item(self.cookies)
        self.idbox = discord.ui.TextInput(
            label="Nhập ID Box",
            required=True
        )
        self.add_item(self.idbox)
        self.delay = discord.ui.TextInput(
            label="Nhập Delay",
            required=True
        )
        self.add_item(self.delay)

    async def on_submit(self, interaction: discord.Interaction):
        folder_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
        folder_path = f"data/{folder_id}"
        os.makedirs(folder_path)
        with open(f"{folder_path}/luutru.txt", "w", encoding="utf-8") as f:
            f.write(f"{self.cookies.value} | {self.idbox.value} | {self.delay.value} | nhay_normal | {interaction.user.id}")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        nhay_path = os.path.join(current_dir, "nhay.txt")
        if not os.path.exists(nhay_path):
            with open(nhay_path, "w", encoding="utf-8") as f:
                f.write("cay ak\ncn choa\nsua em\nsua de\nmanh em\ncay ak\ncn nqu")
        thread = threading.Thread(target=safe_thread_wrapper, args=(start_nhay_func, self.cookies.value, self.idbox.value, self.delay.value, folder_id))
        thread.daemon = True
        thread.start()
        embed = discord.Embed(
            title="✅ Tạo Tasks Thành Công ✅",
            description=f"ID Tasks: {folder_id}",
            color=0x00FF00
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class NhayTagModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Nhây Tag", timeout=None)
        self.cookies = discord.ui.TextInput(
            label="Nhập Cookies",
            style=discord.TextStyle.paragraph,
            required=True
        )
        self.add_item(self.cookies)
        self.idbox = discord.ui.TextInput(
            label="Nhập ID Box",
            required=True
        )
        self.add_item(self.idbox)
        self.delay = discord.ui.TextInput(
            label="Nhập Delay",
            required=True
        )
        self.add_item(self.delay)
        self.uid_tag = discord.ui.TextInput(
            label="Nhập UID Cần Tag",
            required=True
        )
        self.add_item(self.uid_tag)

    async def on_submit(self, interaction: discord.Interaction):
        folder_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
        folder_path = f"data/{folder_id}"
        os.makedirs(folder_path)
        with open(f"{folder_path}/luutru.txt", "w", encoding="utf-8") as f:
            f.write(f"{self.cookies.value} | {self.idbox.value} | {self.delay.value} | nhay_tag | {interaction.user.id} | {self.uid_tag.value}")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        nhay_path = os.path.join(current_dir, "nhay.txt")
        if not os.path.exists(nhay_path):
            with open(nhay_path, "w", encoding="utf-8") as f:
                f.write("cay ak\ncn choa\nsua em\nsua de\nmanh em\ncay ak\ncn nqu")
        thread = threading.Thread(target=safe_thread_wrapper, args=(start_nhay_tag_func, self.cookies.value, self.idbox.value, self.uid_tag.value, self.delay.value, folder_id))
        thread.daemon = True
        thread.start()
        embed = discord.Embed(
            title="✅ Tạo Tasks Thành Công ✅",
            description=f"ID Tasks: {folder_id}",
            color=0x00FF00
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.command()
@check_owner()
async def nhay(ctx):
    embed = discord.Embed(
        title="Bạn Muốn Sử Dụng Phương Thức Nhây Nào?",
        description="Button Nhây Sẽ Là Nhây Thường - Fake Typing\nButton Nhây Tag Sẽ Là Nhây Có Tag - Fake Typing",
        color=0x0099FF
    )
    view = NhayView()
    await ctx.send(embed=embed, view=view)

class NhayTopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Start", style=discord.ButtonStyle.primary)
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = NhayTopModal()
        await interaction.response.send_modal(modal)

class NhayTopModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Nhây Top Tag", timeout=None)
        self.cookies = discord.ui.TextInput(
            label="Nhập Cookies:",
            style=discord.TextStyle.paragraph,
            required=True
        )
        self.add_item(self.cookies)
        self.id_group = discord.ui.TextInput(
            label="Nhập ID Group:",
            required=True
        )
        self.add_item(self.id_group)
        self.id_post = discord.ui.TextInput(
            label="Nhập ID Post:",
            required=True
        )
        self.add_item(self.id_post)
        self.uid_tag = discord.ui.TextInput(
            label="Nhập UID Cần Tag:",
            required=True
        )
        self.add_item(self.uid_tag)
        self.delay = discord.ui.TextInput(
            label="Nhập Delay:",
            required=True
        )
        self.add_item(self.delay)

    async def on_submit(self, interaction: discord.Interaction):
        folder_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
        folder_path = f"data/{folder_id}"
        os.makedirs(folder_path)
        with open(f"{folder_path}/luutru.txt", "w", encoding="utf-8") as f:
            f.write(f"{self.cookies.value} | {self.id_group.value} | {self.id_post.value} | {self.uid_tag.value} | {self.delay.value} | nhay_top_tag | {interaction.user.id}")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        nhay_path = os.path.join(current_dir, "nhay.txt")
        if not os.path.exists(nhay_path):
            with open(nhay_path, "w", encoding="utf-8") as f:
                f.write("cay ak\ncn choa\nsua em\nsua de\nmanh em\ncay ak\ncn nqu")
        thread = threading.Thread(target=safe_thread_wrapper, args=(start_nhay_top_tag_func, self.cookies.value, self.id_group.value, self.id_post.value, self.uid_tag.value, self.delay.value, folder_id))
        thread.daemon = True
        thread.start()
        embed = discord.Embed(
            title="✅ Tạo Tasks Thành Công ✅",
            description=f"ID Tasks: {folder_id}",
            color=0x00FF00
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.command()
@check_owner()
async def nhaytop(ctx):
    embed = discord.Embed(
        title="Vui Lòng Ấn Vào Nút Start Để Nhập Thông Tin",
        color=0xFFC0CB
    )
    view = NhayTopView()
    await ctx.send(embed=embed, view=view)

@bot.command()
@check_owner()
async def danhsachtask(ctx):
    user_id = str(ctx.author.id)
    is_vip = user_id == config['ownerVIP']
    tasks = []
    if os.path.exists('data'):
        for folder in os.listdir('data'):
            folder_path = f"data/{folder}"
            if os.path.isdir(folder_path) and os.path.exists(f"{folder_path}/luutru.txt"):
                with open(f"{folder_path}/luutru.txt", "r", encoding="utf-8") as f:
                    content = f.read().strip()
                parts = content.split(" | ")
                if len(parts) >= 4:
                    task_owner = "Unknown"
                    if parts[3] == "nhay_top_tag" and len(parts) >= 7:
                        task_owner = parts[6]
                    elif parts[3] == "treoso" and len(parts) >= 5:
                        task_owner = parts[4]
                    elif len(parts) >= 5:
                        task_owner = parts[4]
                    
                    if is_vip or task_owner == user_id:
                        created_timestamp = os.path.getctime(folder_path)
                        created_time = datetime.datetime.fromtimestamp(created_timestamp).strftime("%d-%m-%Y")
                        method_map = {
                            "treo_media": "Treo Ảnh/Video",
                            "treo_contact": "Treo Share Contact",
                            "treo_normal": "Treo Normal",
                            "nhay_normal": "Nhây Thường",
                            "nhay_tag": "Nhây Tag",
                            "nhay_top_tag": "Nhây Top Tag",
                            "treoso": "Treo Sớ"
                        }
                        method = method_map.get(parts[3], parts[3])
                        if parts[3] == "nhay_top_tag" and len(parts) >= 7:
                            task_info = f"ID Task: {folder} | ID Group: {parts[1]} | ID Post: {parts[2]} | Tạo Lúc: {created_time} | Lệnh Đã Tạo: {config['prefix']}nhaytop"
                            if is_vip:
                                task_info += f" | Lệnh Được Tạo Bởi: <@{task_owner}>"
                        elif parts[3] == "treoso":
                            task_info = f"ID Tasks: {folder} | ID Box: {parts[1]} | Tạo Lúc: {created_time} | Lệnh Đã Tạo: {config['prefix']}treoso"
                            if is_vip:
                                task_info += f" | Lệnh Được Tạo Bởi: <@{task_owner}>"
                        elif parts[3] in ["nhay_normal", "nhay_tag"]:
                            task_info = f"ID Tasks: {folder} | ID Box: {parts[1]} | Tạo Lúc: {created_time} | Lệnh Đã Tạo: {config['prefix']}nhay | Phương Thức: {method}"
                            if is_vip:
                                task_info += f" | Lệnh Được Tạo Bởi: <@{task_owner}>"
                        else:
                            task_info = f"ID Tasks: {folder} | ID Box: {parts[1]} | Tạo Lúc: {created_time} | Lệnh Đã Tạo: {config['prefix']}treo | Phương Thức: {method}"
                            if is_vip:
                                task_info += f" | Lệnh Được Tạo Bởi: <@{task_owner}>"
                        tasks.append(task_info)
    
    if not tasks:
        embed = discord.Embed(
            title="Bạn Chưa Có Tạo Tasks Nào Hiện Tại Cả ❌",
            color=0xFF0000
        )
        await ctx.send(embed=embed)
        return

    tasks_per_page = 10
    total_pages = (len(tasks) + tasks_per_page - 1) // tasks_per_page
    current_page = 1

    def create_embed(page):
        start_idx = (page - 1) * tasks_per_page
        end_idx = start_idx + tasks_per_page
        page_tasks = tasks[start_idx:end_idx]
        description = "\n".join(page_tasks) + "\n\nBot By: DKhanh"
        embed = discord.Embed(
            title="🌟 Danh Sách Tasks 🌟",
            description=description,
            color=0x0099FF
        )
        embed.set_footer(text=f"Đang Ở Trang {page}/{total_pages}")
        return embed

    embed = create_embed(current_page)
    if total_pages == 1:
        await ctx.send(embed=embed)
        return

    view = discord.ui.View(timeout=None)

    async def prev_callback(interaction):
        nonlocal current_page
        if current_page > 1:
            current_page -= 1
            embed = create_embed(current_page)
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.response.defer()

    async def next_callback(interaction):
        nonlocal current_page
        if current_page < total_pages:
            current_page += 1
            embed = create_embed(current_page)
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.response.defer()

    prev_button = discord.ui.Button(emoji="◀️", style=discord.ButtonStyle.primary)
    next_button = discord.ui.Button(emoji="▶️", style=discord.ButtonStyle.primary)
    prev_button.callback = prev_callback
    next_button.callback = next_callback
    view.add_item(prev_button)
    view.add_item(next_button)

    message = await ctx.send(embed=embed, view=view)

    async def on_timeout():
        for item in view.children:
            item.disabled = True
        try:
            await message.edit(view=view)
        except:
            pass

    view.on_timeout = on_timeout

@bot.command()
@check_owner()
async def stoptask(ctx, task_id: str = None):
    if not task_id:
        await ctx.send("Vui Lòng Nhập ID Tasks !")
        return
    user_id = str(ctx.author.id)
    is_vip = user_id == config['ownerVIP']
    folder_path = f"data/{task_id}"
    if not os.path.exists(folder_path):
        embed = discord.Embed(
            title="❌ ID Tasks Này Không Tồn Tại Hoặc Không Thuộc Quyền Sỡ Hữu Của Bạn ❌",
            color=0xFF0000
        )
        await ctx.send(embed=embed)
        return
    if os.path.exists(f"{folder_path}/luutru.txt"):
        with open(f"{folder_path}/luutru.txt", "r", encoding="utf-8") as f:
            content = f.read().strip()
        parts = content.split(" | ")
        task_owner = "Unknown"
        if parts[3] == "nhay_top_tag" and len(parts) >= 7:
            task_owner = parts[6]
        elif parts[3] == "treoso" and len(parts) >= 5:
            task_owner = parts[4]
        elif len(parts) >= 5:
            task_owner = parts[4]
        
        if not is_vip and task_owner != user_id:
            embed = discord.Embed(
                title="❌ ID Tasks Này Không Tồn Tại Hoặc Không Thuộc Quyền Sỡ Hữu Của Bạn ❌",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return
    
    if task_id in active_senders:
        active_senders[task_id].stop()
        del active_senders[task_id]
    
    import shutil
    shutil.rmtree(folder_path)
    embed = discord.Embed(
        title=f"✅ Xóa Thành Công Tasks > {task_id} ✅",
        color=0x00FF00
    )
    await ctx.send(embed=embed)

class TreoSoModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Treo Sớ", timeout=None)
        self.cookies = discord.ui.TextInput(
            label="Nhập Cookies",
            style=discord.TextStyle.paragraph,
            required=True
        )
        self.add_item(self.cookies)
        self.idbox = discord.ui.TextInput(
            label="Nhập ID Box",
            required=True
        )
        self.add_item(self.idbox)
        self.delay = discord.ui.TextInput(
            label="Nhập Delay",
            required=True
        )
        self.add_item(self.delay)

    async def on_submit(self, interaction: discord.Interaction):
        folder_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
        folder_path = f"data/{folder_id}"
        os.makedirs(folder_path, exist_ok=True)
        with open(f"{folder_path}/luutru.txt", "w", encoding="utf-8") as f:
            f.write(f"{self.cookies.value} | {self.idbox.value} | {self.delay.value} | treoso | {interaction.user.id}")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        nhay_path = os.path.join(current_dir, "so.txt")
        if not os.path.exists(nhay_path):
            with open(nhay_path, "w", encoding="utf-8") as f:
                f.write("cay ak\ncn choa\nsua em\nsua de\nmanh em\ncay ak\ncn nqu")
        thread = threading.Thread(target=safe_thread_wrapper, args=(start_treoso_func, self.cookies.value, self.idbox.value, self.delay.value, folder_id))
        thread.daemon = True
        thread.start()
        embed = discord.Embed(
            title="✅ Tạo Tasks Thành Công ✅",
            description=f"ID Tasks: {folder_id}",
            color=0x00FF00
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class TreoSoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Start", style=discord.ButtonStyle.primary, emoji="🚀")
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = TreoSoModal()
        await interaction.response.send_modal(modal)

@bot.command()
@check_owner()
async def listbox(ctx):
    embed = discord.Embed(
        title="📋 Lấy Danh Sách Box Facebook",
        description="Ấn Vào Nút **Start** Để Nhập Cookies",
        color=0xFF69B4,
        timestamp=datetime.datetime.utcnow()
    )
    embed.add_field(
        name="📌 Hướng Dẫn",
        value="• Nhập Cookies Facebook\n• Bot Sẽ Tự Động Lấy Tất Cả Box Có Trong Cookies\n• Kết Quả Sẽ Được Hiển Thị Theo Trang",
        inline=False
    )
    embed.set_footer(text="Developed By Pham Tuan Kiet", icon_url=bot.user.avatar.url if bot.user.avatar else None)
    
    view = ListBoxView()
    await ctx.send(embed=embed, view=view)

class ListBoxModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="🍪 Nhập Cookies Facebook", timeout=None)
        self.cookies = discord.ui.TextInput(
            label="Cookies Facebook",
            placeholder="Nhập Cookies Facebook Của Bạn...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=4000
        )
        self.add_item(self.cookies)

    async def on_submit(self, interaction: discord.Interaction):
        loading_embed = discord.Embed(
            title="⏰ Đang Xử Lý...",
            description="Bot Đang Lấy List Box, Vui Lòng Đợi...",
            color=0xFFD700
        )
        await interaction.response.send_message(embed=loading_embed, ephemeral=True)
        
        try:
            fb = facebook(self.cookies.value)
            fbt = fbTools(fb.data)
            
            success = fbt.getAllThreadList()
            if success:
                thread_data = fbt.getListThreadID()
                if "threadIDList" in thread_data and "threadNameList" in thread_data:
                    thread_ids = thread_data["threadIDList"]
                    thread_names = thread_data["threadNameList"]
                    
                    if len(thread_ids) > 10:
                        pages = []
                        for i in range(0, len(thread_ids), 10):
                            page_data = []
                            for j in range(i, min(i + 10, len(thread_ids))):
                                page_data.append({
                                    "index": j + 1,
                                    "name": thread_names[j],
                                    "id": thread_ids[j]
                                })
                            pages.append(page_data)
                        
                        view = PaginationView(pages, len(thread_ids))
                        initial_embed = view.create_embed()
                        await interaction.followup.send(embed=initial_embed, view=view, ephemeral=False)
                    else:
                        embed = discord.Embed(
                            title="📋 Danh Sách Box Facebook",
                            color=0x00FF00,
                            timestamp=datetime.datetime.utcnow()
                        )
                        
                        description = ""
                        for i in range(len(thread_ids)):
                            description += f"**{i+1}.** {thread_names[i]}\n`{thread_ids[i]}`\n\n"
                        
                        embed.description = description
                        embed.set_footer(text=f"Tổng Cộng: {len(thread_ids)} Box")
                        
                        await interaction.followup.send(embed=embed, ephemeral=False)
                else:
                    error_embed = discord.Embed(
                        title="❌ Lỗi",
                        description="Không Thể Lấy List Box Từ Data",
                        color=0xFF0000
                    )
                    await interaction.followup.send(embed=error_embed, ephemeral=False)
            else:
                error_embed = discord.Embed(
                    title="❌ Lỗi Cookies",
                    description="Không Thể Lấy Danh Sách Nhóm, Vui Lòng Check Lại Cookies.",
                    color=0xFF0000
                )
                await interaction.followup.send(embed=error_embed, ephemeral=False)
        except Exception as e:
            error_embed = discord.Embed(
                title="⚠️ Đã Xảy Ra Lỗi",
                description=f"{e}",
                color=0xFF0000
            )
            await interaction.followup.send(embed=error_embed, ephemeral=False)

class ListBoxView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Start", style=discord.ButtonStyle.primary, emoji="🚀")
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ListBoxModal()
        await interaction.response.send_modal(modal)

class PaginationView(discord.ui.View):
    def __init__(self, pages, total_items):
        super().__init__(timeout=300)
        self.pages = pages
        self.current_page = 0
        self.total_items = total_items

    def create_embed(self):
        embed = discord.Embed(
            title="📋 Danh Sách Box Facebook",
            color=0x00FF00,
            timestamp=datetime.datetime.utcnow()
        )
        
        current_page_data = self.pages[self.current_page]
        description = ""
        
        for item in current_page_data:
            description += f"**{item['index']}.** {item['name']}\n`{item['id']}`\n\n"
        
        embed.description = description
        
        embed.set_footer(
            text=f"Trang {self.current_page + 1}/{len(self.pages)} • Tổng Cộng: {self.total_items} Box"
        )
        
        return embed

    @discord.ui.button(emoji="⬅️", style=discord.ButtonStyle.secondary, disabled=True)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            
            self.previous_page.disabled = self.current_page == 0
            self.next_page.disabled = False
            
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(emoji="➡️", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            
            self.next_page.disabled = self.current_page == len(self.pages) - 1
            self.previous_page.disabled = False
            
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="Đóng", emoji="❌", style=discord.ButtonStyle.danger)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="✅ Đã Đóng",
            description="Danh Sâch Đã Được Đóng",
            color=0x808080
        )
        await interaction.response.edit_message(embed=embed, view=None)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


@bot.command()
@check_owner()
async def menu(ctx):
    embed = discord.Embed(
        title="📜・MENU BOT",
        description="✨ Bot By **DKhanh** ✨\n",
        color=discord.Colour.from_rgb(0, 255, 255)
    )
    embed.add_field(
        name="👑・Owner VIP Commands",
        value=(
            f"🔹 **`{config['prefix']}add`** — Thêm Người Dùng Vào Danh Sách Owner\n"
            f"🔹 **`{config['prefix']}remove`** — Xoá Người Dùng Khỏi Danh Sách Owner"
        ),
        inline=False
    )
    embed.add_field(
        name="🤖・Bot Commands",
        value=(
            f"📑 **`{config['prefix']}menu`** — Xem Menu Của Bot\n"
            f"💤 **`{config['prefix']}treo`** — Treo Mess (3 Chức Năng)\n"
            f"🎭 **`{config['prefix']}nhay`** — Nhây/Nhây Tag, Mess Fake Soạn\n"
            f"🎯 **`{config['prefix']}nhaytop`** — Nhây Top Tag Post Group\n"
            f"📜 **`{config['prefix']}treoso`** — Treo Sớ Super Múp, Fake Soạn\n"
            f"📝 **`{config['prefix']}danhsachtask`** — Xem Danh Sách Task Của Bạn\n"
            f"👤 **`{config['prefix']}listbox`** - Xem Danh Sách Box Của Cookies\n"
            f"⛔ **`{config['prefix']}stoptask`** — Dừng Task Theo ID"
        ),
        inline=False
    )
    embed.set_footer(text="✨ Bot DKhanh ✨")
    embed.set_thumbnail(url="https://i.postimg.cc/fTx68pTk/IMG-0037.jpg")
    await ctx.send(embed=embed)

@bot.command()
@check_owner()
async def treoso(ctx):
    embed = discord.Embed(
        title="Ấn Vào Button Start Để Bắt Đầu Nhập Thông Tin Cần Thiết 📘",
        color=0x0099FF
    )
    view = TreoSoView()
    await ctx.send(embed=embed, view=view)

@bot.event
async def on_disconnect():
    print("Bot disconnected, attempting to reconnect...")

@bot.event
async def on_resumed():
    print("Bot connection resumed")

@bot.event
async def on_error(event, *args, **kwargs):
    print(f"An error occurred in {event}: {args}")

async def main():
    while True:
        try:
            await bot.start(config['tokenbot'], reconnect=True)
        except discord.HTTPException as e:
            if e.status == 429:
                print("Rate limited. Waiting...")
                await asyncio.sleep(60)
            else:
                print(f"HTTP Exception: {e}")
                await asyncio.sleep(5)
        except discord.ConnectionClosed:
            print("Connection closed. Reconnecting...")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Unexpected error: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        import sys
        sys.exit(1)