import os
import random
import discord

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# ==========================================
# 📊 状態管理変数
# ==========================================
current_quiz = None             # 一般知識用クイズの状態
current_quiz_junior_high = None # 中学生用クイズの出題中の問題データ

# 👤 ユーザーの選択状態を管理（細分化用）
user_status = None 
selected_subject = None         
selected_unit = None            

# ==========================================
# 📚 中学生用：教科・範囲・内容別のクイズデータ（3段階構造）
# ==========================================
quiz_junior_high_school = {
    "国語": {
        "漢字": {
            "はじまりの風": {
                "「はじまりの風」に出てくる「フクシュウ」の漢字は？（※前回の復習の意味）": {
                    "answer": "復習",
                    "explanation": "「繰り返し習う」という意味なので「復」を使います。お腹に一物ある「復讐」と間違えないようにしましょう。",
                    "hint": "往復の「復」に、学習の「習」です。"
                },
            }
        }
    },
    "数学": {
        "代数": {
            "方程式": {
                "3x + 5 = 11 の解は？": {
                    "answer": "2",
                    "explanation": "3x = 11 - 5 ➔ 3x = 6 ➔ x = 2 となります。",
                    "hint": "5を右辺に移項してみましょう。"
                }
            }
        }
    },
      "理科": {
        "物質": {  # 👈 これが「範囲」
            "金属と非金属": {  # 👈 これが「内容（単元）」
                # ⬇️ ここに【問題文】をキーとして、その中に answer などを書きます
                "金属の性質に当てはまらないものを次のア～ウから一つ選び、記号で答えろ。ア：延性がある イ：電気伝導性がある ウ：熱伝導性がある エ：磁石に引き寄せられる オ：展性がある カ：金属光沢がある": {
                    "answer": "エ",
                    "explanation": "金属の性質には、延性、展性、電気伝導性、熱伝導性、金属光沢があります。磁石に引き寄せられるのは鉄など一部の金属に限られますので、エが正解です。",
                    "hint": "当てはまらないのは鉄のみに当てはまる性質です！"
                }
            }
        }
    },
}

# ==========================================
# 📊 状態管理変数のアップデート
# ==========================================
# user_status の状態一覧:
# None: 通常状態
# "select_subject": 教科を選び中
# "select_range": 範囲を選び中   👈【追加】
# "select_content": 内容を選び中 👈【追加】
# "quiz_active": クイズ中
user_status = None 
selected_subject = None         
selected_range = None    # 👈【追加】一時記憶用
selected_content = None  # 👈【追加】一時記憶用
current_quiz_junior_high = None

# 【一般知識】クイズの辞書
quiz_dictionary = {
    "0831→1964→2015→1345→?": {
        "answer": "1104",
        "explanation": "明治、大正、昭和、平成と続いた法則です。最後は慶応4年を指すため1104となります！",
        "hint": "前半二桁は元号を表しています！",
    },
    "世界恐慌は何年？": {
        "answer": "1929年",
        "explanation": "ニューヨークの株価大暴落がきっかけです。",
        "hint": "1920年代の終わり頃です。"
    },
    "工業用エタノールに酒税はかかる？": {
        "answer": "かからない",
        "explanation": "お酒として飲めないように処置されているため、税金はかかりません。",
        "hint": "工業用のエタノールは飲めません！",
    },
    "5次方程式以上の代数的な解の公式が存在しないことを示した理論は？": {
        "answer": "ガロア理論",
        "explanation": "ガロア理論は、5次以上の一般解の公式が存在しないことを証明する理論です。",
        "hint": "人物名+理論名です！",
    },
    "SVO型の言語であり、ドイツ、オーストリアなどが公用語として扱っている言語は？": {
        "answer": "ドイツ語",
        "explanation": "ドイツ語はインド・ヨーロッパ語族に属する言語です。",
        "hint": "ヨーロッパの国名＋語で考えてみてください！",
    },
    "アフリカでフランスの横断政策、イギリスの縦断政策により衝突した二国が起こした事件は？": {
        "answer": "ファショダ事件",
        "explanation": "1898年にスーダンのファショダで、フランスとイギリスが衝突した事件です。",
        "hint": "アフリカの地名＋事件で考えてみてください！",
    },
    '映画「ソウルの春」のテーマになった出来事は？': {
        "answer": ["12.12.軍事反乱", "12月12日軍事クーデター", "12.12.軍事クーデター"],
        "explanation": "1979年12月12日に韓国で発生した軍事クーデターです。",
        "hint": "1979年12月12日に韓国で発生した事件です。",
    },
    "積分におけるdxはどのような意味を持つ？": {
        "answer": "xの微小な変化",
        "explanation": "積分におけるdxは、変数xの微小な変化を表します。",
        "hint": "微分積分学の基本概念です。",
    },
    "不定積分の式の最後につく記号は？": {
        "answer": "+C",
        "explanation": "不定積分の式の最後につく記号+Cは、積分定数を表します。",
        "hint": "積分定数を表す記号です。",
    },
    "アガサ・クリスティ著の小説『そして誰もいなくなった』の連続殺人のモチーフとなった詩は？": {
        "answer": ["10人の小さな兵隊さん", "Ten Little Soldier Boys"],
        "explanation": "童謡になぞらえて、登場人物たちが次々と殺害されていくミステリー小説です。",
        "hint": "元となった詩の名前は「Ten Little Indians」です。",
    },
}


