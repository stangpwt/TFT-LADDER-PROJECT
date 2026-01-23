import pandas as pd
import requests
import time
import os
from datetime import datetime

# --- Configuration ---
API_KEY = os.getenv("RIOT_API_KEY")
SERVER = 'sg2'
ROUTING = 'asia'

def get_data(url):
    try:
        res = requests.get(url)
        if res.status_code == 200: return res.json()
        if res.status_code == 429:
            wait = int(res.headers.get('Retry-After', 10))
            print(f"⚠️ Rate Limit! Waiting {wait}s...")
            time.sleep(wait)
            return get_data(url)
        return None
    except: return None

# 1. ดึงข้อมูลจากทั้งสอง Tier และเพิ่มคอลัมน์ระบุประเภท
print("📡 Fetching Leaderboards...")

# ดึง Challenger
url_chal = f'https://{SERVER}.api.riotgames.com/tft/league/v1/challenger?queue=RANKED_TFT&api_key={API_KEY}'
data_chal = get_data(url_chal)
df_chal = pd.json_normalize(data_chal['entries']) if data_chal else pd.DataFrame()
df_chal['tier'] = 'Challenger' # เพิ่มคอลัมน์ระบุแรงค์

# ดึง Grandmaster
url_gm = f'https://{SERVER}.api.riotgames.com/tft/league/v1/grandmaster?queue=RANKED_TFT&api_key={API_KEY}'
data_gm = get_data(url_gm)
df_gm = pd.json_normalize(data_gm['entries']) if data_gm else pd.DataFrame()
df_gm['tier'] = 'Grandmaster' # เพิ่มคอลัมน์ระบุแรงค์

# รวมตาราง
all_players = pd.concat([df_chal, df_gm], ignore_index=True)

# กรองให้เหลือเฉพาะหัวตารางเพื่อความรวดเร็วในการรันบน GitHub (เช่น 20 คนแรก)
all_players = all_players.sort_values(by='leaguePoints', ascending=False).head(20)

riot_ids = []
print(f"📊 Processing {len(all_players)} players...")

for i, row in all_players.iterrows():
    sid = row['summonerId']
    # ดึงข้อมูล Summoner เพื่อเอา PUUID และชื่อล่าสุด
    s_info = get_data(f"https://{SERVER}.api.riotgames.com/tft/summoner/v1/summoners/{sid}?api_key={API_KEY}")
    
    if s_info:
        puuid = s_info['puuid']
        # ดึง Riot ID (Name#Tag)
        acc_info = get_data(f"https://{ROUTING}.api.riotgames.com/riot/account/v1/accounts/by-puuid/{puuid}?api_key={API_KEY}")
        if acc_info:
            riot_ids.append(f"{acc_info['gameName']}#{acc_info['tagLine']}")
        else:
            riot_ids.append(s_info.get('name', 'Unknown'))
    else:
        riot_ids.append("Unknown")
    
    time.sleep(1.2) # ปลอดภัยสำหรับ Developer Key

# ใส่ข้อมูลกลับเข้า DataFrame
all_players['Riot_ID'] = riot_ids
all_players['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# จัดลำดับคอลัมน์ให้ดูง่าย
columns_to_save = ['Riot_ID', 'tier', 'leaguePoints', 'wins', 'losses', 'last_updated']
all_players = all_players[columns_to_save]

# บันทึกไฟล์
all_players.to_csv("tft_players_data.csv", index=False, encoding='utf-8-sig')
print("✅ Done! Files updated with Tier info.")
