import os
import random
import discord
import sympy as sp
import json
import string
import asyncio
import requests
from discord.ext import tasks  # 🌟 インポートはここに綺麗にまとめます

# 全てのインポートが終わった後に、変数を置きます！
user_scores = {}
# ==========================================
ROBLOX_API_KEY = os.getenv("ROBLOX_API_KEY", "あなたの実際のAPIキー、または.envから読み込み")
UNIVERSE_ID = "あなたのゲームのUNIVERSE_ID"
DATASTORE_NAME = "GameScores"

# ==========================================
# 🔑 管理者パスワード管理（複合システム版）
# ==========================================
ADMIN_PASSWORD = str(random.randint(1000, 9999))

# 👑 絶対に変わらない「元の3人（創設者）」の固定IDリスト
ORIGINAL_ADMINS = [
    1385634725460316273,
    1551496753088561238,  
    1446830807007101102
    ]

# 📝 動的に管理者が増えていくリスト（最初は3人からスタート）
ADMIN_USER_ID = ORIGINAL_ADMINS.copy()

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

@tasks.loop(hours=24)
async def auto_reset_password():
    global ADMIN_PASSWORD
    # 英大文字・小文字・数字をすべて混ぜたおもちゃ箱を作る
    characters = string.ascii_letters + string.digits

    # そこからランダムに6文字を選んで合体させる
    ADMIN_PASSWORD = "".join(random.choices(characters, k=6))
    print(f"【🔑定期リセット】24時間が経過したため、パスワードを自動変更しました: {ADMIN_PASSWORD}")

# Botが起動したときに、上のタイマーをスタートさせる
@client.event
async def on_ready():
    print(f"ログインしました: {client.user}")
    print(f"【🔑システムログ】初期パスワードは: {ADMIN_PASSWORD}")
    
    # ⏱️ タイマーがまだ動いていなければ、ここで起動する
    if not auto_reset_password.is_running():
        auto_reset_password.start()
        
    # 📊 【追加】ランキング自動発表タイマーを起動
    if not auto_announce_ranking.is_running():
        auto_announce_ranking.start()
# ==========================================
# 📊 定期ランキング自動発表システム（新機能）
# ==========================================
# 💡 hours=24 で24時間ごとに実行。毎日決まった時間に動かしたい場合は time 指定も可能です
@tasks.loop(hours=24)
async def auto_announce_ranking():
    # 💡 クイズが許可されているチャンネルが1つでもあれば、その最初のチャンネルに送信する
    # サーバー個別設定から、登録されているチャンネルIDを探す
    for guild_id_str, settings in server_settings.items():
        channel_ids = settings.get("quiz_channel_ids", [])
        if not channel_ids:
            # 古い設定（1つだけ保存する形式）の互換性チェック
            old_id = settings.get("quiz_channel_id")
            if old_id:
                channel_ids = [old_id]
        
        if not channel_ids:
            continue  # チャンネルが1つも登録されていないサーバーはスキップ

        # 許可されている最初のチャンネルを取得
        target_channel = client.get_channel(channel_ids[0])
        if target_channel is None:
            continue

        try:
            # Supabaseから正解数（correct_count）が多い順に上位5名を取得
            response = supabase.table("user_scores").select("*").order("correct_count", desc=True).limit(5).execute()
            
            if response.data and len(response.data) > 0:
                # 🎨 Discordに送るオシャレなランキングカード（Embed）を作成
                embed = discord.Embed(
                    title="🏆 【毎日発表】クイズ正解数ランキング・トップ5 🏆",
                    description="現在のサーバー内のクイズ強者たちの成績です！みんなも負けずに挑戦しよう！",
                    color=discord.Color.gold()
                )
                
                # メダル絵文字のリスト
                medals = ["🥇 1位", "🥈 2位", "🥉 3位", "✨ 4位", "✨ 5位"]
                
                for i, row in enumerate(response.data):
                    username = row.get("username", "名無し学者")
                    correct = row.get("correct_count", 0)
                    wrong = row.get("wrong_count", 0)
                    
                    # 順位に応じたメダルを割り当て
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

# 💡【追加】役職自動付与機能のオンオフスイッチ（True=オン、False=オフ）
is_rank_role_enabled = True  

# ==========================================
# ⚙️ サーバーごとの個別設定管理システム
# ==========================================
server_settings = {}

# ボット起動時に保存された設定ファイルを読み込む
if os.path.exists("server_settings.json"):
    with open("server_settings.json", "r", encoding="utf-8") as f:
        server_settings = json.load(f)

def save_server_settings():
    """設定をファイルに保存するヘルパー関数"""
    with open("server_settings.json", "w", encoding="utf-8") as f:
        json.dump(server_settings, f, ensure_ascii=False, indent=4)

def is_rank_enabled_for_guild(guild_id: int) -> bool:
    """そのサーバーで役職機能が有効かどうかを判定する（デフォルトはTrue=オン）"""
    str_id = str(guild_id)
    # サーバー個別の設定がなければ、初期値として True（オン）を返す
    return server_settings.get(str_id, {}).get("rank_role_enabled", True)

# ① 中学クイズ
quiz_junior_high_school = {}
if os.path.exists("quiz_junior_high_school.json"):
    with open("quiz_junior_high_school.json", "r", encoding="utf-8") as f:
        quiz_junior_high_school = json.load(f)

# ② 学術クイズ
quiz_academic = {}
if os.path.exists("quiz_academic.json"):
    with open("quiz_academic.json", "r", encoding="utf-8") as f:
        quiz_academic = json.load(f)

# ==========================================
# 💡 ボタンコンポーネントクラスを定義（フリーズ＆色固定 対策版）
# ==========================================
class AcademicQuizButton(discord.ui.Button):
    def __init__(self, label, view_obj, style):
        super().__init__(label=label, style=style)
        self.view_obj = view_obj

    async def callback(self, interaction: discord.Interaction):
        # 💡 Discordのフリーズ対策：「考え中...」のサインを出して3秒制限を解除
        await interaction.response.defer()
        # 👑 エラーの原因だった正誤判定処理を呼び出す
        await self.view_obj.process_choice(interaction, self.label)


