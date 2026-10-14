import os
import random
import discord
import sympy as sp
import json
user_scores = {}
from discord.ext import tasks  # 🌟 一番上のインポート欄に追加
import random

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
    ADMIN_PASSWORD = str(random.randint(1000, 9999))
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
    # ⚠️ 一番最初の「青にする処理」自体を、ここで完全に書き換えます！
    def __init__(self, label, view_obj, style):
        # ここを style=style にすることで、最初から絶対に指定した色になります
        super().__init__(label=label, style=style)
        self.view_obj = view_obj

    async def callback(self, interaction: discord.Interaction):
        # 💡 Discordのフリーズ対策：ボタンを押されたら、即座に「考え中...」のサインを出して3秒制限を解除する
        await interaction.response.defer()
        
        # その後、正誤判定のメッセージを送る
        await self.view_obj.process_choice(interaction, self.label)


class AcademicQuizView(discord.ui.View):
    def __init__(self, correct_answer, explanation, options):
        super().__init__(timeout=60.0) 
        self.correct_answer = correct_answer
        self.explanation = explanation
        
        shuffled_options = options.copy()
        random.shuffle(shuffled_options)
        
        # 🎨 4つのボタンに別々の色（スタイル）を用意する
        button_styles = [
            discord.ButtonStyle.primary,   # 青
            discord.ButtonStyle.success,   # 緑
            discord.ButtonStyle.secondary, # グレー
            discord.ButtonStyle.danger     # 赤
        ]
        
        # enumerateを使って、選択肢と色を1つずつペアにして取り出す
        for i, opt in enumerate(shuffled_options):
            current_style = button_styles[i % 4]
            
            # 💡 ボタンを作るときに、引数として「色（current_style）」を直接渡す！
            btn = AcademicQuizButton(label=opt, view_obj=self, style=current_style)
            self.add_item(btn)

