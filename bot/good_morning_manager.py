import random
from typing import List

class GoodMorningManager:
    """Manages good morning wishes with motivational quotes."""
    
    def __init__(self):
        self.quotes = [
            "Success is not final, failure is not fatal: it is the courage to continue that counts.",
            "Believe you can and you're halfway there.",
            "The only way to do great work is to love what you do.",
            "Don't watch the clock; do what it does. Keep going.",
            "The future belongs to those who believe in the beauty of their dreams.",
            "Strive not to be a success, but rather to be of value.",
            "The only impossible journey is the one you never begin.",
            "Everything you've ever wanted is on the other side of fear.",
            "Success usually comes to those who are too busy to be looking for it.",
            "Don't be afraid to give up the good to go for the great.",
            "I find that the harder I work, the more luck I seem to have.",
            "Success is walking from failure to failure with no loss of enthusiasm.",
            "The way to get started is to quit talking and begin doing.",
            "It does not matter how slowly you go as long as you do not stop.",
            "Your limitation—it's only your imagination.",
            "Push yourself, because no one else is going to do it for you.",
            "Great things never come from comfort zones.",
            "Dream it. Wish it. Do it.",
            "Success doesn't just find you. You have to go out and get it.",
            "The harder you work for something, the greater you'll feel when you achieve it.",
            "Dream bigger. Do bigger.",
            "Don't stop when you're tired. Stop when you're done.",
            "Wake up with determination. Go to bed with satisfaction.",
            "Do something today that your future self will thank you for.",
            "Little things make big days.",
            "It's going to be hard, but hard does not mean impossible.",
            "Don't wait for opportunity. Create it.",
            "Sometimes we're tested not to show our weaknesses, but to discover our strengths.",
            "The key to success is to focus on goals, not obstacles.",
            "Dream it. Believe it. Build it.",
        ]
        
        self.hindi_quotes = [
            "सफलता का कोई शॉर्टकट नहीं होता, मेहनत ही इसकी चाबी है।",
            "कठिन समय में ही असली योद्धा बनते हैं।",
            "अपने सपनों को पूरा करने के लिए पहले उन्हें देखना जरूरी है।",
            "हर नई सुबह एक नया अवसर लेकर आती है।",
            "जो लोग हार नहीं मानते, वही विजेता बनते हैं।",
            "आज की मेहनत कल की सफलता की नींव है।",
            "विश्वास रखो, मेहनत करो, सफलता तुम्हारी होगी।",
            "असफलता सफलता की पहली सीढ़ी है।",
            "जो आज की कीमत समझता है, वही कल का निर्माता बनता है।",
            "सपने वो नहीं जो नींद में आएं, सपने वो हैं जो नींद उड़ा दें।",
        ]
    
    def get_random_quote(self, language: str = 'english') -> str:
        """Get a random motivational quote."""
        if language == 'hindi':
            return random.choice(self.hindi_quotes)
        return random.choice(self.quotes)
    
    def generate_good_morning_message(self, language: str = 'english') -> str:
        """Generate a beautiful good morning message with motivational quote."""
        quote = self.get_random_quote(language)
        
        if language == 'hindi':
            message = f"""
╔═══════════════════════════════╗
║   🌅 **शुभ प्रभात** 🌅   ║
╚═══════════════════════════════╝

🌸 नमस्ते! एक नए दिन की शुरुआत 🌸

✨ **आज का प्रेरक विचार:**
💭 _{quote}_

🌞 आज का दिन शुभ हो! 🌞

━━━━━━━━━━━━━━━━━━━━━━
💝 यह संदेश [Aman](https://t.me/Aman_PersonalBot) की ओर से
【~@DrQuizRobot】
"""
        else:
            message = f"""
╔═══════════════════════════════╗
║   🌅 **Good Morning!** 🌅   ║
╚═══════════════════════════════╝

🌸 Wishing you a beautiful day ahead! 🌸

✨ **Today's Inspirational Quote:**
💭 _{quote}_

🌞 Have a wonderful day! 🌞

━━━━━━━━━━━━━━━━━━━━━━
💝 This message is from [Aman](https://t.me/Aman_PersonalBot)
【~@DrQuizRobot】
"""
        
        return message.strip()

# Global instance
good_morning_manager = GoodMorningManager()
