import os
import random
import discord
import sympy as sp
import json
import string
from discord.ext import tasks  # 🌟 インポートはここに綺麗にまとめます

# 全てのインポートが終わった後に、変数を置きます！
user_scores = {}


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
        
        # 🎨 4つのボタンに別々の色（スタイル）を用意
        button_styles = [
            discord.ButtonStyle.primary,   # 青
            discord.ButtonStyle.success,   # 緑
            discord.ButtonStyle.secondary, # グレー
            discord.ButtonStyle.danger     # 赤
        ]
        
        for i, opt in enumerate(shuffled_options):
            current_style = button_styles[i % 4]
            btn = AcademicQuizButton(label=opt, view_obj=self, style=current_style)
            self.add_item(btn)

    # 🛠️ 【追加】ボタンが押されたときの正誤判定ロジック（これが抜けていました）
    async def process_choice(self, interaction: discord.Interaction, chosen_label: str):
        # すでにボタンが押された後なので、すべてのボタンを無効化（連打防止）
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        
        # メッセージを更新してボタンを押せなくする
        await interaction.message.edit(view=self)

        user_id = interaction.user.id
        is_correct = (chosen_label == self.correct_answer)

        if is_correct:
            # スコアの更新とロールチェックを実行
            update_db_score(user_id, interaction.user.display_name, is_correct, interaction.message, member=interaction.user)
            await interaction.channel.send(f"💡 {interaction.user.mention} **正解！お見事です（学術クイズ）！🎉**")
            await interaction.channel.send(f'<:hint:1556661937356546069> 【解説】\n{self.explanation}')
        else:
            update_db_score(user_id, interaction.user.display_name, is_correct, interaction.message, member=interaction.user)
            await interaction.channel.send(f"😢 {interaction.user.mention} **不正解です...。もう一度挑戦してみてください！**")
            await interaction.channel.send(f"正解は **【 {self.correct_answer} 】** でした！")
        
        # ビューの処理を完全に終了する
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