# ==========================================
# 🔑 管理者認証用の入力フォーム（モーダル画面）
# ==========================================
class AdminAuthModal(discord.ui.Modal, title="管理者認証フォーム"):
    password_input = discord.ui.TextInput(
        label="4桁のパスワードを入力してください", 
        placeholder="例: 1234",
        min_length=4,
        max_length=4
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

async def on_message(message):
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

x, h = sp.symbols('x h')
f = x**2
definition_expr = (f.subs(x, x + h) - f) / h
derivative = sp.limit(definition_expr, h, 0)

# ③ 一般知識クイズ
quiz_dictionary = {}
if os.path.exists("quiz_dictionary.json"):
    with open("quiz_dictionary.json", "r", encoding="utf-8") as f:
        quiz_dictionary = json.load(f)

def update_db_score(user_id: int, username: str, is_correct: bool):
    """正解・不正解時にクラウドデータベースのカウントを+1（アップサート）する関数"""
    try:
        response = supabase.table("user_scores").select("*").eq("user_id", user_id).execute()
        
        # 💡 response.data が空ではない（登録済みユーザー）の場合
        if response.data and len(response.data) > 0:
            current = response.data[0]  # 👈 【重要】 [0] をつけてリストの先頭の辞書を取り出す
            correct = current["correct_count"] + (1 if is_correct else 0)
            wrong = current["wrong_count"] + (0 if is_correct else 1)
        else:
            # 初めてクイズに答えるユーザーの場合
            correct = 1 if is_correct else 0
            wrong = 0 if is_correct else 1

        # データをSupabaseへ保存
        supabase.table("user_scores").upsert({
            "user_id": user_id,
            "username": username,
            "correct_count": correct,
            "wrong_count": wrong,
            "updated_at": "now()"
        }).execute()
        print(f"【システムログ】{username} さんのデータをSupabaseに保存しました。") # 確認用ログ
    except Exception as e:
        print(f"Supabase書き込みエラー: {e}")

# 💡 1. デコレータを必ず付ける
@client.event
async def on_message(message):
    global current_quiz, current_quiz_junior_high, current_quiz_academic
    global user_status, selected_grade, selected_subject, selected_range, selected_content

    if message.author == client.user:
        return

        # 🔄 【トリガー2】元の3人だけが使えるパスワード強制リセットコマンド
    if message.content == "!password-reset":
        # 🌟 if文を使って、打った人が「元の3人」のリストに入っているか厳格にチェック！
        if message.author.id in ORIGINAL_ADMINS:
            global ADMIN_PASSWORD
            ADMIN_PASSWORD = str(random.randint(1000, 9999))
            
            # 実行した創設者のDM（ダイレクトメッセージ）にだけ、新しいパスワードをこっそり通知
            try:
                await message.author.send(f"👑 パスワードを強制リセットしました：【{ADMIN_PASSWORD}】")
                await message.channel.send("🔄 創設者権限により、パスワードをランダムな新しい値に変更しました！（実行者にDMを送信しました）")
            except discord.Forbidden:
                # 万が一DMがブロックされていた場合のバックアップ対策
                await message.channel.send(f"🔄 パスワードを変更しました！（※DMが閉じていたため、MWSのログを確認してください）")
        else:
            await message.channel.send("❌ エラー：この緊急コマンドはBotの【創設者3人】のみが実行できます。")
        return

    # 💡 2. 先頭が「!」のコマンドは、クイズの『解答中』の時だけ判定をスルーさせるように修正
    # （これがないと、!学術クイズ などのコマンド自体もすべて無視されてしまいます）
    if message.content.startswith("!") and message.content not in ["!ストップ", "!stop", "!cancel"]:
        # クイズが何も始まっていない（待機状態の）時は、下のコマンド受付に進ませる
        if current_quiz is None and current_quiz_junior_high is None and current_quiz_academic is None and user_status is None:
            pass 
        else:
            return  # クイズ進行中の時は、誤爆防止のためメッセージをスルーする

    # 🎯 2. 一般知識クイズ解答判定 （ここから下は元のコードと同じです）
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
            update_db_score(user_id, message.author.display_name, is_correct)
            await message.channel.send("<a:marugame:1556977377601527920> 正解！お見事です（一般知識）！🎉")
            await message.channel.send(f'<:hint:1556661937356546069> 【解説】\n{quiz_data["explanation"]}')
            current_quiz = None  
        else:
            update_db_score(user_id, message.author.display_name, is_correct)
            await message.channel.send("不正解です。<:oh_no:1556661209116184686> もう一度挑戦してみてください！")
            await message.channel.send(f'<:hint:1556661937356546069> 【ヒント】\n{quiz_data["hint"]}')
        return

    # 🎯 2.5 学術クイズ（テキスト形式）の解答判定
    # 💡 【重要】並び順をココに移動して、上の一般知識クイズ判定（if）の直後の「elif」として綺麗に繋げました！
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
            update_db_score(user_id, message.author.display_name, is_correct)
            await message.channel.send("<a:marugame:1556977377601527920> 正解！お見事です！🎉📚")
            await message.channel.send(f'<:hint:1556661937356546069> 【解説】\n{quiz_data["explanation"]}')
            current_quiz_academic = None  
            user_status = None
        else:
            update_db_score(user_id, message.author.display_name, is_correct)
            await message.channel.send("不正解です😢...<:oh_no:1556661209116184686> もう一度挑戦してみてください！")
            await message.channel.send(f'<:hint:1556661937356546069> 【ヒント】\n{quiz_data["hint"]}')
        return

    # 🎯 3. 中学クイズ解答判定
    # 💡 【重要】ここも「elif」に変更し、上のクイズ判定の鎖へ一本に合流させました！
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
            # 💡 古い user_scores のプラス処理を、正しい Supabase 保存処理にアップデートしました
            update_db_score(user_id, message.author.display_name, is_correct)
            await message.channel.send("<a:marugame:1556977377601527920> ⭕ 正解！お見事です！ 🎉")
            await message.channel.send(f'💡 【解説】 \n{quiz_data["explanation"]}')
            current_quiz_junior_high = None  
            user_status = None  
        else:
            update_db_score(user_id, message.author.display_name, is_correct)
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
        
        # 💡 古い user_scores の計算処理（5行分）はここに挟まず、直接Supabaseを読み込みます
        try:
            response = supabase.table("user_scores").select("*").eq("user_id", user_id).execute()
            if response.data and len(response.data) > 0:
                data = response.data[0]  # 👈 リストの先頭の辞書オブジェクトを確実に取得
                correct = data["correct_count"]
                wrong = data["wrong_count"]
                total = correct + wrong
                rate = (correct / total * 100) if total > 0 else 0
                
                await message.channel.send(
                    f"📊 **{message.author.display_name} さんのクイズ成績（クラウド保存）**\n"
                    f"• 正解数: {correct} 回 ⭕\n"
                    f"• 不正解数: {wrong} 回 ❌\n"
                    f"• 正答率: {rate:.1f} %"
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
            ),
            inline=False
        )
        embed.add_field(
            name="🛠️ 管理者向け機能(実行は管理専用サーバーでしてください)",
            value=("• `!github-repositories` : 開発用GitHubリポジトリのURLを確認する\n"
                   "• `!supabase-table(quiz_score)` : 全員のクイズの成績を確認する\n"
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

@client.event
async def on_ready():
    print(f"ログインしました: {client.user}")

TOKEN = os.getenv("DISCORD_TOKEN")
client.run(TOKEN)