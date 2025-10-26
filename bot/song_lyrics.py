import random

# Personalized message templates for tagall - various moods and styles
# Each will be filled with user's name/mention

PERSONALIZED_MESSAGES = [
    # Funny/Comedy
    "😂 {name} जी का entry! सब हाथ जोड़ लो, बड़े लोग आ गए हैं! 🙏",
    "🤣 {name} को देखो यार, इतना cute कैसे हो सकता है कोई? 😍💕",
    "😆 {name} महाराज की तरफ से फ्री की biryani! अरे मज़ाक है 🍛😂",
    "🤪 {name} का swag देखो, Netflix को bhi competition दे रहे हैं! 📺✨",
    "😅 {name} बोले तो एकदम dhinchak! Full on masti mode activated 🔥🎉",
    
    # Flirty
    "💘 {name}, तुम्हारी smile के आगे सूरज भी फीका पड़ जाए 🌞✨",
    "😘 {name} की ek nazar = दिल का हाल बेकरार! 💕💫",
    "🥰 {name} जैसा खूबसूरत इंसान मिलना मुश्किल है! Lucky us! 🍀💖",
    "😍 {name}, तुम्हारी आवाज़ सुनकर दिल की धड़कन तेज़ हो जाती है! 💓🎵",
    "💝 {name} को देखा और बस... दिल ले गए! Chori hogyi ji! 👀💕",
    
    # Friendship/Wholesome
    "🤗 {name} जैसे दोस्त मिल जाएं तो life set है! Forever वाली friendship 💙✨",
    "🫂 {name}, तुम हो तो सब मुश्किलें आसान हो जाती हैं! Thank you yaar 🙏💕",
    "😊 {name} के बिना group तो अधूरा है! Jaan ho tum is group ki 💚",
    "🌟 {name} जैसा loyal friend? Rare hai boss, rare hai! 🔥👑",
    "💛 {name}, तुम्हारे साथ बिताए हर पल यादगार हैं! Memories for life 📸✨",
    
    # Sarcasm/Tease
    "😏 {name} भाई, itna attitude? Hawa mein udne ka time aagaya kya? ✈️😂",
    "🙄 {name} को लगता है वो special हैं... और sach mein hain bhi! 👑😎",
    "😌 {name} का swag देखो, जैसे Bollywood star हों! Drama queen/king alert 🎬💅",
    "🤨 {name}, online toh ho but reply nahi? Bhoot ban gaye kya? 👻😂",
    "😆 {name} की photography skills = बस Mona Lisa की smile! Mysterious 🤳😅",
    
    # Emotional/Personal
    "🥺 {name}, तुम्हारा साथ सबसे खूबसूरत gift है! Grateful hun 💕🙏",
    "😢 {name} के बिना कुछ अच्छा नहीं लगता... Miss you always 💔✨",
    "🌈 {name}, तुमने मेरी ज़िंदगी में रंग भर दिए! Thank you 🎨💖",
    "💫 {name} जैसा समझदार इंसान rare है! You're special 🌟💙",
    "🙏 {name}, तुम्हारी हर बात दिल को छू जाती है! Real one ❤️✨",
    
    # Relatable/Teenage
    "😭 {name} भी procrastinate करते हैं? Us moment! Welcome to the club 📚😂",
    "🎮 {name} gaming kar rahe? Mujhe bhi le chalo yaar! Level up together 🕹️🔥",
    "☕ {name} को coffee bhi pasand है? Soul connect ho gaya! ☕💕",
    "📱 {name} bhi 3 baje tak phone chalate ho? Same energy! 😴📲",
    "🍕 {name} + Pizza + Late night talks = Perfect combo! 🌙✨",
    
    # Meme/Gen-Z Style  
    "💀 {name} literally slaying! Main toh mar hi gaya bro 🔥😂",
    "✨ {name} is giving main character energy! Period. 💅👑",
    "🚀 {name} ka vibe? Out of this world! Literally unstoppable 🌌💫",
    "👁️👄👁️ {name} ne pura game change kar diya! Respect++",
    "🎯 {name} hits different! No cap, fr fr 💯🔥",
    
    # Sad/Emotional
    "💔 {name}, तुम्हारी कमी खलती है यार... Come back soon 🥺💙",
    "😔 {name} के बिना सब सूना सा लगता है... Miss the good times 🌧️💕",
    "🌙 {name}, रातें तुम्हारी यादों में गुज़र जाती हैं... 💭✨",
    "🥀 {name} की खामोशी भी बहुत कुछ कह जाती है... Silent but special 💫",
    "🕊️ {name}, तुम्हारी बातें दिल को सुकून देती हैं... Peace 🙏💙",
    
    # Motivational/Positive
    "🔥 {name} unstoppable है! Keep shining star ⭐💪",
    "💪 {name} जैसा fighter मिलना मुश्किल है! Warrior vibes 🛡️👑",
    "⚡ {name} की energy देखो! Sabko charge kar dete हैं 🔋✨",
    "🌟 {name}, तुम्हारा confidence सबको inspire करता है! Keep it up 💯🎯",
    "🎯 {name} goals achieve kar lenge! Believe in yourself 🚀💙",
    
    # Random Fun
    "🦄 {name} is literally a unicorn! Rare and magical ✨💖",
    "🎭 {name} ka drama? Netflix se zyada interesting! 📺😂",
    "🌮 {name} + Food = Match made in heaven! Foodie gang 🍔💕",
    "🎨 {name} creative af! Artist vibes 100% 🖌️✨",
    "🎵 {name} ki playlist? Fire hai boss! Music lover 🔥🎧",
    
    # Sweet/Kind
    "🌸 {name} जैसा sweet person? Rare gem hai! 💎💕",
    "🍯 {name} की मीठी बातें > सब cheezein! Honey you are 🐝✨",
    "💗 {name}, तुम्हारा दिल सोने जैसा है! Pure soul 🙏💫",
    "🌺 {name} की kindness सबको मोह लेती है! Beautiful inside out 🌈💖",
    "🎀 {name} is a blessing! Lucky to have you around 🍀💙"
]

