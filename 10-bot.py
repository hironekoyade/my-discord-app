import os
import random
import discord
import sympy as sp
import json
import string
import asyncio
import requests
from discord.ext import tasks
from discord import app_commands  
from pathlib import Path

# インテンツの設定
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# ==========================================
# 🎮 Roblox連携：セキュリティ対応設定
# ==========================================
ROBLOX_API_KEY = os.getenv("ROBLOX_API_KEY", "None")
UNIVERSE_ID = os.getenv("ROBLOX_UNIVERSE_ID", "None")
DATASTORE_NAME = os.getenv("ROBLOX_DATASTORE_NAME", "GameScores")
BLOXLINK_API_KEY = os.getenv("BLOXLINK_API_KEY")

print(f"【デバッグ】Roblox ID: {UNIVERSE_ID}")
print(f"【デバッグ】Roblox Key: {ROBLOX_API_KEY[:5] if ROBLOX_API_KEY else 'None'}...")

# ==========================================
# 🔑 パスワード管理（6桁英数字統一・4桁廃止）
# ==========================================
ADMIN_PASSWORD = "".join(random.choices(string.ascii_letters + string.digits, k=6))

# 👑 絶対に変わらない「元の3人（創設者）」の固定IDリスト
ORIGINAL_ADMINS = [
    1385634725460316273,
    1551496753088561238,  
    1446830807007101102
]

# 📝 動的に「運営」が増えていくリスト
ADMIN_USER_ID = ORIGINAL_ADMINS.copy()

# 🔑 パスワード認証を突破した「各サーバーの管理者」を記憶するリスト
AUTHENTICATED_SERVER_ADMINS = []

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    load_dotenv(dotenv_path=env_path)
except ImportError:
    pass

from supabase import create_client, Client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

print(f"【デバッグ】読み込んだURL: {SUPABASE_URL}")
print(f"【デバッグ】読み込んだKEY: {SUPABASE_KEY[:10] if SUPABASE_KEY else 'None'}...")

# パスワード自動変更タスク
@tasks.loop(hours=24)
async def auto_reset_password():
    global ADMIN_PASSWORD
    characters = string.ascii_letters + string.digits
    ADMIN_PASSWORD = "".join(random.choices(characters, k=6))
    print(f"【🔑定期リセット】24時間が経過したため、パスワードを自動変更しました: {ADMIN_PASSWORD}")

# Botが起動したとき
@client.event
async def on_ready():
    print(f"ログインしました: {client.user}")
    print(f"【🔑システムログ】初期パスワードは: {ADMIN_PASSWORD}")
    
    if not auto_reset_password.is_running():
        auto_reset_password.start()
        
    if not auto_announce_ranking.is_running():
        auto_announce_ranking.start()

    # 👑 【修正】フリーズ防止のため、起動時にここで1回だけ同期を実行
    try:
        await tree.sync()
        print("【🤖システムログ】すべてのスラッシュコマンドの同期が完了しました！")
    except Exception as e:
        print(f"コマンド同期エラー: {e}")

# ==========================================
# 📊 定期ランキング自動発表システム
# ==========================================
@tasks.loop(hours=24)
async def auto_announce_ranking():
    for guild_id_str, settings in server_settings.items():
        channel_ids = settings.get("quiz_channel_ids", [])
        if not channel_ids:
            old_id = settings.get("quiz_channel_id")
            if old_id:
                channel_ids = [old_id]
        if not channel_ids:
            continue

        target_channel = client.get_channel(channel_ids[0])
        if target_channel is None:
            continue

        try:
            response = supabase.table("user_scores").select("*").order("correct_count", desc=True).limit(5).execute()
            if response.data and len(response.data) > 0:
                embed = discord.Embed(
                    title="🏆 【毎日発表】クイズ正解数ランキング・トップ5 🏆",
                    description="現在のサーバー内のクイズ強者たちの成績です！みんなも負けずに挑戦しよう！",
                    color=discord.Color.gold()
                )
                medals = ["🥇 1位", "🥈 2位", "🥉 3位", "✨ 4位", "✨ 5位"]
                for i, row in enumerate(response.data):
                    username = row.get("username", "名無し学者")
                    correct = row.get("correct_count", 0)
                    wrong = row.get("wrong_count", 0)
                    rank_label = medals[i] if i < len(medals) else f"🔹 {i+1}位"
                    embed.add_field(
                        name=f"{rank_label}：{username} さん",
                        value=f"• 正解数: **{correct}回** ⭕ / 不正解: {wrong}回 ❌",
                        inline=False
                    )
                embed.set_footer(text="※ランキングは24時間ごとに自動更新されます。")
                await target_channel.send(embed=embed)
        except Exception as e:
            print(f"定期ランキング発表エラー: {e}")

# ==========================================
# 📊 マルチサーバー対応：状態管理システム
# ==========================================
server_current_quiz = {}             
server_current_quiz_jh = {} 
server_current_quiz_academic = {}    

user_status_dict = {} 
user_selected_grade = {}    
user_selected_subject = {}         
user_selected_range = {}    
user_selected_content = {} 

is_rank_role_enabled = True  

# ==========================================
# ⚙️ サーバーごとの個別設定管理システム
# ==========================================
server_settings = {}

if os.path.exists("server_settings.json"):
    with open("server_settings.json", "r", encoding="utf-8") as f:
        server_settings = json.load(f)

def save_server_settings():
    with open("server_settings.json", "w", encoding="utf-8") as f:
        json.dump(server_settings, f, ensure_ascii=False, indent=4)

def is_rank_enabled_for_guild(guild_id: int) -> bool:
    str_id = str(guild_id)
    return server_settings.get(str_id, {}).get("rank_role_enabled", True)

# クイズデータのロード
quiz_junior_high_school = {}
if os.path.exists("quiz_junior_high_school.json"):
    with open("quiz_junior_high_school.json", "r", encoding="utf-8") as f:
        quiz_junior_high_school = json.load(f)

quiz_academic = {}
if os.path.exists("quiz_academic.json"):
    with open("quiz_academic.json", "r", encoding="utf-8") as f:
        quiz_academic = json.load(f)

quiz_dictionary = {}
if os.path.exists("quiz_dictionary.json"):
    with open("quiz_dictionary.json", "r", encoding="utf-8") as f:
        quiz_dictionary = json.load(f)

