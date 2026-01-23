
from datetime import datetime, timedelta
import pandas as pd
import requests
import time
import os

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

print("🚀 Fetching Leaderboard...")
df_chal = get_league_data('challenger')
df_chal['tier'] = 'Challenger'
df_gm = get_league_data('grandmaster')
df_gm['tier'] = 'Grandmaster'
all_players = pd.concat([df_chal, df_gm], ignore_index=True)


riot_ids = []
for i, puuid in enumerate(all_players['puuid']):
    name = get_riot_id(puuid)
    riot_ids.append(name)
    time.sleep(1.2) 

all_players['Riot_ID'] = riot_ids
all_players['total_games'] = all_players['wins'] + all_players['losses']
all_players['win_rate'] = (all_players['wins'] / all_players['total_games'] * 100).round(2)
all_players['updated_at'] = pd.Timestamp.now(tz='Asia/Bangkok')

#Folder
folder_name = "data"
if not os.path.exists(folder_name):
    os.makedirs(folder_name)
    print(f"📁 Created folder: {folder_name}")

dt_th = datetime.utcnow() + timedelta(hours=7)
date_str = dt_th.strftime("%Y%m%d")
filename = f"{folder_name}/tft_players_{date_str}.csv" 

all_players.to_csv(filename, index=False, encoding='utf-8-sig')
print(f"✅ บันทึกไฟล์สำเร็จในโฟลเดอร์: {filename}")

#DISCORD NOTI
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

if WEBHOOK_URL:
    top_player = all_players.iloc[0]
    message = {
        "content": f"✅ **อัปเดตอันดับ TFT สำเร็จ!** ({date_str})\n"
                   f"🏆 อันดับ 1: **{top_player['Riot_ID']}** ({top_player['leaguePoints']} LP)\n"
                   f"📊 จำนวนผู้เล่นทั้งหมด: {len(all_players)} คน\n"
                   f"🔗 ดูข้อมูลเต็มๆ ได้ที่ GitHub ของคุณครับ!"
    }
    requests.post(WEBHOOK_URL, json=message)
    print("🔔 ส่งการแจ้งเตือนไปยัง Discord แล้ว")