# Funny, teasing, engaging questions for tagall
TAGALL_QUESTIONS = [
    "Bhai teri relationship ka kya hua? 💔",
    "Aur kaisi hai yaar? 😏",
    "Bhai teri wali to loyal thi na fir kya hua? 🤔",
    "Kyu nhi ho rhi padhai? 📚😂",
    "Bhai gym kab join karoge? 💪😅",
    "Aaj kal online kyun nahi dikhte? 👻",
    "Crush ka reply aaya ki nahi? 💘",
    "Exam mein kitne number aaye the? 🎯",
    "Netflix pe kya dekh rahe ho aaj kal? 📺",
    "Subah uthte ho ya seedha lunch pe? ☀️😴",
    "Last kab nahaye the bhai? 🚿😂",
    "Crush ko propose kab karoge? 💕",
    "Instagram pe kitne followers hai? 📱",
    "Pizza या Burger? Choose one! 🍕🍔",
    "Kal raat ko kya kar rahe the? 🌙👀",
    "Apna ex miss hota hai? 💭",
    "Sachi bolo, crush kon hai? 😍",
    "2 AM tak phone pe kya karte ho? 📲",
    "Salary kitni milti hai bhai? 💰😏",
    "Shaadi kab karoge? 💍",
    "Coffee ya Tea? ☕",
    "Job lag gayi ki nahi? 💼",
    "Ghar waale pareshan kar rahe hain? 😅",
    "Aaj kal khaana kiske saath khate ho? 🍽️",
    "Last kab kisi se jhagda hua? 😤",
    "Sach bolo, kitni baar breakup hua? 💔",
    "Apna type kya hai? 😏💕",
    "Last kab kisi ko impress kiya? 😎",
    "Favorite meme template kya hai? 😂",
    "Kitne baje sote ho raat ko? 🌙",
    "Morning person ho ya night owl? 🦉",
    "Apni sabse badi galti kya thi? 🤦",
    "Kya tumhe bhoot pe vishwas hai? 👻",
    "Pehli salary pe kya liya tha? 💸",
    "Sabse embarrassing moment kya tha? 😳",
    "Phone ka screen time kitna hai? 📱👀",
    "Last kab jhooth bola tha? 🤥",
    "Apna childhood crush yaad hai? 💭💕",
    "Sabse zyada kya spend karte ho? 💰",
    "Gym jaate ho ya ghar pe workout? 🏋️",
    "Cooking aati hai? 👨‍🍳",
    "Pet paalte ho? Kya naam hai? 🐕",
    "Height kitni hai sachhi? 📏😏",
    "Gaadi hai ki nahi? 🚗",
    "Sabse favorite song kaunsa hai? 🎵",
    "LinkedIn pe active ho? 💼",
    "Last kab kisi party mein gaye? 🎉",
    "Apna biggest flex kya hai? 💅",
    "Sapne mein kya dekhte ho? 💭😴",
    "Subah breakfast karte ho? 🍳",
    "Kitni languages aati hain? 🗣️",
    "Favorite web series konsi hai? 📺",
    "Kabhi fail hue exams mein? 📝",
    "Apna lucky number kya hai? 🍀",
    "Last vacation kab gaye the? ✈️",
    "Kitne dost hain sachche wale? 👥",
    "Apna biggest fear kya hai? 😱",
    "Shaadi fixed hai kya? 💍😏",
    "Kitne din se haircut nahi karwaya? ✂️",
    "Mom-dad se kitni baar daant padte ho? 😅",
    "Piggy bank mein kitne paise hain? 🐷💰",
    "Best compliment jo mili ho? 🥰"
]

def get_personalized_message_template():
    """Get a random personalized message template with {name} placeholder."""
    return random.choice(PERSONALIZED_MESSAGES)

def get_tagall_question():
    """Get a random funny question for tagall."""
    return random.choice(TAGALL_QUESTIONS)