class AcademicQuizView(discord.ui.View):
    def __init__(self, correct_answer, explanation, options):
        super().__init__(timeout=60.0) 
        self.correct_answer = correct_answer
        self.explanation = explanation
        
        shuffled_options = options.copy()
        random.shuffle(shuffled_options)
        
        # 🎨 ボタンに使う色（スタイル）のリスト
        button_styles = [
            discord.ButtonStyle.primary,   # 青
            discord.ButtonStyle.success,   # 緑
            discord.ButtonStyle.secondary, # グレー
            discord.ButtonStyle.danger,    # 赤
            discord.ButtonStyle.primary    # 5個目は青（またはお好みの色に！）
        ]
        
        # 💡 enumerateを使って、選択肢が何個あっても（5個でも）自動ですべてボタン化する
        for i, opt in enumerate(shuffled_options):
            # スタイルが足りなくなってもエラーにならないように % でループさせる
            current_style = button_styles[i % len(button_styles)]
            btn = AcademicQuizButton(label=opt, view_obj=self, style=current_style)
            self.add_item(btn)

    # ボタンが押されたときの正誤判定ロジック（変更なし）
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
        # 💡 【重要】メッセージを出し終えたので、Botのクイズ解答待ち状態を完全にクリアする
        global current_quiz, current_quiz_junior_high, current_quiz_academic, user_status
        current_quiz = None
        current_quiz_junior_high = None
        current_quiz_academic = None
        user_status = None

        self.stop()

class MultiChoiceQuizButton(discord.ui.Button):
    def __init__(self, label, view_obj, style):
        super().__init__(label=label, style=style)
        self.view_obj = view_obj

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.view_obj.process_choice(interaction, self)

