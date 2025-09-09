import os
import tempfile
import unittest


class TestTTS(unittest.TestCase):

    def test_pyttsx3_synthesize(self):
        from vocal_vse.tts.pyttsx3 import Synthesizer

        h = Synthesizer()
        voices = h.engine.getProperty("voices")
        for voice in voices:
            print(
                f"ID: {voice.id}, Name: {voice.name}, Gender: {voice.gender}, Languages: {voice.languages}"
            )

        with tempfile.NamedTemporaryFile(
            prefix="voc1_", delete=False, suffix=".wav"
        ) as f:
            f.close()
            Synthesizer().synthesize(
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
            prefix="jpx_", delete=False, suffix=".wav"
        ) as f:
            f.close()
            Synthesizer("jpx/ja").synthesize(
                "Furuike ya/ Kawazu tobikomu/ Mizu no oto", f.name
            )
            self.assertTrue(os.path.exists(f.name))


if __name__ == "__main__":
    unittest.main()
