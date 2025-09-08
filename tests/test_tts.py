import os
import tempfile
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

        with tempfile.NamedTemporaryFile(
            prefix="voc1_", delete=False, suffix=".wav"
        ) as f:
            f.close()
            Handler("bnt/sw").synthesize(
                r"""Beautiful is better than ugly.
                Explicit is better than implicit.
                Simple is better than complex.
                Complex is better than complicated.
                Flat is better than nested.
                Sparse is better than dense.
                Readability counts.""",
                f.name,
            )
            self.assertTrue(os.path.exists(f.name))
        with tempfile.NamedTemporaryFile(
            prefix="voc2_", delete=False, suffix=".wav"
        ) as f:
            f.close()
            Handler().synthesize("The quick brown fox jumped over the lazy dog", f.name)
            self.assertTrue(os.path.exists(f.name))


if __name__ == "__main__":
    unittest.main()
