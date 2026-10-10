import os
import random
import discord
import sympy as sp

user_scores = {}

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
selected_grade = None    
selected_subject = None         
selected_range = None    
selected_content = None    

# ==========================================
# 📚 クイズデータ（学年対応版）
# ==========================================
quiz_junior_high_school = {
    "中学1年": {
        "国語": {
            "漢字": {
                "はじまりの風": {
                    "「はじまりの風」に出てくる「フクシュウ」の漢字は？": {
                        "answer": "復習",
                        "explanation": "「繰り返し習う」という意味なので「復」を使います。お腹に一物ある「復讐」と間違えないようにしましょう。",
                        "hint": "往復の「復」に、学習の「習」です。"
                    }
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
                    },
                    "方程式では、2(x+3)=2x+6という操作を行うことができるが、これは何法則を用いているか？": {
                        "answer": ["分配法則", "分配"],
                        "explanation": "2(x+3) = 2x + 6 という操作は、2(x+3)という式のx+3という項に2を分配しているため、分配法則を用いています。",
                        "hint": "カッコの中の各項に同じ数をかける法則です。"
                    }
                }
            }
        },
        "理科": {
            "物質": {
                "金属と非金属": {
                    "金属の性質に当てはまらないものを次のア～ウから一つ選び、記号で答えろ。ア：延性がある イ：電気伝導性がある ウ：熱伝導性がある エ：磁石に引き寄せられる オ：展性がある カ：金属光沢がある": {
                        "answer": "エ",
                        "explanation": "金属の性質には、延性、展性、電気伝導性、熱伝導性、金属光沢があります。磁石に引き寄せられるのは鉄など一部の金属に限られますので、エが正解です。",
                        "hint": "当てはまらないのは鉄のみに当てはまる性質です！"
                    },
                },
                "気体の分類":{
                    "空気よりも軽く、水に溶けやすい気体(例えばアンモニアなど)はなんという方法で集める？": {
                        "answer": "上方置換法",
                        "explanation": "空気よりも軽い気体は、上方置換法で集めることができます。",
                        "hint": "水上置換法、上方置換法、下方置換法のうちいずれかを使います。"
                    },
                    "二酸化炭素を溶かした液体は何性？": {
                        "answer": "酸性",
                        "explanation": "二酸化炭素を水に溶かすと炭酸が生成され、酸性を示します。",
                        "hint": "二酸化炭素は水に溶けるとソーダになります。"
                    }
                }
            }
        },
        "社会": {
            "地理": {
                "アジア州": {
                    "中国が経済を発展させるために作った特徴的な地域は？": {
                        "answer": "経済特区",
                        "explanation": "中国には、経済特区という地域があり、外国企業の投資を促進するための特別な制度があります。",
                        "hint": "特定の地域に設けられる経済制度です。"
                    },
                    "アジア州に吹く、季節によって方向が変わる風のことを何という？": {
                        "answer": ["モンスーン", "季節風"],
                        "explanation": "モンスーンは、季節によって風向きが変わる風のことを指します。夏には南西から、冬には北東から吹くことが特徴です。",
                        "hint": "アジア州で季節によって吹く風のことを指します。"
                    },
                    "中国で、1組の夫婦に子どもを原則1人までとする、人口抑制のためにかつて行われていた政策は？": {
                        "answer": "一人っ子政策",
                        "explanation": "少子高齢化が進んだため、現在は廃止（制限緩和）されています。",
                        "hint": "「一人の子ども」を育てる政策という意味の名前です。"
                    }
                },
                "緯度": {
                    "緯度は最大何度まである？": {
                        "answer": ["90度", "90°"],
                        "explanation": "緯度は地球の表面を東西に走る線（緯線）の角度で表され、赤道が基準となり、北緯と南緯でそれぞれ90度まであります。",
                        "hint": "赤道を基準にして、北緯と南緯でそれぞれ90度まであります。"
                    }
                },
                "経度": {
                    "経度は最大何度まである？": {
                        "answer": ["180度", "180°"],
                        "explanation": "経度は地球の表面を南北に走る線（経線）の角度で表され、グリニッジ天文台が基準となり、東経と西経でそれぞれ180度まであります。",
                        "hint": "グリニッジ天文台を基準にして、東経と西経でそれぞれ180度まであります。"
                    }
                },
                "時差": {
                    "時差の計算には緯度と経度、どちらを用いる？": {
                        "answer": "経度",
                        "explanation": "時差は経度に基づいて計算されます。地球は自転しているため、経度が異なると時間帯が異なります。",
                        "hint": "経度はグリニッジ天文台が0度、緯度は赤道が0度です。"
                    },
                    "日本(東経135度)とサンフランシスコ(西経120度)の時差は何時間？": {
                        "answer": "17時間",
                        "explanation": "日本とサンフランシスコの経度の差は135度 + 120度 = 255度です。地球は360度を24時間で回転するため、1時間あたり15度進むことになります。したがって、255度 ÷ 15度/時間 = 17時間の時差があります。",
                        "hint": "東経と西経では、経度の差を足して計算します。"
                    }
                },
                "アフリカ州":{
                    "アフリカ州北部に広がる世界最大の砂漠は？": {
                        "answer": "サハラ砂漠",
                        "explanation": "サハラ砂漠は、アフリカ州北部に広がる世界最大の熱帯砂漠です。",
                        "hint": "アルジェリアやリビアなどの国々に広がる砂漠です。"
                    },
                    "アフリカ州東部を流れる世界最長の川を何というか。":{
                        "answer": "ナイル川",
                        "explanation": "ナイル川は、アフリカ州東部を流れる世界最長の川で、全長約6,650キロメートルです。",
                        "hint": "エジプト文明の発展に大きく関わった川です。"
                    }
                },
                "ヨーロッパ州":{
                    "ヨーロッパ州で広く信仰されている宗教は？": {
                        "answer": "キリスト教",
                        "explanation": "ヨーロッパ州では、キリスト教が広く信仰されています。",
                        "hint": "西洋の主要な宗教です。"
                    }
                }
            }
        },
        "英語": {
            "文法": {
                "一人称": {
                    "I amの短縮形は？": {
                        "answer": "I'm",
                        "explanation": "I amの短縮形はI'mです。",
                        "hint": "最初の文字は大文字ですか？"
                    }
                },
                "二人称": {
                    "二人称は誰のことを指す？ア～ウから記号で一つ選びなさい。 ア：私 イ：あなた ウ：私とあなた以外の人": {
                        "answer": "イ",
                        "explanation": "二人称は「あなた」を指します。私は一人称、私とあなた以外の人は三人称です。",
                        "hint": "英語のyouは二人称の代名詞です。"
                    }
                },
                "三人称": {
                    "三人称単数現在形では、動詞に-sがつく。これは正しい？": {
                        "answer": "正しくない",
                        "explanation": "三人称単数現在形では、動詞には-s以外にも-esや不規則変化があるため、すべての動詞に-sがつくわけではありません。",
                        "hint": "三人称単数現在形の動詞、例えばliveやgoなどはどのように変化しますか？"
                    },
                    "三人称単数現在形では、doはどんな単語に変化する？": {
                        "answer": "does", 
                        "explanation": "三人称単数現在形では、助動詞doはdoesに変化します。例えば、He does his homework.のように使われます。",
                        "hint": "三人称単数現在形の文で、doを使う場合はどのように変化しますか？"}
                },
                "疑問文": {
                    "5W1Hは、助動詞(doなど)やbe動詞(am are is)の前につく。これは正しい？": {
                        "answer": "正しい",
                        "explanation": "5W1Hは、助動詞(doなど)やbe動詞(am are is)の前につきます。例えば、What do you want?やWhere is the station?のように使われます。",
                        "hint": "疑問文を思い浮かべてください。5W1H、例えばWhatやWhereはどのような位置にありますか？"
                    },
                    "疑問文では、主語と動詞の順番が入れ替わる。これは正しい？": {
                        "answer": "正しい",
                        "explanation": "疑問文では、主語と動詞の順番が入れ替わります。例えば、You are a student.は疑問文ではAre you a student?となります。",
                        "hint": "疑問文を作るとき、主語と動詞の位置はどうなりますか？"
                    },
                    "次の２つの文を比較し、どちらが正しいかを記号で答えなさい。 ア：what is this? イ：what's is this?": {
                        "answer": "ア",
                        "explanation": "正しい疑問文は「What is this?」です。「What's is this?」はwhat isの短縮形であるWhat's and isが重複しているため、文法的に正しくありません。",
                        "hint": "疑問文の構造を確認してください。"
                    },
                    "次の文が正しいか正しくないかを判断し、正しければ「正しい」と、正しくなければ内容は変えずに文法的に正確な文を答えなさい。 I favorite ice cream is banana.": {
                        "answer": "My favorite ice cream is banana.",
                        "explanation": "正しい文は「I favorite ice cream is banana.」ではなく、「My favorite ice cream is banana.」です。",
                        "hint": "主語と形容詞の関係を考えてみてください。また、最初は大文字にしたかも見直しましょう。"
                    },
                    "do you have three rabbit.という文がある。この時、rabbitには複数形のsを付けるか、付けないか。":{
                        "answer": "付ける",
                        "explanation": "あなたは〇〇を持っていますか？という文は、相手が複数物を持っていることをも想定するので、複数形のsを付けます。",
                        "hint": "いくつ持っているかを聞くとき、想定される回答は1、もしくは1以上です。",
                    },
                },
                "否定文":{
                    "you don't like study.という文の、don'tとは何の省略形か。":{
                        "answer": "do not",
                        "explanation": "",
                        "hint": "",
                    }
                }
            }
        }
    }
}

