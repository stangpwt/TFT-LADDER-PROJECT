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

# 1. ดึงข้อมูล Leaderboards
print("📡 Fetching Leaderboards...")

# ดึง Challenger
url_chal = f'https://{SERVER}.api.riotgames.com/tft/league/v1/challenger?queue=RANKED_TFT&api_key={API_KEY}'
data_chal = get_data(url_chal)
df_chal = pd.json_normalize(data_chal['entries']) if data_chal and 'entries' in data_chal else pd.DataFrame()
if not df_chal.empty: df_chal['tier'] = 'Challenger'

# ดึง Grandmaster
url_gm = f'https://{SERVER}.api.riotgames.com/tft/league/v1/grandmaster?queue=RANKED_TFT&api_key={API_KEY}'
data_gm = get_data(url_gm)
df_gm = pd.json_normalize(data_gm['entries']) if data_gm and 'entries' in data_gm else pd.DataFrame()
if not df_gm.empty: df_gm['tier'] = 'Grandmaster'

# รวมตาราง
all_players = pd.concat([df_chal, df_gm], ignore_index=True)

if all_players.empty:
    print("❌ ไม่พบข้อมูลผู้เล่นจาก API กรุณาเช็ค API Key")
    exit(1)

# ตรวจสอบว่าคอลัมน์เขียนว่า summonerId หรือ summonerid
id_col = 'summonerId' if 'summonerId' in all_players.columns else 'summonerid'

# กรองให้เหลือเฉพาะหัวตาราง (20 คนแรก)
all_players = all_players.sort_values(by='leaguePoints', ascending=False).head(20)

riot_ids = []
print(f"📊 Processing {len(all_players)} players...")

for i, row in all_players.iterrows():
    sid = row[id_col] # ใช้ชื่อคอลัมน์ที่ตรวจพบ
    
    # ดึงข้อมูล Summoner
    s_info = get_data(f"https://{SERVER}.api.riotgames.com/tft/summoner/v1/summoners/{sid}?api_key={API_KEY}")
    
    if s_info and 'puuid' in s_info:
        puuid = s_info['puuid']
        # ดึง Riot ID
        acc_info = get_data(f"https://{ROUTING}.api.riotgames.com/riot/account/v1/accounts/by-puuid/{puuid}?api_key={API_KEY}")
        if acc_info:
            riot_ids.append(f"{acc_info['gameName']}#{acc_info['tagLine']}")
        else:
            riot_ids.append("Unknown#Tag")
    else:
        riot_ids.append("Hidden Player")
    
    time.sleep(1.2)

# ใส่ข้อมูลกลับ
all_players['Riot_ID'] = riot_ids
all_players['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# เลือกคอลัมน์ที่มีอยู่จริงมาบันทึก
available_cols = [c for c in ['Riot_ID', 'tier', 'leaguePoints', 'wins', 'losses', 'last_updated'] if c in all_players.columns]
final_df = all_players[available_cols]

# บันทึกไฟล์
final_df.to_csv("tft_players_data.csv", index=False, encoding='utf-8-sig')
print("✅ Done! Data saved successfully.")
