from . import BaseTTSHandler


class Handler(BaseTTSHandler):
    def __init__(self, rate=150, volume=1.0, voice_gender="male", **kwargs):
        self.rate = rate
        self.volume = volume
        self.voice_gender = voice_gender.lower()
        if 0:
            import pyttsx3

            self.engine = pyttsx3.init()

    def synthesize(self, text: str, output_path: str) -> bool:
        self.engine.save_to_file(text, output_path)
        self.engine.runAndWait()  # Important: Waits for file to be written

    def is_available(self):
        return self.engine is not None

    def _get_engine(self):
        engine = None
        try:
            import pyttsx3

            engine = pyttsx3.init()
            engine.setProperty("rate", self.rate)
            engine.setProperty("volume", self.volume)

            if self.voice_gender in ["male", "female"]:
                voices = engine.getProperty("voices")
                # Simple selection - improve if needed
                selected_voice = None
                for v in voices:
                    if self.voice_gender in v.name.lower():
                        selected_voice = v
                        break
                if selected_voice:
                    engine.setProperty("voice", selected_voice.id)
                else:
                    print(
                        f"Warning: Could not find {self.voice_gender} voice for pyttsx3."
                    )
            # Handle other kwargs if necessary for pyttsx3

        except Exception as e:
            print(f"Error initializing pyttsx3 engine: {e}")
            engine = None
        return engine