x, h = sp.symbols('x h')
f = x**2
definition_expr = (f.subs(x, x + h) - f) / h
derivative = sp.limit(definition_expr, h, 0)

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
    "映画「ソウルの春」のテーマになった出来事は？": {
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
    "f(x)=x^2の導関数は？":{
        "answer":["f'(x)=2x","dy/dx=2x"],
        "explanation": f"導関数の定義から計算した結果、{derivative} になります。",
        "hint":"導関数の定義から考えましょう。",
    },
}

# ==========================================
# 📩 メッセージ受信イベント
# ==========================================
@client.event
async def on_message(message):
    global current_quiz, current_quiz_junior_high
    global user_status, selected_grade, selected_subject, selected_range, selected_content

    if message.author == client.user:
        return

    # 🛑 1. 中断コマンド
    if message.content in ["!ストップ", "!stop", "!cancel"]:
        user_status = None
        current_quiz = None
        current_quiz_junior_high = None
        selected_grade = None    
        selected_subject = None
        selected_range = None    
        selected_content = None  
        await message.channel.send("🛑 クイズ・メニュー選択を中断してリセットしました！")
        return

    # 🎯 2. 一般知識クイズ解答判定
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
        if user_id not in user_scores:
            user_scores[user_id] = {"correct": 0, "wrong": 0}

        if is_correct:
            user_scores[user_id]["correct"] += 1  
            await message.channel.send("<a:marugame:1556977377601527920> 正解！お見事です（一般知識）！🎉")
            await message.channel.send(f'<:hint:1556661937356546069> 【解説】\n{quiz_data["explanation"]}')
            current_quiz = None  
        else:
            user_scores[user_id]["wrong"] += 1    
            await message.channel.send("不正解です。<:oh_no:1556661209116184686> もう一度挑戦してみてください！")
            await message.channel.send(f'<:hint:1556661937356546069> 【ヒント】\n{quiz_data["hint"]}')
        return

    # 🎯 3. 中学クイズ解答判定
    if user_status == "quiz_active" and current_quiz_junior_high is not None:
        is_correct = False
        quiz_data = current_quiz_junior_high
        if isinstance(quiz_data["answer"], list):
            if message.content in quiz_data["answer"]:
                is_correct = True
        else:
            if message.content == quiz_data["answer"]:
                is_correct = True

        user_id = message.author.id
        if user_id not in user_scores:
            user_scores[user_id] = {"correct": 0, "wrong": 0}

        if is_correct:
            user_scores[user_id]["correct"] += 1  
            await message.channel.send("<a:marugame:1556977377601527920> ⭕ 正解！お見事です！ 🎉")
            await message.channel.send(f'💡 【解説】 \n{quiz_data["explanation"]}')
            current_quiz_junior_high = None  
            user_status = None  
        else:
            user_scores[user_id]["wrong"] += 1    
            await message.channel.send(" 不正解です... <:oh_no:1556661209116184686> もう一度挑戦してみてください！")
            await message.channel.send(f'<:hint:1556661937356546069> 【ヒント】 \n{quiz_data["hint"]}')
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
        if user_id in user_scores:
            correct = user_scores[user_id].get("correct", 0)
            wrong = user_scores[user_id].get("wrong", 0)
            total = correct + wrong
            # 正答率の計算（0除算対策）
            rate = (correct / total * 100) if total > 0 else 0
            
            await message.channel.send(
                f"📊 **{message.author.display_name} さんのクイズ成績**\n"
                f"• 正解数: {correct} 回 ⭕\n"
                f"• 不正解数: {wrong} 回 ❌\n"
                f"• 正答率: {rate:.1f} %"
            )
        else:
            await message.channel.send(f"📊 {message.author.display_name} さんは、まだクイズに挑戦していません！")
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
        
        # 💡 【構文を変えずに追加】管理者向け項目のフィールド
        embed.add_field(
            name="🛠️ 管理者向け機能",
            value="• `!github-repositories` : 開発用GitHubリポジトリのURLを確認する(管理者のみ)",
            inline=False
        )
        
        embed.set_footer(text="大文字・小文字の打ち間違いに注意してね！")
        await message.channel.send(embed=embed)
        return

    # 🛠️ 管理者専用：GitHubリポジトリ確認コマンド
    if message.content == "!github-repositories":
        # 💡 【重要】ここに先ほどコピーしたあなたの「18桁の数字のID」を直接貼り付けてください
        # ※数字なので、前後にクォーテーション（"" や ''）は付けなくて大丈夫です。
        ADMIN_USER_ID = [
            1385634725460316273,  # あなたのID
            1551496753088561238,  # 2人目のID
            1188811877447372881,   # 3人目のID（何人でも増やせます）
        ]
        
        # メッセージを送ってきた人のIDが、管理者IDと一致するかチェック
        if message.author.id == ADMIN_USER_ID:
            await message.channel.send("リポジトリです。https://github.com")
        else:
            # 管理者以外が打った場合は、URLを隠して警告を出す
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
    elif message.content == "!github-repositories":
        await message.channel.send("リポジトリです。https://github.com/hironekoyade/my-discord-app")
        return

@client.event
async def on_ready():
    print(f"ログインしました: {client.user}")

TOKEN = os.getenv("DISCORD_TOKEN")
client.run(TOKEN)
