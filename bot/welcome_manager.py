import json
import random
from pathlib import Path

class WelcomeManager:
    def __init__(self, data_file='data/welcome_groups.json'):
        self.data_file = data_file
        self.enabled_groups = self._load_data()
        
        self.shayaris = [
            "दोस्ती में न कोई शर्त है, न कोई उम्मीद,\nबस इतना है कि साथ हमेशा निभाया जाए। 💫",
            
            "तेरी मुस्कान से रोशन है मेरी दुनिया,\nतू आ गया तो महफ़िल सजी है। 😊✨",
            
            "टूटे हुए दिलों की भी एक कहानी होती है,\nहर ज़ख्म के साथ एक नई जवानी होती है। 💔",
            
            "शरारत तो हमारी फितरत है यारों,\nबिना मस्ती के जिंदगी अधूरी है! 😜🎉",
            
            "दोस्त वो नहीं जो साथ हो सिर्फ खुशियों में,\nदोस्त वो है जो गम में भी साथ खड़ा हो। 🤝❤️",
            
            "मोहब्बत एक एहसास है जो बयां नहीं होता,\nदिल से दिल का रिश्ता जुबां नहीं होता। 💕",
            
            "तुम्हारी आँखों में खो जाऊं ऐसा मेरा हुनर है,\nतुम्हारी बातों में डूब जाऊं ये मेरा शौक़ है। 😍💖",
            
            "जिंदगी में कभी हार मत मानना दोस्त,\nहर अंधेरे के बाद सवेरा होता है। 🌅💪",
            
            "चिढ़ाना तो हमारा काम है,\nहंसाना हमारा धर्म है! 😄🎭",
            
            "यारों की महफ़िल में जो मज़ा है,\nवो किसी और जगह नहीं! 🎊👯",
            
            "तेरे बिना अधूरी है ये ज़िन्दगी मेरी,\nतू ही मेरी मंज़िल है, तू ही सफ़र मेरा। 💑",
            
            "दर्द छुपाकर मुस्कुराना सीख लिया,\nटूटकर भी जीना सीख लिया। 🥀",
            
            "दिल तो बच्चा है जी, हर बात पे रूठ जाता है,\nपर तुम्हारी एक मुस्कान से मान जाता है। 😊💝",
            
            "दोस्ती में ना कोई रुतबा है, ना कोई फासला,\nबस एक सच्चा साथ और खूबसूरत रिश्ता है। 🌟",
            
            "तुझसे मिलकर लगा जैसे खुदा मिल गया,\nतेरे साथ का हर पल जन्नत सा लगा। 🌹",
            
            "मस्ती में जीना सीखो यारों,\nज़िन्दगी बस एक बार मिलती है! 🎈🎪",
            
            "तन्हाई में तेरी यादें साथ देती हैं,\nआँसू भी कभी-कभी मुस्कुराहट देती हैं। 🌙💭",
            
            "फ़्लर्ट करना तो हमारी आदत है,\nदिल जीतना हमारा हुनर है! 😏💘",
            
            "हर नया दिन नई उम्मीद लेकर आता है,\nज़िन्दगी फिर से मुस्कुराना सिखा जाता है। 🌈",
            
            "दोस्त बनना आसान है,\nदोस्ती निभाना मुश्किल, हम दोनों कर लेंगे! 🤗"
        ]
    
    def _load_data(self):
        try:
            Path('data').mkdir(exist_ok=True)
            if Path(self.data_file).exists():
                with open(self.data_file, 'r') as f:
                    return set(json.load(f))
        except:
            pass
        return set()
    
    def _save_data(self):
        try:
            Path('data').mkdir(exist_ok=True)
            with open(self.data_file, 'w') as f:
                json.dump(list(self.enabled_groups), f)
        except Exception as e:
            print(f"Error saving welcome data: {e}")
    
    def enable_welcome(self, group_id):
        group_id = str(group_id)
        if group_id not in self.enabled_groups:
            self.enabled_groups.add(group_id)
            self._save_data()
            return True
        return False
    
    def disable_welcome(self, group_id):
        group_id = str(group_id)
        if group_id in self.enabled_groups:
            self.enabled_groups.remove(group_id)
            self._save_data()
            return True
        return False
    
    def is_welcome_enabled(self, group_id):
        return str(group_id) in self.enabled_groups
    
    def get_random_shayari(self):
        return random.choice(self.shayaris)

welcome_manager = WelcomeManager()