# ==========================================
# 💡 ボタンコンポーネントクラス（フリーズ＆色固定 対策版）
# ==========================================
class AcademicQuizButton(discord.ui.Button):
    def __init__(self, label, view_obj, style):
        super().__init__(label=label, style=style)
        self.view_obj = view_obj

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.view_obj.process_choice(interaction, self.label)


class AcademicQuizView(discord.ui.View):
    def __init__(self, correct_answer, explanation, options):
        super().__init__(timeout=60.0) 
        self.correct_answer = correct_answer
        self.explanation = explanation
        
        shuffled_options = options.copy()
        random.shuffle(shuffled_options)
        
        button_styles = [
            discord.ButtonStyle.primary,
            discord.ButtonStyle.success,
            discord.ButtonStyle.secondary,
            discord.ButtonStyle.danger,
            discord.ButtonStyle.primary
        ]
        for i, opt in enumerate(shuffled_options):
            current_style = button_styles[i % len(button_styles)]
            btn = AcademicQuizButton(label=opt, view_obj=self, style=current_style)
            self.add_item(btn)

    async def process_choice(self, interaction: discord.Interaction, chosen_label: str):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        await interaction.message.edit(view=self)

        user_id = interaction.user.id
        is_correct = (chosen_label == self.correct_answer)

        if is_correct:
            update_db_score(user_id, interaction.user.display_name, is_correct, interaction.message, member=interaction.user)
            await interaction.channel.send(f"💡 {interaction.user.mention} **正解！お見事です（学術クイズ）！🎉**")
            await interaction.channel.send(f'<:hint:1556661937356546069> 【解説】\n{self.explanation}')
        else:
            update_db_score(user_id, interaction.user.display_name, is_correct, interaction.message, member=interaction.user)
            await interaction.channel.send(f"😢 {interaction.user.mention} **不正解です...。もう一度挑戦してみてください！**")
            await interaction.channel.send(f"正解は **【 {self.correct_answer} 】** でした！")

        global server_current_quiz, server_current_quiz_jh, server_current_quiz_academic, user_status_dict
        g_id = interaction.guild.id if interaction.guild else 0
        u_id = interaction.user.id
        if g_id in server_current_quiz: del server_current_quiz[g_id]
        if g_id in server_current_quiz_jh: del server_current_quiz_jh[g_id]
        if g_id in server_current_quiz_academic: del server_current_quiz_academic[g_id]
        if u_id in user_status_dict: del user_status_dict[u_id]
        self.stop()


class MultiChoiceQuizButton(discord.ui.Button):
    def __init__(self, label, view_obj, style):
        super().__init__(label=label, style=style)
        self.view_obj = view_obj

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.view_obj.process_choice(interaction, self)


class MultiChoiceQuizView(discord.ui.View):
    def __init__(self, correct_answers, explanation, options):
        super().__init__(timeout=60.0)
        self.correct_answers = correct_answers
        self.explanation = explanation
        self.selected_buttons = []
        
        shuffled_options = options.copy()
        random.shuffle(shuffled_options)
        
        button_styles = [
            discord.ButtonStyle.primary,
            discord.ButtonStyle.success,
            discord.ButtonStyle.secondary,
            discord.ButtonStyle.danger,
            discord.ButtonStyle.primary
        ]
        for i, opt in enumerate(shuffled_options):
            current_style = button_styles[i % len(button_styles)]
            btn = MultiChoiceQuizButton(label=opt, view_obj=self, style=current_style)
            self.add_item(btn)

    async def process_choice(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.selected_buttons) >= 2 and button not in self.selected_buttons:
            return
        if button in self.selected_buttons:
            self.selected_buttons.remove(button)
            button.style = discord.ButtonStyle.secondary
        else:
            self.selected_buttons.append(button)
            button.style = discord.ButtonStyle.primary

        if len(self.selected_buttons) < 2:
            await interaction.message.edit(view=self)
            return

        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
                if item.label in self.correct_answers:
                    item.style = discord.ButtonStyle.success
                elif item in self.selected_buttons:
                    item.style = discord.ButtonStyle.danger

        await interaction.message.edit(view=self)

        user_id = interaction.user.id
        user_choices = [btn.label for btn in self.selected_buttons]
        is_all_correct = all(ans in user_choices for ans in self.correct_answers)

        if is_all_correct:
            update_db_score(user_id, interaction.user.display_name, True, interaction.message, member=interaction.user)
            await interaction.channel.send(f"💡 {interaction.user.mention} **大正解！2つの選択肢を完璧に見抜きました！🎉**")
            await interaction.channel.send(f'<:hint:1556661937356546069> 【解説】\n{self.explanation}')
        else:
            update_db_score(user_id, interaction.user.display_name, False, interaction.message, member=interaction.user)
            correct_text = " と ".join([f"【{a}】" for a in self.correct_answers])
            await interaction.channel.send(f"😢 {interaction.user.mention} **残念、不正解です...。**\n正解は {correct_text} でした！")
        
        global server_current_quiz, server_current_quiz_jh, server_current_quiz_academic, user_status_dict
        g_id = interaction.guild.id if interaction.guild else 0
        u_id = interaction.user.id
        if g_id in server_current_quiz: del server_current_quiz[g_id]
        if g_id in server_current_quiz_jh: del server_current_quiz_jh[g_id]
        if g_id in server_current_quiz_academic: del server_current_quiz_academic[g_id]
        if u_id in user_status_dict: del user_status_dict[u_id]
        self.stop()