# 💡 1. デコレータを必ず付ける
@client.event
async def on_message(message):
    global current_quiz, current_quiz_junior_high, current_quiz_academic
    global user_status, selected_grade, selected_subject, selected_range, selected_content

    # 🔑 管理者認証ボタンを呼び出す新しいコマンド
    if message.content == "!admin":
        class AuthButtonView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60.0)
            
            @discord.ui.button(label="👑 管理者認証フォームを開く", style=discord.ButtonStyle.primary)
            async def open_modal(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                await button_interaction.response.send_modal(AdminAuthModal())

        await message.channel.send("以下のボタンを押して、パスワードを入力してください！", view=AuthButtonView())
        return

    if message.author == client.user:
        return

    # 🔄 【トリガー2】元の3人だけが使えるパスワード強制リセットコマンド
    if message.content == "!password-reset":
        if message.author.id in ORIGINAL_ADMINS:
            global ADMIN_PASSWORD
            
            # 🌟 ここも「英数字6文字」を生成するコードに書き換える！
            characters = string.ascii_letters + string.digits
            ADMIN_PASSWORD = "".join(random.choices(characters, k=6))
            
            try:
                await message.author.send(f"👑 パスワードを強制リセットしました：【{ADMIN_PASSWORD}】")
                await message.channel.send("🔄 創設者権限により、パスワードをランダムな新しい値に変更しました！（実行者にDMを送信しました）")
            except discord.Forbidden:
                await message.channel.send(f"🔄 パスワードを変更しました！")
        else:
            await message.channel.send("❌ エラー：この緊急コマンドはBotの【創設者3人】のみが実行できます。")
        return

    # 💡 2. 先頭が「!」のコマンドは、クイズの『解答中』の時だけ判定をスルーさせるように修正
    if message.content.startswith("!") and message.content not in ["!ストップ", "!stop", "!cancel"]:
        if current_quiz is None and current_quiz_junior_high is None and current_quiz_academic is None and user_status is None:
            pass 
        else:
            return  

    # 🎯 2. 一般知識クイズ解答判定 （末尾に message を追加）
    if current_quiz is not None:
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

    # 🎯 2.5 学術クイズ（テキスト形式）の解答判定 （末尾に message を追加）
    elif user_status == "academic_quiz_active" and current_quiz_academic is not None:
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

    # 🎯 3. 中学クイズ解答判定 （末尾に message を追加）
    elif user_status == "quiz_active" and current_quiz_junior_high is not None:
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
        
        if q_data["type"] == "choice":
            view = AcademicQuizView(q_data["answer"], q_data["explanation"], q_data["options"])
            
            await message.channel.send(
                f"🎓 **【学術クイズ - {chosen['category']}】**（4択ボタン形式）\n\n**問題：{q_text}**", 
                view=view
            )
            return

        elif q_data["type"] == "text":
            current_quiz_academic = q_data
            user_status = "academic_quiz_active"
            
            await message.channel.send(
                f"🎓 **【学術クイズ - {chosen['category']}】**（テキスト入力形式）\n\n**問題：{q_text}**"
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
                "• `!今日の運勢` : 今日の運勢を占う!\n"
                "• `!明日の運勢` : 明日の運勢を占う!!\n"
                "• `!サイコロ` : サイコロを振る `!サイコロ 100`のように上限を指定できるよ！\n"
                "`!サイコロ 2 3`のように振る回数も指定できるよ!\n"
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
        ADMIN_USER_ID = [
            1385634725460316273, 
            1551496753088561238,  
            1446830807007101102,
            1446830807007101102,
            1188811877447372881,
            1190487161875742781,
            1218614290542497967
        ]
        
        if message.author.id in ADMIN_USER_ID:
            await message.channel.send("リポジトリです。https://github.com")
        else:
            await message.channel.send("❌ このコマンドはBotの管理者のみが実行できます。")
        return

            # 🛠️ 管理者専用：Supabaseのスコア表＆管理画面ボタンを表示する独立コマンド
    if message.content == "!supabase-table(quiz_score)":
        ADMIN_USER_ID = [
            1385634725460316273,  
            1551496753088561238,   
            1446830807007101102,
            1188811877447372881,
            1190487161875742781,
            1218614290542497967
        ]
        
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

        ADMIN_USER_ID = [
            1385634725460316273,  
            1551496753088561238,   
            1446830807007101102,
            1188811877447372881,
            1190487161875742781,
            1218614290542497967
        ]

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

        if dice_count == 1:
            await message.channel.send(f"🎲 1 〜 {max_value} のサイコロを振りました！ 出た目は **【 {total} 】** です！")
        else:
            details = " ＋ ".join([f"[{r}]" for r in results])
            await message.channel.send(f"🎲 1 〜 {max_value} のサイコロを **{dice_count} 個** 振りました！\n内訳: {details}\n合計は **【 {total} 】** です！")
        return

    # 💬 8. 定型文・その他挨拶機能
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
    elif message.content == "!今日の運勢":
        results = ["大吉：今日は最高の1日になります！", "吉：良いことあるかも。", "凶：忘れ物に注意。"]
        await message.channel.send(random.choice(results))
        return
    elif message.content == "!明日の運勢":
        results = ["大吉：明日は最高の運勢になります！", "吉：明日は良いことあるかも？", "凶：忘れ物に注意..."]
        await message.channel.send(random.choice(results))
        return
    elif message.content == "!ランダムに州を選んで":
        await message.channel.send("州をランダムに選びます！選ばれたのは...")
        state = ["オセアニア州！", "アフリカ州！", "アジア州！", "ヨーロッパ州！", "北アメリカ州！", "南アメリカ州！"]
        await message.channel.send(random.choice(state))
        return
        # 🏅 役職の昇進条件を表示する単独コマンド
        # ⚙️【各サーバー管理者専用】役職昇進機能のオンオフ切り替えコマンド
    elif message.content == "!server-rank-toggle":
        if message.guild is None:
            await message.channel.send("❌ このコマンドはサーバー内でのみ実行できます。")
            return

        # 💡 開発者リストに入っているか、または「そのサーバーの管理者権限」を持っているかチェック
        is_server_admin = message.author.guild_permissions.administrator
        if (message.author.id in ADMIN_USER_ID) or is_server_admin:
            
            guild_id_str = str(message.guild.id)
            
            # 現在の状態を取得して反転させる
            current_status = is_rank_enabled_for_guild(message.guild.id)
            next_status = not current_status
            
            # サーバーごとの辞書を更新して保存
            if guild_id_str not in server_settings:
                server_settings[guild_id_str] = {}
            server_settings[guild_id_str]["rank_role_enabled"] = next_status
            save_server_settings()
            
            status_text = "【🟢有効（オン）】" if next_status else "【🔴無効（オフ）】"
            await message.channel.send(f"⚙️ **サーバー管理設定：** このサーバーでのクイズ役職自動昇進システムを **{status_text}** に切り替えました。")
        else:
            await message.channel.send("❌ この設定コマンドは、Botの管理者、またはこのサーバーの管理者権限（Administrator）を持つ人のみ実行できます。")
        return
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
    # 👤【一般ユーザー用】自分自身の役職自動付与をオンオフするコマンド
    elif message.content == "!myrank-toggle":
        user_id = message.author.id
        
        try:
            # データベースから現在の設定を取得
            response = supabase.table("user_scores").select("*").eq("user_id", user_id).execute()
            
            current_status = True  # デフォルト値
            correct_count = 0
            wrong_count = 0
            
            if response.data and len(response.data) > 0:
                current_status = response.data[0].get("is_rank_enabled", True)
                correct_count = response.data[0].get("correct_count", 0)
                wrong_count = response.data[0].get("wrong_count", 0)
            
            # 状態を反転させる
            next_status = not current_status
            
            # データベースを即座に更新
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

@client.event
async def on_ready():
    print(f"ログインしました: {client.user}")

TOKEN = os.getenv("DISCORD_TOKEN")
client.run(TOKEN)