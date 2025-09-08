from . import BaseTTSHandler


class Handler(BaseTTSHandler):
    def __init__(self, voice_id="", rate=-1, volume=-1.0, **kwargs):
        self.rate = rate
        self.volume = volume
        self.voice_id = voice_id
        if 0:  # for typing
            import pyttsx3

            self.engine = pyttsx3.init()

    def synthesize(self, text: str, output_path: str):
        self.engine.save_to_file(text, output_path)
        self.engine.runAndWait()  # Important: Waits for file to be written

    def is_available(self):
        return self.engine is not None

    def _get_engine(self):
        import pyttsx3

        engine = pyttsx3.init()
        self.rate >= 0 and engine.setProperty("rate", self.rate)
        self.volume >= 0 and engine.setProperty("volume", self.volume)
        self.voice_id and engine.setProperty("voice", self.voice_id)
        return engine
