# ==========================================
# 📚 クイズデータ（Javaから受け継ぐ版）
# ==========================================
import os
import random
import discord
import sympy as sp
import json

user_scores = {}

# 💡 元の try 〜 except Pass のブロックをこれに書き換えます
from pathlib import Path
try:
    from dotenv import load_dotenv
    # プログラムがある場所（7-bot.pyのフォルダー）の直下にある .env を確実に指名して読み込む
    env_path = Path(__file__).parent / ".env"
    load_dotenv(dotenv_path=env_path)
except ImportError:
    pass

from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

intents = discord.Intents.default()
intents.message_content = True

# 💡 もしこの下の1行が消えていたら、新しく書き足してください！
client = discord.Client(intents=intents)

# 💡 ここに下の2行を追加してください
print(f"【デバッグ】読み込んだURL: {SUPABASE_URL}")
print(f"【デバッグ】読み込んだKEY: {SUPABASE_KEY[:10] if SUPABASE_KEY else 'None'}...")

# ==========================================
# 📊 状態管理変数
# ==========================================
current_quiz = None             
current_quiz_junior_high = None 
current_quiz_academic = None    # 💡 学術クイズ用の状態管理変数を追加

user_status = None 
selected_grade = None    
selected_subject = None         
selected_range = None    
selected_content = None    

# ==========================================
# 📚 すべてのクイズデータ（Javaから読み込み版）
# ==========================================

# ① 中学クイズの読み込み
quiz_junior_high_school = {}
if os.path.exists("quiz_junior_high_school.json"):
    with open("quiz_junior_high_school.json", "r", encoding="utf-8") as f:
        quiz_junior_high_school = json.load(f)

# ② 学術クイズの読み込み
quiz_academic = {}
if os.path.exists("quiz_academic.json"):
    with open("quiz_academic.json", "r", encoding="utf-8") as f:
        quiz_academic = json.load(f)

# ③ 一般知識クイズの読み込み
quiz_dictionary = {}
if os.path.exists("quiz_dictionary.json"):
    with open("quiz_dictionary.json", "r", encoding="utf-8") as f:
        quiz_dictionary = json.load(f)