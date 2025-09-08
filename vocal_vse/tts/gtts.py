from . import SynthesizerBase


class Synthesizer(SynthesizerBase):
    def __init__(self, lang="en", tld="com", slow=False, timeout=0, **kwargs):
        self.lang = lang
        self.tld = tld
        self.slow = slow
        self.timeout = timeout
        if 0:
            from gtts import gTTS

            self.gTTS = gTTS

    def synthesize(self, text: str, output_path: str):
        self.gTTS(
            text=text,
            lang=self.lang,
            slow=self.slow,
            tld=self.tld,
            timeout=self.timeout or None,
        ).save(output_path)

    def _get_gTTS(self):
        from gtts import gTTS

        return gTTS

    def is_available(self):
        return self.gTTS is not None
