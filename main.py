
from datetime import datetime
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

date_str = datetime.now().strftime("%Y%m%d")
filename = f"tft_players_{date_str}.csv"
final_df = all_players.drop(['rank', 'updated_at'], axis=1)
final_df.to_csv(filename, index=False, encoding='utf-8-sig')