# ==========================================
# 🎰 UI連動型：ボタン式ルーレットシステム（新機能）
# ==========================================
class RouletteButton(discord.ui.Button):
    def __init__(self):
        # 💡 初期状態は緑色のカッコいいボタン
        super().__init__(label="🎰 ルーレットをスタートする！", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        # ボタンを押した人以外の連打を防ぐため、即座に「考え中...」状態にする
        await interaction.response.defer()
        # ビュー側に「ボタンが押されたので演出を開始して」と命令する
        await self.view_obj.start_rotation(interaction)


class RouletteView(discord.ui.View):
    def __init__(self, options):
        super().__init__(timeout=120.0) # 2分間誰にも押されなければ自動終了
        self.options = options
        
        # ビューに起動ボタンを取り付ける
        self.button = RouletteButton()
        self.button.view_obj = self
        self.add_item(self.button)

    async def start_rotation(self, interaction: discord.Interaction):
        # 1. 誰かが押したら、二度と押せないようにボタンを無効化（ロック）する
        self.button.disabled = True
        self.button.label = "⏳ 抽選中..."
        self.button.style = discord.ButtonStyle.secondary
        await interaction.edit_original_response(view=self)

        # 2. 🎰 チャット欄でのドラムロール演出アニメーション
        status_msg = await interaction.channel.send(f"🔮 {interaction.user.mention} さんがルーレットを始動しました！")
        await asyncio.sleep(0.8)
        
        await status_msg.edit(content="🎰 ドゥルルルルルルルルルルルル……")
        await asyncio.sleep(1.2)
        await status_msg.edit(content="👀 くるくる…… ぴたっ…… 💡")
        await asyncio.sleep(0.8)

        # 3. 厳正なるランダム抽選
        chosen = random.choice(self.options)
        
        # 4. 🎉 最終結果をドカンとEmbedで発表！
        embed = discord.Embed(
            title="🎯 ルーレット抽選結果 🎯",
            description=f"抽選を実行した人：{interaction.user.mention}\n\n🥇 当選したのは……\n\n🏆 **【 {chosen} 】** です！！ 🎉",
            color=discord.Color.random()
        )
        embed.set_footer(text=f"選択肢の候補：{'、'.join(self.options)}")
        
        # 演出用メッセージを消去し、綺麗なカードを送信
        await status_msg.delete()
        await interaction.channel.send(embed=embed)
        
        # ビューを完全に終了
        self.stop()

    # 万が一、ボタンが押されずに2分経った場合の安全装置
    async def on_timeout(self):
        self.button.disabled = True
        self.button.label = "❌ 時間切れ（無効）"
        self.stop()

class MultiChoiceQuizView(discord.ui.View):
    def __init__(self, correct_answers, explanation, options):
        super().__init__(timeout=60.0)
        self.correct_answers = correct_answers  # 💡 正解のリスト（例: ["A", "B"]）
        self.explanation = explanation
        self.selected_buttons = []  # ユーザーが選択したボタンを記録
        
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
        # 💡 ここから下は「半差スペース8個分（赤線のさらに右）」に引っ込めて縦ラインを揃えます
        
        # 既に2つ選ばれて処理中の場合は何もしない
        if len(self.selected_buttons) >= 2 and button not in self.selected_buttons:
            return

        # 🔄 トグル処理：すでに選ばれているボタンをもう一度押したら「選択解除」にする
        if button in self.selected_buttons:
            self.selected_buttons.remove(button)
            button.style = discord.ButtonStyle.secondary  # グレーに戻す
        else:
            # 新しく選択されたら青色（Primary）に変える
            self.selected_buttons.append(button)
            button.style = discord.ButtonStyle.primary

        # 💡 【1つ目のボタンのとき】
        # interaction.response.defer() の後は、edit_original_response を使うのがDiscordの絶対ルール！
        if len(self.selected_buttons) < 2:
            await interaction.edit_original_response(view=self)
            return

        # 🚨 【2つのボタンが揃ったら】正誤判定に突入！
        # 連打や修正を防ぐためにすべてのボタンを無効化（ロック）
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
                # 正解のボタンは緑色（Success）に、不正解は赤色（Danger）に変えて答え合わせ
                if item.label in self.correct_answers:
                    item.style = discord.ButtonStyle.success
                elif item in self.selected_buttons:
                    item.style = discord.ButtonStyle.danger

        # 💡 ここも同様に edit_original_response でボタンの見た目を確定させます
        await interaction.edit_original_response(view=self)

        user_id = interaction.user.id
        # ユーザーが選んだ2つの選択肢（テキスト）のリスト
        user_choices = [btn.label for btn in self.selected_buttons]

        # 💡 2つの正解が両方とも含まれているかをチェック（順不同）
        is_all_correct = all(ans in user_choices for ans in self.correct_answers)

        # 🚨 ここを修正：True固定ではなく、実際の判定結果（is_all_correct）を正しく関数に引き渡します！
        if is_all_correct:
            # 見事両方正解なら、is_correct=True としてスコアを+1加算
            update_db_score(user_id, interaction.user.display_name, True, interaction.message, member=interaction.user)
            await interaction.channel.send(f"💡 {interaction.user.mention} **大正解！2つの選択肢を完璧に見抜きました！🎉**")
            await interaction.channel.send(f'<:hint:1556661937356546069> 【解説】\n{self.explanation}')
        else:
            # 1つでも間違えていたら、is_correct=False として不正解（wrong_count）を+1加算
            update_db_score(user_id, interaction.user.display_name, False, interaction.message, member=interaction.user)
            correct_text = " と ".join([f"【{a}】" for a in self.correct_answers])
            await interaction.channel.send(f"😢 {interaction.user.mention} **残念、不正解です...。**\n正解は {correct_text} でした！")
        
        # 【ゾンビ化防止ガード】解き終わったのでフラグをNoneにクリア
        global current_quiz, current_quiz_junior_high, current_quiz_academic, user_status
        current_quiz = None
        current_quiz_junior_high = None
        current_quiz_academic = None
        user_status = None

        self.stop()

# ==========================================
# 🔑 管理者認証用の入力フォーム（モーダル画面）
# ==========================================
class AdminAuthModal(discord.ui.Modal, title="管理者認証フォーム"):
    password_input = discord.ui.TextInput(
        label="6桁の英数字パスワードを入力してください", 
        placeholder="例: aB3x9Z",
        min_length=6,
        max_length=6
    )

    async def on_submit(self, interaction: discord.Interaction):
        global ADMIN_USER_ID
        user_id = interaction.user.id
        
        if self.password_input.value == ADMIN_PASSWORD:
            if user_id in ADMIN_USER_ID:
                await interaction.response.send_message("⚠️ あなたはすでに管理者リストに登録されています。", ephemeral=True)
            else:
                ADMIN_USER_ID.append(user_id)
                await interaction.response.send_message(f"👑 認証成功！管理者リストに追加されました！", ephemeral=True)
        else:
            await interaction.response.send_message("❌ パスワードが違います。認証に失敗しました。", ephemeral=True)

x, h = sp.symbols('x h')
f = x**2
definition_expr = (f.subs(x, x + h) - f) / h
derivative = sp.limit(definition_expr, h, 0)

# ③ 一般知識クイズ
quiz_dictionary = {}
if os.path.exists("quiz_dictionary.json"):
    with open("quiz_dictionary.json", "r", encoding="utf-8") as f:
        quiz_dictionary = json.load(f)

def update_db_score(user_id: int, username: str, is_correct: bool, message: discord.Message = None, member: discord.Member = None):
    """正解・不正解時にクラウドデータベースのカウントを+1し、個人の役職設定をチェックする関数"""
    try:
        response = supabase.table("user_scores").select("*").eq("user_id", user_id).execute()
        
        # ユーザー個人の設定（デフォルトはTrue=オン）
        user_rank_preference = True
        
        if response.data and len(response.data) > 0:
            current = response.data[0]
            correct = current["correct_count"] + (1 if is_correct else 0)
            wrong = current["wrong_count"] + (0 if is_correct else 1)
            user_rank_preference = current.get("is_rank_enabled", True)
        else:
            correct = 1 if is_correct else 0
            wrong = 0 if is_correct else 1

        # データをSupabaseへ保存
        supabase.table("user_scores").upsert({
            "user_id": user_id,
            "username": username,
            "correct_count": correct,
            "wrong_count": wrong,
            "is_rank_enabled": user_rank_preference,
            "updated_at": "now()"
        }).execute()
        print(f"【システムログ】{username} さんのデータをSupabaseに保存しました。（現在: {correct}問正解）")

        # 👑 役職昇進チェック
        if is_correct and message and message.guild and member:
            # Bot自身（client.user.id）が紛れ込んだ場合は完全に除外する
            if member.id == client.user.id:
                return

            server_enabled = is_rank_enabled_for_guild(message.guild.id)
            if server_enabled and user_rank_preference:
                
                async def assign_rank_role():
                    # 💡 条件判定をシンプルにし、現在の正確な正解数（correct）でチェック
                    role_name = None
                    if correct >= 120:
                        role_name = "永世博士"
                    elif correct >= 80:
                        role_name = "博士博士号"
                    elif correct >= 50:
                        role_name = "物知り博士"
                    elif correct >= 30:
                        role_name = "クイズ達人"
                    elif correct >= 10:
                        role_name = "見習い学者"
                    
                    if role_name:
                        role = discord.utils.get(message.guild.roles, name=role_name)
                        if role:
                            # 💡 ターゲットを message.author ではなく「member（ボタンを押した人）」に修正
                            if role not in member.roles:
                                try:
                                    await member.add_roles(role)
                                    await message.channel.send(f"🆙 **【ランクアップ！】** {member.mention} さんの累計正解数が **{correct}問** に達したため、**【{role_name}】** に昇進しました！ 🎉")
                                except discord.Forbidden:
                                    await message.channel.send(f"⚠️ 権限エラー: Botの役職順位が低いため、**【{role_name}】** を付与できませんでした。")
                                except Exception as e:
                                    print(f"ロール付与失敗: {e}")
                
                client.loop.create_task(assign_rank_role())

    except Exception as e:
        print(f"Supabase書き込み/ロール付与エラー: {e}")

@client.event
async def on_message(message):
    global current_quiz, current_quiz_junior_high, current_quiz_academic
    global user_status, selected_grade, selected_subject, selected_range, selected_content

    # 1. 自分のメッセージや他のBot（Dynoなど）は最初に完全無視
    if message.author.bot:
        return

    # 🔑 管理者認証ボタンコマンド
    if message.content == "!admin":
        class AuthButtonView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60.0)
            @discord.ui.button(label="👑 管理者認証フォームを開く", style=discord.ButtonStyle.primary)
            async def open_modal(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                await button_interaction.response.send_modal(AdminAuthModal())
        await message.channel.send("以下のボタンを押して、パスワードを入力してください！", view=AuthButtonView())
        return

    # 🔄 パスワード強制リセットコマンド
    if message.content == "!password-reset":
        if message.author.id in ORIGINAL_ADMINS:
            global ADMIN_PASSWORD
            characters = string.ascii_letters + string.digits
            ADMIN_PASSWORD = "".join(random.choices(characters, k=6))
            try:
                await message.author.send(f"👑 パスワードを強制リセットしました：【{ADMIN_PASSWORD}】")
                await message.channel.send("🔄 パスワードをランダムな新しい値に変更しました！（実行者にDM送信済）")
            except discord.Forbidden:
                await message.channel.send(f"🔄 パスワードを変更しました！")
        else:
            await message.channel.send("❌ エラー：この緊急コマンドはBotの【創設者3人】のみが実行できます。")
        return

    # 🛠️ 【新機能】専用チャンネルの「追加」コマンド（管理者用）
    if message.content == "!add-quiz-channel":
        is_server_admin = message.author.guild_permissions.administrator if message.guild else False
        
        # 💡 固定リストの代入を削除し、既存の ADMIN_USER_ID リストをそのまま参照
        if (message.author.id in ADMIN_USER_ID) or is_server_admin:
            if message.guild is None:
                await message.channel.send("❌ このコマンドはサーバー内でのみ実行できます。")
                return
            
            guild_id_str = str(message.guild.id)
            if guild_id_str not in server_settings:
                server_settings[guild_id_str] = {}
            
            # リスト形式で保存する（まだリストがない場合は新しく作る）
            if "quiz_channel_ids" not in server_settings[guild_id_str]:
                server_settings[guild_id_str]["quiz_channel_ids"] = []
                
            current_channels = server_settings[guild_id_str]["quiz_channel_ids"]
            
            if message.channel.id in current_channels:
                await message.channel.send("⚠️ このチャンネルはすでにクイズ専用チャンネルとして登録されています。")
            else:
                current_channels.append(message.channel.id)
                save_server_settings()
                await message.channel.send(f"🎯 **チャンネルを追加しました：** 以降、**{message.channel.mention}** でもクイズ機能が動作します！")
        else:
            await message.channel.send("❌ この設定コマンドは、Botの管理者、またはサーバー管理者のみ実行できます。")
        return

    # 🛠️ 【新機能】専用チャンネルの「削除」コマンド（管理者用）
    if message.content == "!remove-quiz-channel":
        is_server_admin = message.author.guild_permissions.administrator if message.guild else False
        
        # 💡 固定リストの代入を削除
        if (message.author.id in ADMIN_USER_ID) or is_server_admin:
            if message.guild is None:
                await message.channel.send("❌ このコマンドはサーバー内でのみ実行できます。")
                return
            
            guild_id_str = str(message.guild.id)
            current_channels = server_settings.get(guild_id_str, {}).get("quiz_channel_ids", [])
            
            if message.channel.id in current_channels:
                current_channels.remove(message.channel.id)
                save_server_settings()
                await message.channel.send(f"❌ **チャンネルを解除しました：** 以降、**{message.channel.mention}** ではクイズ機能が動作しません。")
            else:
                await message.channel.send("⚠️ このチャンネルはクイズ専用チャンネルとして登録されていません。")
        else:
            await message.channel.send("❌ この設定コマンドは、Botの管理者、またはサーバー管理者のみ実行できます。")
        return

    # 💡 2. 先頭が「!」のコマンドは、クイズの『解答中』の時だけ判定をスルー
    if message.content.startswith("!") and message.content not in ["!ストップ", "!stop", "!cancel"]:
        if current_quiz is None and current_quiz_junior_high is None and current_quiz_academic is None and user_status is None:
            pass 
        else:
            return  

    # 🎮 7.5. Robloxゲーム内ステータス照会コマンド（追加分）
    elif message.content.startswith("!roblox_score"):
        args = message.content.split()
        if len(args) < 2:
            await message.channel.send("❌ ユーザー名を指定してください。(例: `!roblox_score PlayerA`)")
            return
            
        target_player = args[1]
        await message.channel.send(f"🔍 Robloxから {target_player} さんのデータを照会中...")

        # Roblox Open Cloud DataStore API のURL
        url = f"https://roblox.com{UNIVERSE_ID}/standard-datastores/datastore/entries/entry"
        
        headers = {
            "x-api-key": ROBLOX_API_KEY
        }
        params = {
            "datastoreName": DATASTORE_NAME,
            "entryKey": target_player
        }

        try:
            # 💡 requestsを非同期のBotを邪魔しないように実行（または import requests を一番上で行ってください）
            import requests
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                roblox_data = response.json()
                score = roblox_data.get("Score", 0)
                level = roblox_data.get("Level", 1)
                
                await message.channel.send(
                    f"🎮 **{target_player} さんのRobloxゲーム内ステータス**\n"
                    f"• 現在のレベル: **Lv.{level}**\n"
                    f"• 獲得スコア: **{score} 点** 🏆"
                )
            elif response.status_code == 404:
                await message.channel.send(f"⚠️ {target_player} さんのデータはゲーム内に見つかりませんでした。")
            else:
                await message.channel.send("❌ Roblox APIとの通信に失敗しました。")
        except Exception as e:
            print(f"Robloxデータ取得エラー: {e}")
            await message.channel.send("❌ エラーが発生しました。")
        return
    # 🚧 【鉄壁のガード：指定チャンネル完全限定版】
    # 管理者用コマンド以外のすべての一般コマンド・機能を、登録された専用部屋だけでしか動かないように一括制限します！
    
    # 🔑 1. どこでも実行できてほしい「管理者用・設定用コマンド」をリストアップして除外する
    is_admin_command = message.content in [
        "!admin", "!password-reset", "!github-repositories", 
        "!supabase-table(quiz_score)", "!rank-toggle", 
        "!add-quiz-channel", "!remove-quiz-channel"
    ]

    # 🔑 2. 先頭に「!」がついている一般コマンド、またはクイズ解答中の場合を制限対象にする
    is_general_command = message.content.startswith("!") and (not is_admin_command)
    is_currently_answering = (current_quiz is not None) or (user_status in ["quiz_active", "academic_quiz_active", "select_grade", "select_subject", "select_range", "select_content"])

    # 💡 サーバー（Guild）内で、一般コマンドが打たれたかクイズ中のときだけチェックを実行
    if message.guild and (is_general_command or is_currently_answering):
        guild_id_str = str(message.guild.id)
        target_channel_ids = server_settings.get(guild_id_str, {}).get("quiz_channel_ids", [])
        
        # 専用チャンネルが1つ以上登録されている場合のみガードを発動
        if target_channel_ids:
            # 今発言されたチャンネルが、登録されている専用部屋リストに「含まれていない」場合は即座に終了（無視）
            if message.channel.id not in target_channel_ids:
                return 

    # ==========================================
    # 🎯 クイズの解答判定エリア（出題中のみ実行するように厳格化）
    # ==========================================

    # 1. 一般知識クイズの解答判定
    if current_quiz is not None:
        # メッセージ送信者がBot自身、または他のBot（Dynoなど）の場合は完全に無視する
        if message.author.bot:
            return

        quiz_data = quiz_dictionary[current_quiz]
        is_correct = False
        if isinstance(quiz_data["answer"], list):
            if message.content in quiz_data["answer"]:
                is_correct = True
        else:
            if message.content == quiz_data["answer"]:
                is_correct = True

        user_id = message.author.id
        if is_correct:
            update_db_score(user_id, message.author.display_name, is_correct, message, member=message.author)
            await message.channel.send("<a:marugame:1556977377601527920> 正解！お見事です（一般知識）！🎉")
            await message.channel.send(f'<:hint:1556661937356546069> 【解説】\n{quiz_data["explanation"]}')
            current_quiz = None  
        else:
            update_db_score(user_id, message.author.display_name, is_correct, message, member=message.author)
            await message.channel.send("不正解です。<:oh_no:1556661209116184686> もう一度挑戦してみてください！")
            await message.channel.send(f'<:hint:1556661937356546069> 【ヒント】\n{quiz_data["hint"]}')
        return

    # 2. 学術クイズ（テキスト入力形式）の解答判定
    elif user_status == "academic_quiz_active" and current_quiz_academic is not None:
        if message.author.bot:
            return

        quiz_data = current_quiz_academic
        is_correct = False
        if isinstance(quiz_data["answer"], list):
            if message.content in quiz_data["answer"]:
                is_correct = True
        else:
            if message.content == quiz_data["answer"]:
                is_correct = True

        user_id = message.author.id
        if is_correct:
            update_db_score(user_id, message.author.display_name, is_correct, message, member=message.author)
            await message.channel.send("<a:marugame:1556977377601527920> 正解！お見事です！🎉📚")
            await message.channel.send(f'<:hint:1556661937356546069> 【解説】\n{quiz_data["explanation"]}')
            current_quiz_academic = None  
            user_status = None
        else:
            update_db_score(user_id, message.author.display_name, is_correct, message, member=message.author)
            await message.channel.send("不正解です😢...<:oh_no:1556661209116184686> もう一度挑戦してみてください！")
            await message.channel.send(f'<:hint:1556661937356546069> 【ヒント】\n{quiz_data["hint"]}')
        return

    # 3. 中学クイズの解答判定
    elif user_status == "quiz_active" and current_quiz_junior_high is not None:
        if message.author.bot:
            return

        is_correct = False
        quiz_data = current_quiz_junior_high
        if isinstance(quiz_data["answer"], list):
            if message.content in quiz_data["answer"]:
                is_correct = True
        else:
            if message.content == quiz_data["answer"]:
                is_correct = True

        user_id = message.author.id
        if is_correct:
            update_db_score(user_id, message.author.display_name, is_correct, message, member=message.author)
            await message.channel.send("<a:marugame:1556977377601527920> ⭕ 正解！お見事です！ 🎉")
            await message.channel.send(f'💡 【解説】 \n{quiz_data["explanation"]}')
            current_quiz_junior_high = None  
            user_status = None  
        else:
            update_db_score(user_id, message.author.display_name, is_correct, message, member=message.author)
            await message.channel.send(" 不正解です... <:oh_no:1556661209116184686> もう一度挑戦してみてください！")
            await message.channel.send(f'<:hint:1556661937356546069> 【ヒント】 \n{quiz_data["hint"]}')
        return

    # 🛑 1. 中断コマンド
    # 💡 クイズではない独立したコマンド判定なので、クイズ判定の「外側（一番後ろ）」へ安全に退避させました
    if message.content in ["!ストップ", "!stop", "!cancel"]:
        user_status = None
        current_quiz = None
        current_quiz_junior_high = None
        current_quiz_academic = None
        selected_grade = None    
        selected_subject = None
        selected_range = None    
        selected_content = None  
        await message.channel.send("🛑 クイズ・メニュー選択を中断してリセットしました！")
        return
    
    # 📋 4. 中学クイズ：段階的メニュー選択処理
    if user_status == "select_grade":
        grade = message.content.strip()
        if grade in quiz_junior_high_school:
            selected_grade = grade
            user_status = "select_subject"
            subjects = list(quiz_junior_high_school[selected_grade].keys())
            subjects_text = "・".join(subjects)
            await message.channel.send(
                f"📂 **{selected_grade}** が選択されました。\n"
                f"**どの教科にしますか？**\n"
                f"{subjects_text} の中から選んでください。"
            )
        else:
            await message.channel.send(f"⚠️ 正しい学年を入力してください。")
        return

    if user_status == "select_subject":
        subject = message.content.strip()
        available_subjects = quiz_junior_high_school[selected_grade]
        if subject in available_subjects:
            selected_subject = subject
            user_status = "select_range"
            ranges = list(available_subjects[selected_subject].keys())
            ranges_text = "・".join(ranges)
            await message.channel.send(
                f"📂 {selected_grade} ➔ **{selected_subject}** が選択されました。\n"
                f"**どの分野にしますか？**\n"
                f"{ranges_text} の中から選んでください。"
            )
        else:
            await message.channel.send(f"⚠️ 正しい教科を入力してください。")
        return

    if user_status == "select_range":
        range_name = message.content.strip()
        available_ranges = quiz_junior_high_school[selected_grade][selected_subject]
        if range_name in available_ranges:
            selected_range = range_name
            user_status = "select_content"
            contents = list(available_ranges[selected_range].keys())
            contents_text = "・".join(contents)
            await message.channel.send(
                f"📂 {selected_grade} ➔ {selected_subject} ➔ **{selected_range}** が選択されました。\n"
                f"**どの単元にしますか？**\n"
                f"{contents_text} の中から選んでください。"
            )
        else:
            await message.channel.send(f"⚠️ 正しい分野を入力してください。")
        return

    if user_status == "select_content":
        content_name = message.content.strip()
        available_contents = quiz_junior_high_school[selected_grade][selected_subject][selected_range]
        if content_name in available_contents:
            selected_content = content_name
            questions = available_contents[selected_content]
            if not questions:
                await message.channel.send("❌ この単元にはまだ問題が登録されていません。選択をリセットします。")
                user_status = None
                return
                
            q_text = random.choice(list(questions.keys()))
            current_quiz_junior_high = questions[q_text]
            user_status = "quiz_active"
            await message.channel.send(
                f"🎯 出題範囲：{selected_grade} ➔ {selected_subject} ➔ {selected_range} ➔ {selected_content}\n\n"
                f"**問題：{q_text}**"
            )
        else:
            await message.channel.send(f"⚠️ 正しい単元を入力してください。")
        return

    # 🚀 5. コマンド受付
    # 🚀 学術特化クイズコマンド
    if message.content == "!学術クイズ":
        all_academic_q = []
        for category, questions in quiz_academic.items():
            for q_text, q_data in questions.items():
                all_academic_q.append({"text": q_text, "data": q_data, "category": category})
        
        chosen = random.choice(all_academic_q)
        q_text = chosen["text"]
        q_data = chosen["data"]
        
        # 💡 データの種類に応じてビューを切り替える
        if q_data["type"] == "choice":
            view = AcademicQuizView(q_data["answer"], q_data["explanation"], q_data["options"])
            # 「学術クイズ」という固定文字を、JSONのカテゴリ名（ chosen['category'] ）に動的変更！
            await message.channel.send(f"🎯 **【クイズ - {chosen['category']}】**（4択ボタン形式）\n\n**問題：{q_text}**", view=view)
            return


        elif q_data["type"] == "multi_choice":
            view = MultiChoiceQuizView(q_data["answer"], q_data["explanation"], q_data["options"])
            # ここもどんなジャンル（ゲーム、地理、アニメ等）でもマッチする表記に修正！
            await message.channel.send(
                f"🔥 **【特別クイズ - {chosen['category']}】**（5択・2つ選択形式）\n\n"
                f"**問題：{q_text}**\n\n"
                f"⚠️ **【ルール】正しいと思う選択肢のボタンを【2つ】押してください！**", 
                view=view
            )
            return


    if message.content == "!中学クイズ":
        user_status = "select_grade"
        grade_text = "・".join(quiz_junior_high_school.keys())
        await message.channel.send(f"**何年生のクイズにしますか？**\n{grade_text}の中から選んでください。")
        return

    if message.content == "!中学クイズおまかせ":
        all_questions = []
        for grade, subjects in quiz_junior_high_school.items():
            for subject, ranges in subjects.items():
                for range_name, contents in ranges.items():
                    for content_name, questions in contents.items():
                        for q_text, q_data in questions.items():
                            all_questions.append({
                                "text": q_text,
                                "data": q_data,
                                "info": f"【{grade} ➔ {subject} ➔ {range_name} ➔ {content_name}】"
                            })
        if not all_questions:
            await message.channel.send("❌ 現在、中学生用のクイズが1問も登録されていません。")
            return
        chosen = random.choice(all_questions)
        current_quiz_junior_high = chosen["data"]
        user_status = "quiz_active"  
        await message.channel.send(f"🎲 すべての範囲からランダムに問題を出します！\n💡 出題範囲：{chosen['info']}\n\n**問題：{chosen['text']}**")
        return

    if message.content == "!一般クイズ":
        await message.channel.send("【一般知識クイズ】を出します！")
        chosen_quiz = random.choice(list(quiz_dictionary.keys()))
        current_quiz = chosen_quiz
        await message.channel.send(chosen_quiz)
        return

    if message.content == "!quiz_score":
        user_id = message.author.id
        
        try:
            response = supabase.table("user_scores").select("*").eq("user_id", user_id).execute()
            if response.data and len(response.data) > 0:
                data = response.data[0]  
                correct = data["correct_count"]
                wrong = data["wrong_count"]
                total = correct + wrong
                rate = (correct / total * 100) if total > 0 else 0
                
                # 💡【追加】データベースからオンオフ設定を読み込んで、表示用のテキストを作る
                is_enabled = data.get("is_rank_enabled", True)
                status_text = "🟢 受け取る（オン）" if is_enabled else "🔴 受け取らない（オフ）"
                
                # 💡 メッセージの一番下に「現在の設定状況」を書き足す
                await message.channel.send(
                    f"📊 **{message.author.display_name} さんのクイズ成績（クラウド保存）**\n"
                    f"• 正解数: {correct} 回 ⭕\n"
                    f"• 不正解数: {wrong} 回 ❌\n"
                    f"• 正答率: {rate:.1f} %\n"
                    f"• 役職の自動付与: **{status_text}**" # 👈 ここを追加！
                )
            else:
                await message.channel.send(f"📊 {message.author.display_name} さんは、まだクイズに挑戦していません！")
        except Exception as e:
            await message.channel.send("❌ スコアの取得中にエラーが発生しました。")
            print(f"Supabase読み込みエラー: {e}")
        return
    
    # 📋 6. ヘルプ機能
    if message.content == "!help-hironekobot":
        quiz_menu_text = ""
        for grade, subjects in quiz_junior_high_school.items():
            quiz_menu_text += f"📂 **{grade}**\n"
            for subject, ranges in subjects.items():
                range_list = []
                for r_name, c_dict in ranges.items():
                    c_names = "、".join(c_dict.keys()) if c_dict.keys() else "設定なし"
                    range_list.append(f"{r_name} ({c_names})")
                range_info = "、".join(range_list) if range_list else "（未登録）"
                quiz_menu_text += f" ┗ 🔹 **{subject}** ➔ 範囲: {range_info}\n"
            quiz_menu_text += "\n"

        embed = discord.Embed(
            title="🤖 クイズボット コマンド・プログラム一覧表",
            description="試験勉強やクイズを楽しむためのコマンド一覧です！",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="📚 クイズメニュー",
            value=f"• `!中学クイズ` : メニューを選んで出題\n• `!中学クイズおまかせ` : 全範囲から完全ランダム出題\n• `!学術クイズ` : 高度な専門クイズに挑戦！\n\n【現在登録されているメニュー】\n{quiz_menu_text}",
            inline=False
        )
        embed.add_field(
            name="🛑 クイズを途中でやめたいとき",
            value="• `!ストップ` / `!stop` / `!cancel` (いつでもリセット可能)",
            inline=False
        )
        embed.add_field(
            name="🎲 その他の機能",
            value=(
                "• `!一般クイズ` : 一般知識クイズに挑戦\n"
                "• `!今日の運勢` / `!明日の運勢` : 今日の運勢・明日の運勢を占う!\n"
                "• `!サイコロ` : サイコロを振る（例: `!サイコロ 100` / `!サイコロ 6 5`）\n"
                "• `!ルーレット` : 🎰 **【大人気】ボタン式の本格演出ルーレット！**\n"
                "  ┗ 💬 自由入力： `!ルーレット 焼肉 寿司 ラーメン` （項目をスペース区切り）\n"
                "  ┗ 🔢 数値指定： `!ルーレット 100` （1〜100からランダムに自動抽選）\n"
                "• `!ランダムに州を選んで` : 世界の6大州をランダムに選択\n"
                "• `!こんにちは` / `!おはよう` / `!こんばんは` / `!おやすみ`\n"
                "• `!quiz_score` : クイズのスコアを表示！\n"
                "• `!myrank-toggle` : 自分のクイズ正解数による役職付与を有効化/無効化\n"
            ),
            inline=False
        )
        embed.add_field(
            name="🛠️ 管理者向け機能(実行は管理専用サーバーでしてください)",
            value=("• `!github-repositories` : 開発用GitHubリポジトリのURLを確認する\n"
                   "• `!supabase-table(quiz_score)` : 全員のクイズの成績を確認する\n"
                   "• `!server-rank-toggle` : サーバーのクイズ正解数による役職付与を有効化/無効化\n"
                   "• `!add-quiz-channel` : クイズ用サーバーを選択(このコマンドの実行は選択したいサーバーで行ってください)\n"
                   "• `!remove-quiz-channel` : クイズ用サーバーを削除(このコマンドの実行は選択したいサーバーで行ってください)\n"
            ),
            inline=False
        )
        embed.add_field(
            name="🫆 運営向けパスワード機能(実行は運営サーバーでしてください)",
            value=("• `!password-reset` : botのパスワード変更(あまりに強力なので私にしか権限付与してません)\n"
            ),
            inline=False
        )
        
        embed.set_footer(text="大文字・小文字の打ち間違いに注意してね！")
        await message.channel.send(embed=embed)
        return

    # 🛠️ 管理者専用：GitHubリポジトリ確認コマンド
    if message.content == "!github-repositories":
        # 💡 固定リストの代入を削除
        if message.author.id in ADMIN_USER_ID:
            await message.channel.send("リポジトリです。https://github.com")
        else:
            await message.channel.send("❌ このコマンドはBotの管理者のみが実行できます。")
        return

    # 🛠️ 管理者専用：Supabaseのスコア表＆管理画面ボタンを表示する独立コマンド
    if message.content == "!supabase-table(quiz_score)":
        # 💡 固定リストの代入を削除
        if message.author.id in ADMIN_USER_ID:
            await message.channel.send("📊 **管理者用メニュー：全ユーザークイズ成績一覧を取得中...**")
            
            # Supabaseの管理画面に直接飛べるURLボタンを作成
            supabase_url_link = "https://supabase.com/dashboard/project/wazohoafsqhhvfigmzwu/editor/17606?schema=public"
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Supabase管理画面を開く", url=supabase_url_link, style=discord.ButtonStyle.link))
            
            try:
                # 全データを正解数（correct_count）が多い順にソートして取得
                response = supabase.table("user_scores").select("*").order("correct_count", desc=True).execute()
                
                if response.data and len(response.data) > 0:
                    table_text = "```\n"
                    table_text += "【全ユーザークイズ成績ランキング】\n"
                    table_text += "----------------------------------------------\n"
                    table_text += f"{'ユーザー名':<16} | {'正解':<4} | {'不正解':<4} | {'正答率':<6}\n"
                    table_text += "----------------------------------------------\n"
                    
                    for row in response.data:
                        username = row.get("username", "Unknown")[:12]
                        correct = row.get("correct_count", 0)
                        wrong = row.get("wrong_count", 0)
                        total = correct + wrong
                        rate = (correct / total * 100) if total > 0 else 0
                        
                        table_text += f"{username:<14} | {correct:<5} | {wrong:<6} | {rate:>5.1f}%\n"
                    
                    table_text += "----------------------------------------------\n"
                    table_text += "```"
                    
                    # スコア表と一緒に、管理画面に飛ぶボタン（view）を送信
                    await message.channel.send(table_text, view=view)
                else:
                    await message.channel.send("⚠️ データベースに登録されているユーザーがまだ存在しません。", view=view)
            except Exception as e:
                await message.channel.send("❌ クラウドデータの取得中にエラーが発生しました。")
                print(f"管理者スコア一覧取得エラー: {e}")
        else:
            await message.channel.send("❌ このコマンドはBotの管理者のみが実行できます。")
        return

    # ⚙️【各サーバー管理者専用】役職昇進機能のオンオフ切り替えコマンド（修正＆統合）
    if message.content == "!rank-toggle":
        if message.guild is None:
            await message.channel.send("❌ このコマンドはサーバー内でのみ実行できます。")
            return

        # 💡 固定リストの代入を削除
        is_server_admin = message.author.guild_permissions.administrator
        if (message.author.id in ADMIN_USER_ID) or is_server_admin:
            guild_id_str = str(message.guild.id)
            
            global is_rank_role_enabled
            is_rank_role_enabled = not is_rank_role_enabled
            
            if guild_id_str not in server_settings:
                server_settings[guild_id_str] = {}
            server_settings[guild_id_str]["rank_role_enabled"] = is_rank_role_enabled
            save_server_settings()
            
            status_text = "【🟢有効（オン）】" if is_rank_role_enabled else "【🔴無効（オフ）】"
            await message.channel.send(f"⚙️ **サーバー管理設定：** このサーバーでのクイズ役職自動昇進システムを **{status_text}** に切り替えました。")
        else:
            await message.channel.send("❌ この設定コマンドは、Botの管理者、またはこのサーバーの管理者権限（Administrator）を持つ人のみ実行できます。")
        return
    
    # 🎲 7. サイコロ機能
    if message.content.startswith("!サイコロ"):
        args = message.content.split()
        MAX_DICE_LIMIT = 30
        MAX_VALUE_LIMIT = 1000000  
        max_value = 6   
        dice_count = 1  
        
        if len(args) == 1:
            pass
        elif len(args) == 2:
            if args[1].isdigit():
                max_value = int(args[1])
            else:
                await message.channel.send("❌ 上限数は数字で入力してください。 (例: `!サイコロ 100`)")
                return
        elif len(args) == 3:
            if args[1].isdigit() and args[2].isdigit():
                max_value = int(args[1])
                dice_count = int(args[2])
            else:
                await message.channel.send("❌ 上限数と個数はどちらも数字で入力してください。 (例: `!サイコロ 6 5`)")
                return
        else:
            await message.channel.send("❌ 引数が多すぎます。 (例: `!サイコロ 6 5`)")
            return

        if max_value < 1 or dice_count < 1:
            await message.channel.send("❌ 上限数と個数は 1 以上を指定してください。")
            return
        if max_value > MAX_VALUE_LIMIT:
            await message.channel.send(f"⚠️ **これ以上の大きな数値（面数）は指定できません！** 最大: {MAX_VALUE_LIMIT}")
            return
        if dice_count > MAX_DICE_LIMIT:
            await message.channel.send(f"⚠️ **これ以上の個数は同時に振ることができません！** 最大: {MAX_DICE_LIMIT}個")
            return

        results = [random.randint(1, max_value) for _ in range(dice_count)]
        total = sum(results)

        # （省略）... !サイコロ機能の一番最後の部分
        if dice_count == 1:
            await message.channel.send(f"🎲 1 〜 {max_value} のサイコロを振りました！ 出た目は **【 {total} 】** です！")
        else:
            details = " ＋ ".join([f"[{r}]" for r in results])
            await message.channel.send(f"🎲 1 〜 {max_value} のサイコロを **{dice_count} 個** 振りました！\n内訳: {details}\n合計は **【 {total} 】** です！")
            return  # 👈 頭に半角スペースを4つ足して、他の行と縦のラインを綺麗に揃えます！

    # ==========================================
    # 🎰 【ここを追加・修正！】ルーレット機能コマンドの本体
    # ==========================================
    if message.content.startswith("!ルーレット"):
        args = message.content.split()
        
        # 1. 引数がない場合（使い方の説明）
        if len(args) == 1:
            await message.channel.send(
                "❌ 項目を指定してください！\n"
                "• 自由入力： `!ルーレット 焼肉 寿司 ラーメン` （スペース区切り）\n"
                "• 数値指定： `!ルーレット 100` （1〜100から自動抽選）"
            )
            return

        options = []
        # 2. 数値指定の場合（例: !ルーレット 100）
        if len(args) == 2 and args[1].isdigit():
            max_num = int(args[1])
            if max_num < 2:
                await message.channel.send("❌ 2以上の数値を指定してください。")
                return
            options = [str(i) for i in range(1, max_num + 1)]
        # 3. スペース区切りで項目が並んでいる場合
        else:
            options = args[1:]

        # すでに実装されているボタン式ルーレットのViewを呼び出す
        view = RouletteView(options)
        await message.channel.send("🎰 ボタンを押すとルーレットの抽選が始まります！", view=view)
        return

    # 💬 8. 定型文・その他挨拶機能（ここへ続く）
    if message.content == "!こんにちは":
        await message.channel.send("こんにちは！")
        return
    elif message.content == "!おはよう":
        await message.channel.send("おはようございます！")
        return
    elif message.content == "!こんばんは":
        await message.channel.send("こんばんは！")
        return
    elif message.content == "!おやすみ":
        await message.channel.send("おやすみなさい！")
        return

    # 🟢 役職自動昇進のオンオフコマンド（インデントを完璧に修正）
    elif message.content == "!server-rank-toggle":
        if message.guild is None:
            await message.channel.send("❌ このコマンドはサーバー内でのみ実行できます。")
            return

        is_server_admin = message.author.guild_permissions.administrator
        if (message.author.id in ADMIN_USER_ID) or is_server_admin:
            guild_id_str = str(message.guild.id)
            
            current_status = is_rank_enabled_for_guild(message.guild.id)
            next_status = not current_status
            
            if guild_id_str not in server_settings:
                server_settings[guild_id_str] = {}
            server_settings[guild_id_str]["rank_role_enabled"] = next_status
            save_server_settings()
            
            status_text = "【🟢有効（オン）】" if next_status else "【🔴無効（オフ）】"
            await message.channel.send(f"⚙️ **サーバー管理設定：** このサーバーでのクイズ役職自動昇進システムを **{status_text}** に切り替えました。")
        else:
            await message.channel.send("❌ この設定コマンドは、Botの管理者、またはこのサーバーの管理者権限（Administrator）を持つ人のみ実行できます。")
        return

    # 🎖️ クイズのランク条件表示コマンド
    elif message.content == "!ランク条件":
        embed = discord.Embed(
            title="🎖️ クイズ役職・昇進条件一覧",
            description="Supabaseに保存された累計正解数で自動昇進します！",
            color=discord.Color.gold()
        )
        embed.add_field(name="⁉️ 永世博士", value="累計 **120問** 正解", inline=False)
        embed.add_field(name="🪪 博士博士号", value="累計 **80問** 正解", inline=False)
        embed.add_field(name="🎓 物知り博士", value="累計 **50問** 正解", inline=False)
        embed.add_field(name="⚔️ クイズ達人", value="累計 **30問** 正解", inline=False)
        embed.add_field(name="📝 見習い学者", value="累計 **10問** 正解", inline=False)
        embed.set_footer(text="現在の自分のスコアは !quiz_score で確認できるよ！")
        await message.channel.send(embed=embed)
        return

    # 👤 個人用の役職付与オンオフ切り替えコマンド
    elif message.content == "!myrank-toggle":
        user_id = message.author.id
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
                "user_id": user_id,
                "username": message.author.display_name,
                "correct_count": correct_count,
                "wrong_count": wrong_count,
                "is_rank_enabled": next_status,
                "updated_at": "now()"
            }).execute()
            
            status_text = "【🟢受け取る（オン）】" if next_status else "【🔴受け取らない（オフ）】"
            await message.channel.send(f"👤 {message.author.mention} さん、あなたのクイズ役職自動付与設定を **{status_text}** に変更しました。")
        except Exception as e:
            await message.channel.send("❌ 設定の変更中にエラーが発生しました。")
            print(f"個人設定切り替えエラー: {e}")
        return

TOKEN = os.getenv("DISCORD_TOKEN")
client.run(TOKEN)