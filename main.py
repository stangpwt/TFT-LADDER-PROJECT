import pandas as pd
import requests
import time
import os

# --- Configuration ---
# ดึง API Key จาก GitHub Secrets (ห้ามเขียนคีย์ลงในนี้ตรงๆ)
API_KEY = os.getenv("RIOT_API_KEY")
SERVER = 'sg2'
ROUTING = 'asia'

def get_league_data(tier):
    url = f'https://{SERVER}.api.riotgames.com/tft/league/v1/{tier}?queue=RANKED_TFT&api_key={API_KEY}'
    res = requests.get(url)
    return pd.json_normalize(res.json()['entries']) if res.status_code == 200 else pd.DataFrame()

def get_riot_id(puuid):
    url = f"https://{ROUTING}.api.riotgames.com/riot/account/v1/accounts/by-puuid/{puuid}?api_key={API_KEY}"
    while True:
        res = requests.get(url)
        if res.status_code == 200:
            data = res.json()
            return f"{data.get('gameName')}#{data.get('tagLine')}"
        elif res.status_code == 429:
            wait_time = int(res.headers.get('Retry-After', 10))
            print(f"⚠️ Rate Limit! Waiting {wait_time}s...")
            time.sleep(wait_time)
            continue
        return "Unknown"

# --- Main Logic ---
print("🚀 Fetching Leaderboard...")
df_chal = get_league_data('challenger')
df_gm = get_league_data('grandmaster')
all_players = pd.concat([df_chal, df_gm], ignore_index=True)

# เพื่อไม่ให้รันนานเกินไปบน GitHub (ซึ่งมีเวลาจำกัด) 
# แนะนำให้ดึงเฉพาะ Top 50 หรือ 100 ก่อนในช่วงแรก
all_players = all_players.head(50) 

riot_ids = []
for i, puuid in enumerate(all_players['puuid']):
    name = get_riot_id(puuid)
    riot_ids.append(name)
    time.sleep(1.2) # ปลอดภัยสำหรับ Key ฟรี

all_players['Riot_ID'] = riot_ids
all_players['updated_at'] = pd.Timestamp.now(tz='Asia/Bangkok')

# บันทึกไฟล์ (ใช้ชื่อเดิมเพื่อให้ GitHub Commit ทับไฟล์เดิม)
filename = "tft_players_data.csv"
all_players.to_csv(filename, index=False, encoding='utf-8-sig')
print(f"✅ Data saved to {filename}")