# ==========================================
# 📩 メッセージ受信イベント
# ==========================================
@client.event
async def on_message(message):
    global current_quiz, current_quiz_junior_high
    global user_status, selected_subject, selected_unit, selected_range, selected_content

    if message.author == client.user:
        return

    
    # ------------------------------------------
    # 🛑 【追加】クイズ・メニュー選択の中断コマンド
    # ------------------------------------------
    if message.content in ["!ストップ", "!stop", "!cancel"]:
        # すべての状態をリセット
        user_status = None
        current_quiz = None
        current_quiz_junior_high = None
        selected_subject = None
        selected_unit = None
        selected_range = None
        await message.channel.send("🛑 クイズ・メニュー選択を中断してリセットしました！")
        return
   
    
 # 🤖 ステップ1: 教科の選択
async def select_subject(message):
    if user_status == "select_subject":
        subjects = list(quiz_junior_high_school.keys())
        if message.content in subjects:
            selected_subject = message.content
            user_status = "select_range"
            
            # 💡 教科のすぐ下にある「範囲（漢字、代数、物質など）」の一覧を取得
            ranges = list(quiz_junior_high_school[selected_subject].keys())
            if not ranges:
                await message.channel.send(f"❌ 現在、{selected_subject}には登録されている範囲がありません。")
                user_status = None
                return
                
            range_text = "・".join(ranges)
            await message.channel.send(f"**範囲はどうしますか？**\n{range_text} から選んでください。")
        else:
            await message.channel.send("選択肢にある教科を正しく入力してください。")
        return

    # 🤖 ステップ2: 範囲の選択
    elif user_status == "select_range":
        ranges = list(quiz_junior_high_school[selected_subject].keys())
        if message.content in ranges:
            selected_range = message.content
            user_status = "select_content"
            
            # 💡 範囲のすぐ下にある「内容（はじまりの風、方程式、金属と非金属など）」の一覧を取得
            contents = list(quiz_junior_high_school[selected_subject][selected_range].keys())
            if not contents:
                await message.channel.send(f"❌ 現在、{selected_range}には登録されている内容がありません。")
                user_status = None
                return
                
            content_text = "、".join(contents)
            await message.channel.send(f"**内容はどれにしますか？**\n{content_text} から選んでください。")
        else:
            await message.channel.send("選択肢にある範囲を正しく入力してください。")
        return

    # 🤖 ステップ3: 内容の選択（出題処理）
    elif user_status == "select_content":
        contents = list(quiz_junior_high_school[selected_subject][selected_range].keys())
        if message.content in contents:
            selected_content = message.content
            
            # 💡 内容のすぐ下にある「問題（問題文がキー、中身が辞書）」の一覧を取得
            questions = quiz_junior_high_school[selected_subject][selected_range][selected_content]
            if not questions:
                await message.channel.send(f"❌ 現在、{selected_content}には問題が登録されていません。")
                user_status = None
                return
                
            # 💡 問題文（テキスト）をランダムに1つ選ぶ
            chosen_question = random.choice(list(questions.keys()))
            
            # 💡 選んだ問題文の奥にあるデータ本体（answerやexplanationの入った辞書）を掴む！
            current_quiz_junior_high = questions[chosen_question]
            
            user_status = "quiz_active"  # 解答待ちモードへ
            await message.channel.send(f"では、ランダムに問題を出します。\n\n**問題：{chosen_question}**")
        else:
            await message.channel.send("選択肢にある内容を正しく入力してください。")
        return


    # ------------------------------------------
    # 🎯 2. 【復活】一般知識クイズの解答判定
    # ------------------------------------------
    if current_quiz is not None:
        quiz_data = quiz_dictionary[current_quiz]
        
        is_correct = False
        if isinstance(quiz_data["answer"], list):
            if message.content in quiz_data["answer"]:
                is_correct = True
        else:
            if message.content == quiz_data["answer"]:
                is_correct = True

        if is_correct:
            await message.channel.send("⭕ 正解！お見事です（一般知識）！🎉")
            await message.channel.send(f'💡 【解説】\n{quiz_data["explanation"]}')
            current_quiz = None  # クイズを終了してリセット
        else:
            await message.channel.send(">_< 不正解です。もう一度挑戦してみてください！")
            await message.channel.send(f'💡 【ヒント】\n{quiz_data["hint"]}')
        return


  # ------------------------------------------
    # 🚀 3. クイズ開始コマンドの受付（通常時）
    # ------------------------------------------
    # 正しいコマンドの受付
    if message.content == "!中学クイズ":
        user_status = "select_subject"
        subject_text = "・".join(quiz_junior_high_school.keys())
        await message.channel.send(f"**どの教科にしますか？**\n{subject_text}の中から選んでください。")
        return

    if message.content == "!normal-quiz":
        await message.channel.send("【一般知識クイズ】を出します！")
        chosen_quiz = random.choice(list(quiz_dictionary.keys()))
        current_quiz = chosen_quiz
        await message.channel.send(chosen_quiz)
        return

    if message.content == "!help-hironekobot":
        quiz_menu_text = ""
        for subject, units in quiz_junior_high_school.items():
            unit_names = "、".join(units.keys()) if units.keys() else "（未登録）"
            quiz_menu_text += f"🔹 **{subject}**\n┗ 単元: {unit_names}\n\n"

        embed = discord.Embed(
            title="🤖 クイズボット コマンド・プログラム一覧表",
            description="試験勉強やクイズを楽しむためのコマンド一覧です！",
            color=discord.Color.blue()
        )
        
        # 📚 勉強用クイズ
        embed.add_field(
            name="📚 中間テスト対策クイズ（教科・単元選択）",
            value=f"コマンド: `!中学クイズ`\n\n【現在登録されているメニュー】\n{quiz_menu_text}",
            inline=False
        )
        embed.add_field(
                    name="📚 中学クイズおまかせ",
                    value=f"コマンド: `!中学クイズおまかせ`\n\n【現在登録されているメニュー】\n{quiz_menu_text}",
                    inline=False
                )
        
        # 🛑 【追加】中断コマンドの案内
        embed.add_field(
            name="🛑 クイズを途中でやめたいとき",
            value="• `!ストップ`  / `!stop` / `!cancel`\n※入力すると、いつでもメニュー選択やクイズを中断してリセットできます。",
            inline=False
        )
        
        # 🎲 その他の機能
        embed.add_field(
            name="🎲 その他の機能",
            value=(
                "• `!なんかクイズ出して` : 一般知識クイズに挑戦\n"
                "• `!今日の運勢` : 今日の運勢を占う!\n"
                "• `!明日の運勢` : 明日の運勢を占う!!\n"
                "• `!サイコロ` : サイコロを振る `!サイコロ 100`のように上限を指定できるよ！ "
                "`!サイコロ 2 3`のように振る回数も指定できるよ!\n"
                "• `!ランダムに州を選んで` : 世界の6大州をランダムに選択\n"
                "• `!こんにちは` / `!おはよう` / `!こんばんは` / `!おやすみ`"
            ),
            inline=False
        )
        
        embed.set_footer(text="大文字・小文字の打ち間違いに注意してね！")
        
        await message.channel.send(embed=embed)
        return

        # ------------------------------------------
    # 🎲 【追加】中学生クイズを完全ランダムに出題する
    # ------------------------------------------
    if message.content == "!中学クイズおまかせ":
        # 全問題の一覧を一時的に集めるリスト
        all_questions = []

        # 3段階の辞書をすべてループして問題データを集める
        for subject, ranges in quiz_junior_high_school.items():
            for range_name, contents in ranges.items():
                for content_name, questions in contents.items():
                    for q_text, q_data in questions.items():
                        # 後で出題メッセージに「どの教科のどの範囲か」を表示できるように情報をセット
                        all_questions.append({
                            "text": q_text,
                            "data": q_data,
                            "info": f"【{subject} ➔ {range_name} ➔ {content_name}】"
                        })

        # 登録されている問題が1問もない場合の対策
        if not all_questions:
            await message.channel.send("❌ 現在、中学生用のクイズが1問も登録されていません。")
            return

    # 集まった問題リストから完全にランダムで1問選ぶ
        chosen = random.choice(all_questions)
        current_quiz_junior_high = chosen["data"]
        user_status = "quiz_active"  # 解答待ちの状態にする

        await message.channel.send(
            f"🎲 すべての範囲からランダムに問題を出します！\n"
            f"💡 出題範囲：{chosen['info']}\n\n"
            f"**問題：{chosen['text']}**"
        )
        return
    
    # ------------------------------------------
    # 💬 4. 挨拶などの日常コマンド
    # ------------------------------------------
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
     # ------------------------------------------
    # 🎲 サイコロ機能（上限と個数を指定可能＋荒らし対策）
    # ------------------------------------------
    elif message.content.startswith("!サイコロ"):
        args = message.content.split()
        
        # 🔒 【荒らし対策設定欄】
        MAX_DICE_LIMIT = 20      # 一度に振れる最大「個数」の制限
        MAX_VALUE_LIMIT = 1000000  # 👈【追加】サイコロの最大の「数値（面数）」の制限

        max_value = 6   # デフォルトのサイコロの面数（1〜6）
        dice_count = 1  # デフォルトのサイコロの個数（1個）
        
        # 1. 引数が1つの場合（!サイコロ）
        if len(args) == 1:
            pass
            
        # 2. 引数が2つの場合（!サイコロ 100）
        elif len(args) == 2:
            if args[1].isdigit():
                max_value = int(args[1])
            else:
                await message.channel.send("❌ 上限数は数字で入力してください。 (例: `!サイコロ 100`)")
                return
                
        # 3. 引数が3つの場合（!サイコロ 6 5）
        elif len(args) == 3:
            if args[1].isdigit() and args[2].isdigit():
                max_value = int(args[1])
                dice_count = int(args[2])
            else:
                await message.channel.send("❌ 上限数と個数はどちらも数字で入力してください。 (例: `!サイコロ 6 5`)")
                return
        else:
            await message.channel.send("❌ 引数が多すぎます。 (例: `!サイコロ 6 5` のように入力してください)")
            return

        # 🚫 基本のエラーチェック（1未満の数字をガード）
        if max_value < 1 or dice_count < 1:
            await message.channel.send("❌ 上限数と個数は、どちらも 1 以上の数字を指定してください。")
            return

        # 🔥 【追加：数値の荒らし対策】設定した最大値を超えている場合の処理
        if max_value > MAX_VALUE_LIMIT:
            await message.channel.send(
                f"⚠️ **これ以上の大きな数値（面数）は指定できません！**\n"
                f"このサーバーでの最大数値は **{MAX_VALUE_LIMIT}** までに制限されています。"
            )
            return

        # 🔥 【個数の荒らし対策】設定した最大個数を超えている場合の処理
        if dice_count > MAX_DICE_LIMIT:
            await message.channel.send(
                f"⚠️ **これ以上の個数は同時に振ることができません！**\n"
                f"このサーバーでの最大同時個数は **{MAX_DICE_LIMIT}個** までに制限されています。"
            )
            return

        # 🎲 サイコロを振る処理
        results = []
        for _ in range(dice_count):
            results.append(random.randint(1, max_value))
            
        total = sum(results)

        # 💬 結果のメッセージを表示
        if dice_count == 1:
            await message.channel.send(f"🎲 1 〜 {max_value} のサイコロを振りました！\n出た目は **【 {total} 】** です！")
        else:
            details = " ＋ ".join([f"[{r}]" for r in results])
            await message.channel.send(
                f"🎲 1 〜 {max_value} のサイコロを **{dice_count} 個** 振りました！\n"
                f"内訳: {details}\n"
                f"合計は **【 {total} 】** です！"
            )
        return

@client.event
async def on_ready():
    print(f"ログインしました: {client.user}")

TOKEN = os.getenv("DISCORD_TOKEN")
client.run(TOKEN)