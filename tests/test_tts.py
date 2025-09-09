import os
from pathlib import Path
import tempfile
import unittest

tmp = Path(tempfile.gettempdir())


class TestTTS(unittest.TestCase):

    def test_pyttsx3_synthesize(self):
        from vocal_vse.tts.pyttsx3 import Synthesizer

        # voices = Synthesizer().engine.getProperty("voices")
        # for voice in voices:
        #     print(
        #         f"ID: {voice.id}, Name: {voice.name}, Gender: {voice.gender}, Languages: {voice.languages}"
        #     )
        f = str(tmp / "voc1_jb1wu1.wav")
        Synthesizer().synthesize(
            r"""Beautiful is better than ugly.
                Explicit is better than implicit.
                Simple is better than complex.
                Complex is better than complicated.
                Flat is better than nested.
                Sparse is better than dense.
                Readability counts.""",
            f,
        )
        self.assertTrue(os.path.exists(f))

    def test_cmd_synthesize_gtts(self):
        from vocal_vse.tts.cmd import Synthesizer

        synt = Synthesizer(
            "gtts-cli", ["--lang", "fr", "--output", "{output_path}", "-"]
        )
        self.assertTrue(synt.is_available())
        print(synt.shutil.which(synt.bin))
        synt.synthesize("Bonjour le monde", str(tmp / "gtts-cli-fr.wav"))

    def test_cmd_synthesize_espeak(self):
        from vocal_vse.tts.cmd import Synthesizer

        synt = Synthesizer(
            "espeak-ng", ["-v", "ja", "-w", "{output_path}", "-b", "1", "--stdin"]
        )
        print(synt.shutil.which(synt.bin))
        self.assertTrue(synt.is_available())
        synt.synthesize("こんにちは ", str(tmp / "espeak-ja.wav"))

    def test_cmd_synthesize_kokoro(self):
        from vocal_vse.tts.cmd import Synthesizer

        synt = Synthesizer(
            "kokoro-tts",
            [
                "-",
                "{output_path}",
                "--voice",
                "am_puck",
                # "--model",
                # "kokoro-v1.0.onnx",
                # "--voices",
                # "voices-v1.0.bin",
            ],
            cwd="~/.config/kokoro-tts",
        )

        # --speed <float>     Set speech speed (default: 1.0)
        # --lang <str>        Set language (default: en-us)
        # --voice <str>       Set voice or blend voices (default: interactive selection)

        print(synt.shutil.which(synt.bin))
        self.assertTrue(synt.is_available())
        synt.synthesize(
            "Kokoro is an open-weight TTS model with 82 million parameters.",
            str(tmp / "kokoro.wav"),
        )


if __name__ == "__main__":
    unittest.main()
