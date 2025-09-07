import unittest


class TestTTS(unittest.TestCase):

    def test_pyttsx3_synthesize(self):
        from vocal_vse.tts.pyttsx3 import Handler

        h = Handler()
        voices = h.engine.getProperty("voices")
        for voice in voices:
            print(
                f"ID: {voice.id}, Name: {voice.name}, Gender: {voice.gender}, Languages: {voice.languages}"
            )
        r = h.synthesize("Good Day Sunshine", "/tmp/voc1.wav")
        self.assertTrue(r)
        r = h.synthesize(
            "'The quick brown fox jumped over the lazy dog",
            "/tmp/voc2.wav",
        )
        self.assertTrue(r)


if __name__ == "__main__":
    unittest.main()
