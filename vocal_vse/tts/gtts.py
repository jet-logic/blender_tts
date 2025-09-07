import os
from . import BaseTTSHandler


class Handler(BaseTTSHandler):
    def __init__(self, lang="en", tld="com", slow=False, **kwargs):
        self.lang = lang
        self.tld = tld
        self.slow = slow

    def synthesize(self, text: str, output_path: str) -> bool:
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            tts = self.gTTS(text=text, lang=self.lang, slow=self.slow, tld=self.tld)
            tts.save(output_path)
            return os.path.exists(output_path)
        except Exception as e:
            print(f"Error synthesizing with gTTS: {e}")
            return False

    def _get_gTTS(self):
        from gtts import gTTS

        return gTTS

    def is_available(self):
        try:
            from gtts import gTTS

            return True
        except:
            pass

        return False