# ==========================================
# 👑 新設：運営承認システム用のコンポーネント
# ==========================================
class StaffApplyModal(discord.ui.Modal, title="運営スタッフ応募フォーム"):
    reason_input = discord.ui.TextInput(
        label="志望動機や意気込みを教えてください",
        style=discord.TextStyle.long,
        placeholder="例：クイズの管理や運営を一緒にお手伝いしたいです！",
        min_length=10,
        max_length=200
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("📩 運営への申請を送信しました。創設者の審査をお待ちください！", ephemeral=True)
        
        # 👑 創設者（元のリストの最初の人など）のDMへボタン付きメッセージを転送
        try:
            creator = await client.fetch_user(ORIGINAL_ADMINS[0])
            if creator:
                embed = discord.Embed(
                    title="🚀 【新しい運営申請】が届きました！",
                    description=f"申請者: {interaction.user.mention} (ID: `{interaction.user.id}`)\n\n**【志望動機】**\n{self.reason_input.value}",
                    color=discord.Color.teal()
                )
                view = AdminReviewView(interaction.user.id)
                await creator.send(embed=embed, view=view)
        except Exception as e:
            print(f"運営申請転送エラー: {e}")


class AdminReviewView(discord.ui.View):
    def __init__(self, applicant_id):
        super().__init__(timeout=None)
        self.applicant_id = applicant_id

    @discord.ui.button(label="🟢 承認する", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        global ADMIN_USER_ID
        if interaction.user.id not in ORIGINAL_ADMINS:
            await interaction.response.send_message("❌ この操作は創設者のみ可能です。", ephemeral=True)
            return

        if self.applicant_id not in ADMIN_USER_ID:
            ADMIN_USER_ID.append(self.applicant_id)

        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.send_message(f"✅ ユーザー(ID: `{self.applicant_id}`) を「運営」として【承認】しました。")

        try:
            applicant = await client.fetch_user(self.applicant_id)
            if applicant:
                await applicant.send("🎉 クイズBotの運営申請が承認され、管理権限（運営）が付与されました！")
        except Exception as e:
            print(f"本人への承認DM送信失敗: {e}")

    @discord.ui.button(label="🔴 却下する", style=discord.ButtonStyle.danger)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in ORIGINAL_ADMINS:
            await interaction.response.send_message("❌ この操作は創設者のみ可能です。", ephemeral=True)
            return

        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.send_message(f"❌ ユーザー(ID: `{self.applicant_id}`) の運営申請を【却下】しました。")

        try:
            applicant = await client.fetch_user(self.applicant_id)
            if applicant:
                await applicant.send("😢 残念ながら、クイズBotの運営申請は今回は見送りとなりました。")
        except Exception as e:
            print(f"本人への却下DM送信失敗: {e}")

# ==========================================
# 🎰 UI連動型：ボタン式ルーレットシステム
# ==========================================
class RouletteButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="🎰 ルーレットをスタートする！", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.view_obj.start_rotation(interaction)


class RouletteView(discord.ui.View):
    def __init__(self, options):
        super().__init__(timeout=120.0)
        self.options = options
        self.button = RouletteButton()
        self.button.view_obj = self
        self.add_item(self.button)

    async def start_rotation(self, interaction: discord.Interaction):
        self.button.disabled = True
        self.button.label = "⏳ 抽選中..."
        self.button.style = discord.ButtonStyle.secondary
        await interaction.edit_original_response(view=self)

        status_msg = await interaction.channel.send(f"🔮 {interaction.user.mention} さんがルーレットを始動しました！")
        await asyncio.sleep(0.8)
        await status_msg.edit(content="🎰 ドゥルルルルルルルルルルルル……")
        await asyncio.sleep(1.2)
        await status_msg.edit(content="👀 くるくる…… ぴたっ…… 💡")
        await asyncio.sleep(0.8)

        chosen = random.choice(self.options)
        embed = discord.Embed(
            title="🎯 ルーレット抽選結果 🎯",
            description=f"抽選を実行した人：{interaction.user.mention}\n\n🥇 当選したのは……\n\n🏆 **【 {chosen} 】** です！！ 🎉",
            color=discord.Color.random()
        )
        embed.set_footer(text=f"選択肢の候補：{'、'.join(self.options)}")
        await status_msg.delete()
        await interaction.channel.send(embed=embed)
        self.stop()

    async def on_timeout(self):
        self.button.disabled = True
        self.button.label = "❌ 時間切れ（無効）"
        self.stop()

# ==========================================
# 💬 スラッシュコマンド版：挨拶＆エンタメ
# ==========================================
@tree.command(name="/こんにちは", description="ひろねこbotが元気よく挨拶します！")
async def slash_hello(interaction: discord.Interaction):
    await interaction.response.send_message(f"こんにちは、{interaction.user.mention}さん！今日も良い1日にしましょう！☀️")

@tree.command(name="/おはよう", description="ひろねこbotが朝の挨拶をします！")
async def slash_morning(interaction: discord.Interaction):
    await interaction.response.send_message(f"おはようございます、{interaction.user.mention}さん！体調はどうですか？乗っていきましょう！🌱")

@tree.command(name="/こんばんは", description="ひろねこbotが夕方の挨拶をします！")
async def slash_evening(interaction: discord.Interaction):
    await interaction.response.send_message(f"こんばんは、{interaction.user.mention}さん！今日のクイズの調子はどうでしたか？✨")

@tree.command(name="/おやすみ", description="ひろねこbotが夜の挨拶をします！")
async def slash_night(interaction: discord.Interaction):
    await interaction.response.send_message(f"おやすみなさい、{interaction.user.mention}さん。ゆっくり休んで、また明日クイズに挑戦してね。💤")

@tree.command(name="/運営申請", description="ひろねこbotの「運営スタッフ」への昇格申請フォームを開きます。")
async def slash_apply(interaction: discord.Interaction):
    await interaction.response.send_modal(StaffApplyModal())

@tree.command(name="/help-hironekobot", description="ひろねこbotのすべてのスラッシュコマンドと使い方の一覧表を表示します。")
async def slash_help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 ひろねこbot 新・スラッシュコマンド一覧表",
        description="スラッシュ（`/`）を入力するだけで、スマホからでも簡単に呼び出せるようになりました！",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="📚 クイズ機能 `/クイズ`",
        value=(
            "メニューからモードを選択して出題します！\n"
            "• `一般クイズ` : 誰でも解ける一般知識問題\n"
            "• `学術クイズ` : ボタンで答える高度な専門クイズ\n"
            "• `中学クイズメニュー` : 学年・教科・単元をチャットで選んで出題\n"
            "• `中学クイズおまかせ` : 中学生の全範囲から完全ランダム出題"
        ),
        inline=False
    )
    embed.add_field(
        name="🚀 運営機能 `/運営申請`",
        value="• 申請フォームを送信し、創設者に承認されることで「運営」リストへ登録されます。",
        inline=False
    )
    embed.add_field(
        name="🎲 お楽しみエンタメ機能",
        value=(
            "• `/ルーレット` : 🎰 自由入力や数値範囲指定に対応！\n"
            "• `/占い` : 🔮 今日の運勢・明日の運勢を占います\n"
            "• `/サイコロ` : 面の数と振る個数を自由に指定して振る\n"
            "• `/州えらび` : 世界の6大州からランダムに1つ自動選出"
        ),
        inline=False
    )
    await interaction.response.send_message(embed=embed)

@tree.command(name="占い", description="今日または明日の運勢、ラッキーカラーやアイテムを占います！")
@app_commands.describe(day="占いたい日を選択してください")
@app_commands.choices(day=[
    app_commands.Choice(name="今日の運勢", value="today"),
    app_commands.Choice(name="明日の運勢", value="tomorrow")
])
async def slash_fortune(interaction: discord.Interaction, day: str):
    await interaction.response.defer()
    user_id = interaction.user.id
    day_text = "今日" if day == "today" else "明日"
    
    import datetime
    current_date_str = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d")

    fortunes = ["🌟 超大吉", "✨ 大吉", "🎵 中吉", "😊 小吉", "🍀 吉", "💤 末吉", "☔ 凶", "✖大凶"]
    colors = ["赤色", "青色", "黄色", "緑色", "ピンク", "紫色", "オレンジ色", "白色", "黒色", "ゴールド"]
    items = ["お気に入りのペン", "クイズの参考書", "スマホ", "いつもと違う靴下", "マイボトル", "ハンカチ", "お菓子"]
    
    embed = discord.Embed(
        title=f"🔮 ひろねこ占い（{day_text}の運勢）",
        description=f"{interaction.user.mention} さんの{day_text}の運勢を占いました！",
        color=discord.Color.purple()
    )
    embed.add_field(name="✨ 総合運", value=f"**{random.choice(fortunes)}**", inline=False)
    embed.add_field(name="🎨 ラッキーカラー", value=random.choice(colors), inline=True)
    embed.add_field(name="🎒 ラッキーアイテム", value=random.choice(items), inline=True)

    try:
        res = supabase.table("user_scores").select("*").eq("user_id", user_id).execute()
        last_date = None
        correct_count, wrong_count = 0, 0
        is_rank_enabled = True

        user_data_list = getattr(res, "data", res)
        if user_data_list and isinstance(user_data_list, list) and len(user_data_list) > 0:
            user_data = user_data_list[0]
            correct_count = user_data.get("correct_count", 0)
            wrong_count = user_data.get("wrong_count", 0)
            is_rank_enabled = user_data.get("is_rank_enabled", True)
            last_date = user_data.get("last_fortune_date") if day == "today" else user_data.get("last_tomorrow_fortune_date")

        if last_date and (str(last_date) == current_date_str):
            await interaction.followup.send(f"⚠️ {interaction.user.mention} さん、**{day_text}の運勢はすでに占われています！** また明日挑戦してね！")
            return

        update_data = {
            "user_id": user_id, "username": interaction.user.display_name,
            "correct_count": correct_count, "wrong_count": wrong_count,
            "is_rank_enabled": is_rank_enabled, "updated_at": "now()"
        }
        if day == "today": update_data["last_fortune_date"] = current_date_str
        else: update_data["last_tomorrow_fortune_date"] = current_date_str

        supabase.table("user_scores").upsert(update_data).execute()
        await interaction.followup.send(embed=embed)
    except Exception as e:
        print(f"占いエラー: {e}")
        await interaction.followup.send("❌ データベースエラーが発生しました。")

@tree.command(name="州えらび", description="世界の6大州からランダムに1つを選出します。")
async def slash_continent(interaction: discord.Interaction):
    continents = ["アジア州", "ヨーロッパ州", "アフリカ州", "北アメリカ州", "南アメリカ州", "オセアニア州"]
    chosen = random.choice(continents)
    embed = discord.Embed(
        title="🌍 ランダム州選出 🌍",
        description=f"抽選の結果、選ばれたのは……\n\n🎯 **【 {chosen} 】** です！",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed)

@tree.command(name="サイコロ", description="サイコロを振ります。面の数と振る個数を指定できます。")
@app_commands.describe(max_value="サイコロの面の数（デフォルト: 6）", dice_count="振る個数（デフォルト: 1）")
async def slash_dice(interaction: discord.Interaction, max_value: int = 6, dice_count: int = 1):
    if max_value < 1 or dice_count < 1 or max_value > 1000000 or dice_count > 30:
        await interaction.response.send_message("❌ 不正な値です。（面数: 最大1,000,000 / 個数: 最大30）", ephemeral=True)
        return
    results = [random.randint(1, max_value) for _ in range(dice_count)]
    total = sum(results)
    if dice_count == 1:
        await interaction.response.send_message(f"🎲 1 〜 {max_value} のサイコロを振りました！ 出た目は **【 {total} 】** です！")
    else:
        details = " ＋ ".join([f"[{r}]" for r in results])
        await interaction.response.send_message(f"🎲 1 〜 {max_value} のサイコロを **{dice_count} 個** 振りました！\n内訳: {details}\n合計は **【 {total} 】** です！")

# ==========================================
# 🎖️ スラッシュコマンド版：/クイズ（完全統合版）
# ==========================================
@tree.command(name="/クイズ", description="各種クイズに挑戦します。")
@app_commands.describe(mode="クイズの形式を選択してください")
@app_commands.choices(mode=[
    app_commands.Choice(name="一般クイズ", value="general"),
    app_commands.Choice(name="学術クイズ", value="academic"),
    app_commands.Choice(name="中学クイズメニュー", value="junior_high"),
    app_commands.Choice(name="中学クイズおまかせ", value="junior_high_random")
])
async def slash_quiz(interaction: discord.Interaction, mode: str):
    global server_current_quiz, server_current_quiz_jh, server_current_quiz_academic, user_status_dict
    guild_id = interaction.guild.id if interaction.guild else 0
    user_id = interaction.user.id

    if interaction.guild:
        target_ids = server_settings.get(str(guild_id), {}).get("quiz_channel_ids", [])
        if target_ids and (interaction.channel_id not in target_ids):
            await interaction.response.send_message("❌ このチャンネルでのクイズの実行は許可されていません。", ephemeral=True)
            return

    if (guild_id in server_current_quiz) or (guild_id in server_current_quiz_jh) or (guild_id in server_current_quiz_academic) or (user_status_dict.get(user_id) in ["quiz_active", "academic_quiz_active"]):
        await interaction.response.send_message("⚠️ 現在クイズが出題中、または選択処理中です。解答するか `!ストップ` してください。", ephemeral=True)
        return

    await interaction.response.defer()

    if mode == "general":
        if not quiz_dictionary:
            await interaction.followup.send("一般クイズのデータが空、または読み込めていません。")
            return
        chosen_quiz = random.choice(list(quiz_dictionary.keys()))
        quiz_data = quiz_dictionary[chosen_quiz]
        server_current_quiz[guild_id] = chosen_quiz
        
        embed = discord.Embed(
            title="【一般知識クイズ】",
            description=f"**問題：{chosen_quiz}**",
            color=discord.Color.blue()
        )
        if isinstance(quiz_data, dict) and quiz_data.get("image_url"):
            embed.set_image(url=quiz_data["image_url"])
        await interaction.followup.send(embed=embed)

    elif mode == "academic":
        if not quiz_academic:
            await interaction.followup.send("学術クイズのデータが空、または読み込めていません。")
            return
        chosen_category = random.choice(list(quiz_academic.keys()))
        category_quizzes = quiz_academic[chosen_category]
        q_text = random.choice(list(category_quizzes.keys()))
        q_data = category_quizzes[q_text]
        
        server_current_quiz_academic[guild_id] = q_data
        user_status_dict[user_id] = "academic_quiz_active"

        if q_data["type"] == "choice":
            view = AcademicQuizView(q_data["answer"], q_data["explanation"], q_data["options"])
            embed = discord.Embed(
                title=f"🎯 【クイズ - {chosen_category}】（4択ボタン形式）",
                description=f"**問題：{q_text}**",
                color=discord.Color.green()
            )
            if q_data.get("image_url"): embed.set_image(url=q_data["image_url"])
            await interaction.followup.send(embed=embed, view=view)
        elif q_data["type"] == "multi_choice":
            view = MultiChoiceQuizView(q_data["answer"], q_data["explanation"], q_data["options"])
            embed = discord.Embed(
                title=f"🔥 【特別クイズ - {chosen_category}】（5択・2つ選択形式）",
                description=f"**問題：{q_text}**\n\n⚠️ **【ルール】ボタンを【2つ】押してください！**",
                color=discord.Color.red()
            )
            if q_data.get("image_url"): embed.set_image(url=q_data["image_url"])
            await interaction.followup.send(embed=embed, view=view)

    elif mode == "junior_high":
        user_status_dict[user_id] = "select_grade"
        grades = list(quiz_junior_high_school.keys())
        grades_text = "・".join(grades)
        await interaction.followup.send(f"📚 **中学クイズメニューを開きました。**\n**どの学年の問題に挑戦しますか？**\nチャット欄に「{grades_text}」のいずれかを直接入力して送信してください！")

    elif mode == "junior_high_random":
        if not quiz_junior_high_school:
            await interaction.followup.send("中学クイズのデータが空、または読み込めていません。")
            return
        all_questions = []
        for gd, sbs in quiz_junior_high_school.items():
            for sb, rgs in sbs.items():
                for rg, cts in rgs.items():
                    for ct, qs in cts.items():
                        for q_t, q_d in qs.items():
                            all_questions.append({"text": q_t, "data": q_d, "info": f"【{gd} ➔ {sb} ➔ {rg} ➔ {ct}】"})
        if not all_questions:
            await interaction.followup.send("登録されている中学クイズの問題が見つかりません。")
            return
        chosen = random.choice(all_questions)
        q_data = chosen["data"]
        server_current_quiz_jh[guild_id] = q_data 
        user_status_dict[user_id] = "quiz_active"
        
        embed = discord.Embed(
            title="🎲 中学クイズおまかせ出題",
            description=f"💡 出題範囲：{chosen['info']}\n\n**問題：{chosen['text']}**",
            color=discord.Color.orange()
        )
        if q_data.get("image_url"): embed.set_image(url=q_data["image_url"])
        await interaction.followup.send(embed=embed)

@tree.command(name="/ルーレット", description="ボタン式の本格演出ルーレットを開始します！")
@app_commands.describe(
    items="【自由入力】項目をスペースで区切って入力",
    max_num="【数値指定】1から指定した数字まで",
    min_num="【範囲指定オプション】下限の数字を指定したい時"
)
async def slash_roulette(interaction: discord.Interaction, items: str = None, max_num: int = None, min_num: int = None):
    await interaction.response.defer()
    options = []
    mode_text = ""

    if min_num is not None and max_num is not None:
        if min_num >= max_num:
            await interaction.followup.send("❌ 下限値は上限値より小さい数字を入力してください。", ephemeral=True)
            return
        options = [str(i) for i in range(min_num, max_num + 1)]
        mode_text = f"⚙️ **範囲連番モード（{min_num} 〜 {max_num}）**"
    elif max_num is not None:
        if max_num < 2:
            await interaction.followup.send("❌ 2以上の数値を指定してください。", ephemeral=True)
            return
        start_val = min_num if min_num is not None else 1
        options = [str(i) for i in range(start_val, max_num + 1)]
        mode_text = f"🔢 **数値指定モード（{start_val} 〜 {max_num}）**"
    elif items is not None:
        options = items.split()
        mode_text = "💬 **自由入力モード**"
    else:
        await interaction.followup.send("❌ 引数が足りません。", ephemeral=True)
        return

    view = RouletteView(options)
    display_options = options[:15]
    footer_text = ", ".join([f"「{o}」" for o in display_options])
    if len(options) > 15: footer_text += f" ...他 {len(options) - 15} 個"

    await interaction.followup.send(f"🎲 **ルーレットがセットされました！**（{mode_text}）\n📋 **候補：** {footer_text}\n準備ができたら、下のボタンを押してスタートしてね！👇", view=view)

def update_db_score(user_id: int, username: str, is_correct: bool, message: discord.Message = None, member: discord.Member = None):
    try:
        response = supabase.table("user_scores").select("*").eq("user_id", user_id).execute()
        user_rank_preference = True
        correct = 1 if is_correct else 0
        wrong = 0 if is_correct else 1
        
        user_data_list = getattr(response, "data", response)
        if user_data_list and isinstance(user_data_list, list) and len(user_data_list) > 0:
            current = user_data_list[0]
            correct = current.get("correct_count", 0) + (1 if is_correct else 0)
            wrong = current.get("wrong_count", 0) + (0 if is_correct else 1)
            user_rank_preference = current.get("is_rank_enabled", True)

        supabase.table("user_scores").upsert({
            "user_id": user_id, "username": username, "correct_count": correct,
            "wrong_count": wrong, "is_rank_enabled": user_rank_preference, "updated_at": "now()"
        }).execute()

        if is_correct and message and message.guild and member:
            if member.id == client.user.id: return
            if user_rank_preference:
                async def assign_rank_role():
                    role_name = None
                    if correct >= 120: role_name = "永世博士"
                    elif correct >= 80: role_name = "博士博士号"
                    elif correct >= 50: role_name = "物知り博士"
                    elif correct >= 30: role_name = "クイズ達人"
                    elif correct >= 10: role_name = "見習い学者"
                    
                    if role_name:
                        role = discord.utils.get(message.guild.roles, name=role_name)
                        if role and (role not in member.roles):
                            try:
                                await member.add_roles(role)
                                await message.channel.send(f"🆙 **【ランクアップ！】** {member.mention} さんの累計正解数が **{correct}問** に達したため、**【{role_name}】** に昇進しました！ 🎉")
                            except discord.Forbidden:
                                await message.channel.send(f"⚠️ 権限エラー: Botの役職順位が低いため、**【{role_name}】** を付与できませんでした。")
                client.loop.create_task(assign_rank_role())
    except Exception as e:
        print(f"Supabase書き込み/ロール付与エラー: {e}")

# ==========================================
# 💬 旧テキストコマンド＆メッセージ監視システム
# ==========================================
@client.event
async def on_message(message):
    global server_current_quiz, server_current_quiz_jh, server_current_quiz_academic, user_status_dict
    global user_selected_grade, user_selected_subject, user_selected_range, user_selected_content
    global AUTHENTICATED_SERVER_ADMINS, ADMIN_USER_ID

    if message.author.bot: return

    guild_id = message.guild.id if message.guild else 0
    user_id = message.author.id

    # 🔑 各サーバー管理者用のパスワード認証システム
    if message.content == "!admin":
        class AuthButtonView(discord.ui.View):
            def __init__(self): super().__init__(timeout=60.0)
            @discord.ui.button(label="🔑 管理者認証（パスワード入力）", style=discord.ButtonStyle.primary)
            async def open_modal(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                class SimpleAuthModal(discord.ui.Modal, title="サーバー管理者認証"):
                    pwd_input = discord.ui.TextInput(label="6桁の英数字パスワードを入力してください", max_length=6, min_length=6)
                    async def on_submit(self, modal_interaction: discord.Interaction):
                        global AUTHENTICATED_SERVER_ADMINS
                        if self.pwd_input.value == ADMIN_PASSWORD:
                            if modal_interaction.user.id not in AUTHENTICATED_SERVER_ADMINS:
                                AUTHENTICATED_SERVER_ADMINS.append(modal_interaction.user.id)
                            await modal_interaction.response.send_message("✅ パスワード認証に成功しました！このサーバー内での設定変更コマンドが許可されます。", ephemeral=True)
                        else:
                            await modal_interaction.response.send_message("❌ パスワードが違います。", ephemeral=True)
                await button_interaction.response.send_modal(SimpleAuthModal())
        await message.channel.send("以下のボタンを押して、サーバー管理者用のパスワードを入力してください！", view=AuthButtonView())
        return

    # 👑 特定のユーザーを「運営」リストから除外するコマンド（創創者専用）
    if message.content.startswith("!admin-remove"):
        if message.author.id in ORIGINAL_ADMINS:
            args = message.content.split()
            if len(args) < 2:
                await message.channel.send("❌ 使用方法: `!admin-remove [ユーザーID]`")
                return
            try:
                target_id = int(args[1])
                if target_id in ORIGINAL_ADMINS:
                    await message.channel.send("❌ 創設者を運営リストから除外することはできません。")
                    return
                if target_id in ADMIN_USER_ID:
                    ADMIN_USER_ID.remove(target_id)
                    await message.channel.send(f"👑 ユーザーID: `{target_id}` を運営リストから削除しました。")
                else:
                    await message.channel.send("⚠️ そのユーザーは運営リストに登録されていません。")
            except ValueError:
                await message.channel.send("❌ 正しいユーザーIDを数値で入力してください。")
        else:
            await message.channel.send("❌ エラー：このコマンドはBotの【創設者】のみが実行できます。")
        return

    if message.content == "!password-reset":
        if message.author.id in ORIGINAL_ADMINS:
            global ADMIN_PASSWORD
            characters = string.ascii_letters + string.digits
            ADMIN_PASSWORD = "".join(random.choices(characters, k=6))
            try:
                await message.author.send(f"👑 パスワードを強制リセットしました：【{ADMIN_PASSWORD}】")
                await message.channel.send("🔄 パスワードをランダムな新しい値に変更しました！（実行者にDM送信済）")
            except discord.Forbidden:
                await message.channel.send("🔄 パスワードを変更しました！")
        else:
            await message.channel.send("❌ エラー：この緊急コマンドはBotの【創設者】のみが実行できます。")
        return

    # 🛠️ 専用チャンネルの「追加・削除」ガード
    is_bot_admin_or_server_manager = (user_id in ADMIN_USER_ID) or (user_id in AUTHENTICATED_SERVER_ADMINS) or (message.author.guild_permissions.administrator if message.guild else False)

    if message.content == "!add-quiz-channel":
        if is_bot_admin_or_server_manager:
            if message.guild is None: return
            guild_id_str = str(message.guild.id)
            if guild_id_str not in server_settings: server_settings[guild_id_str] = {}
            if "quiz_channel_ids" not in server_settings[guild_id_str]: server_settings[guild_id_str]["quiz_channel_ids"] = []
            current_channels = server_settings[guild_id_str]["quiz_channel_ids"]
            
            if message.channel.id in current_channels:
                await message.channel.send("⚠️ このチャンネルはすでにクイズ専用チャンネルとして登録されています。")
            else:
                current_channels.append(message.channel.id)
                save_server_settings()
                await message.channel.send(f"🎯 **チャンネルを追加しました：** 以降、**{message.channel.mention}** でもクイズ機能が動作します！")
        return

    if message.content == "!remove-quiz-channel":
        if is_bot_admin_or_server_manager:
            if message.guild is None: return
            guild_id_str = str(message.guild.id)
            current_channels = server_settings.get(guild_id_str, {}).get("quiz_channel_ids", [])
            if message.channel.id in current_channels:
                current_channels.remove(message.channel.id)
                save_server_settings()
                await message.channel.send(f"❌ **チャンネルを解除しました：** 以降、**{message.channel.mention}** ではクイズ機能が動作しません。")
            else:
                await message.channel.send("⚠️ このチャンネルはクイズ専用チャンネルとして登録されていません。")
        return

    # 🚧 専用チャンネルのガード処理
    is_admin_command = message.content in ["!admin", "!password-reset", "!github-repositories", "!supabase-table(quiz_score)", "!rank-toggle", "!add-quiz-channel", "!remove-quiz-channel", "!admin-remove"]
    is_general_command = message.content.startswith("!") and (not is_admin_command)
    is_currently_answering = (guild_id in server_current_quiz or guild_id in server_current_quiz_jh or guild_id in server_current_quiz_academic or user_id in user_status_dict)

    if message.guild and (is_general_command or is_currently_answering):
        guild_id_str = str(message.guild.id)
        target_channel_ids = server_settings.get(guild_id_str, {}).get("quiz_channel_ids", [])
        if target_channel_ids and (message.channel.id not in target_channel_ids):
            return 

    # 1. 一般知識クイズのチャット解答判定
    if guild_id in server_current_quiz and server_current_quiz[guild_id] is not None:
        chosen_quiz = server_current_quiz[guild_id]
        quiz_data = quiz_dictionary.get(chosen_quiz, {})
        correct_answer = quiz_data.get("answer", "")
        
        is_correct = False
        if isinstance(correct_answer, list):
            if message.content in correct_answer: is_correct = True
        else:
            if message.content == correct_answer: is_correct = True

        if is_correct:
            update_db_score(user_id, message.author.display_name, is_correct, message, member=message.author)
            await message.channel.send("<a:marugame:1556977377601527920> 正解！お見事です（一般知識）！🎉")
            await message.channel.send(f'<:hint:1556661937356546069> 【解説】\n{quiz_data.get("explanation", "解説はありません。")}')
        else:
            update_db_score(user_id, message.author.display_name, is_correct, message, member=message.author)
            await message.channel.send("不正解です。<:oh_no:1556661209116184686> もう一度挑戦してみてください！")
            await message.channel.send(f'<:hint:1556661937356546069> 【ヒント】\n{quiz_data.get("hint", "ヒントはありません。")}')
        del server_current_quiz[guild_id]
        return

    # 2. 中学クイズのチャット解答判定
    elif (user_status_dict.get(user_id) == "quiz_active" and guild_id in server_current_quiz_jh):
        quiz_data = server_current_quiz_jh[guild_id]
        correct_answer = quiz_data["answer"]
        is_correct = False
        if isinstance(correct_answer, list):
            if message.content in correct_answer: is_correct = True
        else:
            if message.content == correct_answer: is_correct = True

        if is_correct:
            update_db_score(user_id, message.author.display_name, is_correct, message, member=message.author)
            await message.channel.send("<a:marugame:1556977377601527920> ⭕ 正解！お見事です！ 🎉")
            await message.channel.send(f'💡 【解説】 \n{quiz_data["explanation"]}')
        else:
            update_db_score(user_id, message.author.display_name, is_correct, message, member=message.author)
            await message.channel.send(" 不正解です... <:oh_no:1556661209116184686> もう一度挑戦してみてください！")
            await message.channel.send(f'<:hint:1556661937356546069> 【ヒント】 \n{quiz_data["hint"]}')
        del server_current_quiz_jh[guild_id]
        if user_id in user_status_dict: del user_status_dict[user_id]
        return

    # 🛑 中断コマンド
    if message.content in ["!ストップ", "!stop", "!cancel"]:
        if guild_id in server_current_quiz: del server_current_quiz[guild_id]
        if guild_id in server_current_quiz_jh: del server_current_quiz_jh[guild_id]
        if guild_id in server_current_quiz_academic: del server_current_quiz_academic[guild_id]
        if user_id in user_status_dict: del user_status_dict[user_id]
        if user_id in user_selected_grade: del user_selected_grade[user_id]
        if user_id in user_selected_subject: del user_selected_subject[user_id]
        if user_id in user_selected_range: del user_selected_range[user_id]
        if user_id in user_selected_content: del user_selected_content[user_id]
        await message.channel.send("🛑 クイズ・メニュー選択を中断してリセットしました！")
        return
    
    # 📋 中学クイズ：段階的メニュー選択処理
    current_user_status = user_status_dict.get(user_id)

    if current_user_status == "select_grade":
        grade = message.content.strip()
        if grade in quiz_junior_high_school:
            user_selected_grade[user_id] = grade
            user_status_dict[user_id] = "select_subject"
            subjects = list(quiz_junior_high_school[grade].keys())
            subjects_text = "・".join(subjects)
            await message.channel.send(f"📂 **{grade}** が選択されました。\n**どの教科にしますか？**\n{subjects_text} の中から選んでください。")
        else:
            await message.channel.send("⚠️ 正しい学年を入力してください。")
        return

    if current_user_status == "select_subject":
        subject = message.content.strip()
        s_grade = user_selected_grade.get(user_id)
        available_subjects = quiz_junior_high_school[s_grade]
        if subject in available_subjects:
            user_selected_subject[user_id] = subject
            user_status_dict[user_id] = "select_range"
            ranges = list(available_subjects[subject].keys())
            ranges_text = "・".join(ranges)
            await message.channel.send(f"📂 {s_grade} ➔ **{subject}** が選択されました。\n**どの分野にしますか？**\n{ranges_text} の中から選んでください。")
        else:
            await message.channel.send("⚠️ 正しい教科を入力してください。")
        return

    if current_user_status == "select_range":
        range_name = message.content.strip()
        s_grade = user_selected_grade.get(user_id)
        s_subject = user_selected_subject.get(user_id)
        available_ranges = quiz_junior_high_school[s_grade][s_subject]
        if range_name in available_ranges:
            user_selected_range[user_id] = range_name
            user_status_dict[user_id] = "select_content"
            contents = list(available_ranges[range_name].keys())
            contents_text = "・".join(contents)
            await message.channel.send(f"📂 {s_grade} ➔ {s_subject} ➔ **{range_name}** が選択されました。\n**どの単元にしますか？**\n{contents_text} の中から選んでください。")
        else:
            await message.channel.send("⚠️ 正しい分野を入力してください。")
        return

    if current_user_status == "select_content":
        content_name = message.content.strip()
        s_grade = user_selected_grade.get(user_id)
        s_subject = user_selected_subject.get(user_id)
        s_range = user_selected_range.get(user_id)
        available_contents = quiz_junior_high_school[s_grade][s_subject][s_range]
        if content_name in available_contents:
            user_selected_content[user_id] = content_name
            questions = available_contents[content_name]
            if not questions:
                await message.channel.send("❌ この単元にはまだ問題が登録されていません。選択をリセットします。")
                if user_id in user_status_dict: del user_status_dict[user_id]
                return
                
            q_text = random.choice(list(questions.keys()))
            server_current_quiz_jh[guild_id] = questions[q_text]
            user_status_dict[user_id] = "quiz_active"
            await message.channel.send(f"🎯 出題範囲：{s_grade} ➔ {s_subject} ➔ {s_range} ➔ {content_name}\n\n**問題：{q_text}**")
        else:
            await message.channel.send("⚠️ 正しい単元を入力してください。")
        return

    # 個人成績確認
    if message.content == "!quiz_score":
        try:
            response = supabase.table("user_scores").select("*").eq("user_id", user_id).execute()
            user_data_list = getattr(response, "data", response)
            
            if user_data_list and isinstance(user_data_list, list) and len(user_data_list) > 0:
                data = user_data_list[0]  
                correct = data.get("correct_count", 0)
                wrong = data.get("wrong_count", 0)
                total = correct + wrong
                rate = (correct / total * 100) if total > 0 else 0
                is_enabled = data.get("is_rank_enabled", True)
                status_text = "🟢 オン" if is_enabled else "🔴 オフ"
                
                await message.channel.send(
                    f"📊 **{message.author.display_name} さんの成績**\n"
                    f"• 正解数: {correct} 回 ⭕\n"
                    f"• 不正解数: {wrong} 回 ❌\n"
                    f"• 正答率: {rate:.1f} %\n"
                    f"• 役職の自動付与: **{status_text}**"
                )
            else:
                await message.channel.send(f"📊 {message.author.display_name} さんは、まだクイズに挑戦していません！")
        except Exception as e:
            await message.channel.send("❌ スコアの取得中にエラーが発生しました。")
        return

    # 🛠️ 運営専用：GitHubリポジトリ確認コマンド
    if message.content == "!github-repositories":
        if user_id in ADMIN_USER_ID:
            await message.channel.send("リポジトリです。https://github.com/hironekoyade/my-discord-app")
        else:
            await message.channel.send("❌ このコマンドはBotの【運営メンバー】のみが実行できます。")
        return

    # 🛠️ 運営専用：Supabaseのスコア表
    if message.content == "!supabase-table(quiz_score)":
        if user_id in ADMIN_USER_ID:
            await message.channel.send("📊 **管理者用メニュー：全ユーザークイズ成績一覧を取得中...**")
            supabase_url_link = "https://supabase.com/dashboard/project/wazohoafsqhhvfigmzwu/editor/17606?schema=public"
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Supabase管理画面を開く", url=supabase_url_link, style=discord.ButtonStyle.link))
            
            try:
                response = supabase.table("user_scores").select("*").order("correct_count", desc=True).execute()
                if response.data and len(response.data) > 0:
                    table_text = "```\n【全ユーザークイズ成績ランキング】\n----------------------------------------------\n"
                    for row in response.data:
                        username = row.get("username", "Unknown")[:12]
                        correct = row.get("correct_count", 0)
                        wrong = row.get("wrong_count", 0)
                        total = correct + wrong
                        rate = (correct / total * 100) if total > 0 else 0
                        table_text += f"{username:<14} | {correct:<5} | {wrong:<6} | {rate:>5.1f}%\n"
                    table_text += "----------------------------------------------\n```"
                    await message.channel.send(table_text, view=view)
                else:
                    await message.channel.send("⚠️ 登録されているユーザーがまだ存在しません。", view=view)
            except Exception as e:
                await message.channel.send("❌ データ取得エラー。")
        else:
            await message.channel.send("❌ このコマンドはBotの【運営メンバー】のみが実行できます。")
        return

    # ⚙️ 役職昇進機能のオンオフ切り替え
    if message.content == "!rank-toggle" or message.content == "!server-rank-toggle":
        if is_bot_admin_or_server_manager:
            if message.guild is None: return
            guild_id_str = str(message.guild.id)
            global is_rank_role_enabled
            is_rank_role_enabled = not is_rank_role_enabled
            if guild_id_str not in server_settings: server_settings[guild_id_str] = {}
            server_settings[guild_id_str]["rank_role_enabled"] = is_rank_role_enabled
            save_server_settings()
            status_text = "【🟢有効（オン）】" if is_rank_role_enabled else "【🔴無効（オフ）】"
            await message.channel.send(f"⚙️ **サーバー管理設定：** このサーバーでのクイズ役職自動昇進システムを **{status_text}** に切り替えました。")
        return
    
    if message.content == "!ランク条件":
        embed = discord.Embed(title="🎖️ クイズ役職・昇進条件一覧", color=discord.Color.gold())
        embed.add_field(name="永世博士", value="累計 **120問** 正解", inline=False)
        embed.add_field(name="博士博士号", value="累計 **80問** 正解", inline=False)
        embed.add_field(name="物知り博士", value="累計 **50問** 正解", inline=False)
        embed.add_field(name="クイズ達人", value="累計 **30問** 正解", inline=False)
        embed.add_field(name="見習い学者", value="累計 **10問** 正解", inline=False)
        await message.channel.send(embed=embed)
        return

    if message.content == "!myrank-toggle":
        try:
            response = supabase.table("user_scores").select("*").eq("user_id", user_id).execute()
            current_status = True
            correct_count = 0
            wrong_count = 0
            if response.data and len(response.data) > 0:
                current_status = response.data[0].get("is_rank_enabled", True)
                correct_count = response.data[0].get("correct_count", 0)
                wrong_count = response.data[0].get("wrong_count", 0)
            next_status = not current_status
            supabase.table("user_scores").upsert({
                "user_id": user_id, "username": message.author.display_name,
                "correct_count": correct_count, "wrong_count": wrong_count,
                "is_rank_enabled": next_status, "updated_at": "now()"
            }).execute()
            status_text = "【🟢オン】" if next_status else "【🔴オフ】"
            await message.channel.send(f"👤 {message.author.mention} さん、あなたの自動付与設定を **{status_text}** に変更しました。")
        except Exception as e:
            await message.channel.send("❌ エラーが発生しました。")
        return

TOKEN = os.getenv("DISCORD_TOKEN")
client.run(TOKEN)
