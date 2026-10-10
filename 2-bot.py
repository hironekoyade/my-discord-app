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
current_quiz = None             
current_quiz_junior_high = None 

user_status = None 
selected_subject = None         
selected_range = None    
selected_content = None  




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
    global user_status, selected_subject, selected_range, selected_content

    if message.author == client.user:
        return

    # 🛑 1. 中断コマンド
    if message.content in ["!ストップ", "!stop", "!cancel"]:
        user_status = None
        current_quiz = None
        current_quiz_junior_high = None
        selected_subject = None
        selected_range = None    
        selected_content = None  
        await message.channel.send("🛑 クイズ・メニュー選択を中断してリセットしました！")
        return

    # 🔄 2. 中学生クイズのフロー
    if user_status == "select_subject":
        subjects = list(quiz_junior_high_school.keys())
        if message.content in subjects:
            selected_subject = message.content
            user_status = "select_range"
            ranges = list(quiz_junior_high_school[selected_subject].keys())
            if not ranges:
                await message.channel.send(f"❌ 現在、{selected_subject}には範囲がありません。")
                user_status = None
                return
            range_text = "・".join(ranges)
            await message.channel.send(f"**範囲はどうしますか？**\n{range_text} から選んでください。")
        else:
            await message.channel.send("選択肢にある教科を正しく入力してください。")
        return

    elif user_status == "select_range":
        ranges = list(quiz_junior_high_school[selected_subject].keys())
        if message.content in ranges:
            selected_range = message.content
            user_status = "select_content"
            contents = list(quiz_junior_high_school[selected_subject][selected_range].keys())
            if not contents:
                await message.channel.send(f"❌ 現在、{selected_range}には内容がありません。")
                user_status = None
                return
            content_text = "、".join(contents)
            await message.channel.send(f"**内容はどれにしますか？**\n{content_text} から選んでください。")
        else:
            await message.channel.send("選択肢にある範囲を正しく入力してください。")
        return

    elif user_status == "select_content":
        contents = list(quiz_junior_high_school[selected_subject][selected_range].keys())
        if message.content in contents:
            selected_content = message.content
            questions = quiz_junior_high_school[selected_subject][selected_range][selected_content]
            if not questions:
                await message.channel.send(f"❌ 現在、{selected_content}には問題がありません。")
                user_status = None
                return
            chosen_question = random.choice(list(questions.keys()))
            current_quiz_junior_high = questions[chosen_question]
            user_status = "quiz_active"  
            await message.channel.send(f"では、ランダムに問題を出します。\n\n**問題：{chosen_question}**")
        else:
            await message.channel.send("選択肢にある内容を正しく入力してください。")
        return

    elif user_status == "quiz_active" and current_quiz_junior_high is not None:
        quiz_data = current_quiz_junior_high
        is_correct = False
        if isinstance(quiz_data["answer"], list):
            if message.content in quiz_data["answer"]:
                is_correct = True
        else:
            if message.content == quiz_data["answer"]:
                is_correct = True

        if is_correct:
            await message.channel.send("⭕ 正解！お見事です！🎉")
            await message.channel.send(f'💡 【解説】\n{quiz_data["explanation"]}')
            user_status = None
            current_quiz_junior_high = None
        else:
            await message.channel.send(">_< 不正解です。もう一度挑戦してみてください！")
            await message.channel.send(f'💡 【ヒント】\n{quiz_data["hint"]}')
        return

    # 🎯 3. 一般知識クイズ解答判定
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
            current_quiz = None  
        else:
            await message.channel.send(">_< 不正解です。もう一度挑戦してみてください！")
            await message.channel.send(f'💡 【ヒント】\n{quiz_data["hint"]}')
        return

    # 🚀 4. コマンド受付
    if message.content == "!中学クイズ":
        user_status = "select_subject"
        subject_text = "・".join(quiz_junior_high_school.keys())
        await message.channel.send(f"**どの教科にしますか？**\n{subject_text}の中から選んでください。")
        return

    if message.content == "!中学クイズおまかせ":
        all_questions = []
        for subject, ranges in quiz_junior_high_school.items():
            for range_name, contents in ranges.items():
                for content_name, questions in contents.items():
                    for q_text, q_data in questions.items():
                        all_questions.append({
                            "text": q_text,
                            "data": q_data,
                            "info": f"【{subject} ➔ {range_name} ➔ {content_name}】"
                        })
        if not all_questions:
            await message.channel.send("❌ 現在、中学生用のクイズが1問も登録されていません。")
            return
        chosen = random.choice(all_questions)
        current_quiz_junior_high = chosen["data"]
        user_status = "quiz_active"  
        await message.channel.send(f"🎲 すべての範囲からランダムに問題を出します！\n💡 出題範囲：{chosen['info']}\n\n**問題：{chosen['text']}**")
        return

    if message.content == "!なんかクイズ出して":
        await message.channel.send("【一般知識クイズ】を出します！")
        chosen_quiz = random.choice(list(quiz_dictionary.keys()))
        current_quiz = chosen_quiz
        await message.channel.send(chosen_quiz)
        return

    # 📋 5. ヘルプ機能
    if message.content == "!help-hironekobot":
        quiz_menu_text = ""
        for subject, ranges in quiz_junior_high_school.items():
            range_list = []
            for r_name, c_dict in ranges.items():
                c_names = "、".join(c_dict.keys()) if c_dict.keys() else "設定なし"
                range_list.append(f"{r_name} ({c_names})")
            range_info = "、".join(range_list) if range_list else "（未登録）"
            quiz_menu_text += f"🔹 **{subject}**\n┗ 範囲: {range_info}\n\n"

        embed = discord.Embed(
            title="🤖 クイズボット コマンド・プログラム一覧表",
            description="試験勉強やクイズを楽しむためのコマンド一覧です！",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="📚 中間テスト対策クイズ",
            value=f"• `!中学クイズ` : メニューを選んで出題\n• `!中学クイズおまかせ` : 全範囲から完全ランダム出題\n\n【現在登録されているメニュー】\n{quiz_menu_text}",
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

    # 🎲 6. サイコロ機能
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