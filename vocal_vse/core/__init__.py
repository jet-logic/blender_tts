import os
from logging import getLogger
import platform

logger = getLogger(__name__)


class Config:
    config_dir: str
    voices_config_path: str
    default_output_dir: str
    voices: dict

    def __getattr__(self, name):
        f = not name.startswith("_get_") and getattr(self, f"_get_{name}", None)
        if f:
            setattr(self, name, None)
            v = f()
            setattr(self, name, v)
            return v
        try:
            m = super().__getattr__  # type: ignore
        except AttributeError:
            pass
        else:
            return m(name)
        c = self.__class__
        raise AttributeError(
            f"{c.__module__}.{c.__qualname__} has no attribute '{name}'"
        )

    def _get_config_dir(self):
        """Get the standard config directory for the add-on."""
        home = os.path.expanduser("~")
        if os.name == "nt":  # Windows
            config_dir = os.path.join(home, "AppData", "Roaming")
        else:  # Linux/macOS
            config_dir = os.path.join(home, ".config")
        addon_config_dir = os.path.join(config_dir, "vocal_vse")
        os.makedirs(addon_config_dir, exist_ok=True)
        return addon_config_dir

    def _get_voices_config_path(self):
        """Get the path to the voices.toml file."""
        return os.path.join(self.config_dir, "voices.toml")

    def _get_default_output_dir(self):
        """Get the default output directory for audio files.
        Tries to use a '_vocal_vse' folder next to the .blend file.
        Falls back to ~/.cache/vocal_vse if the blend file is unsaved.
        """
        blend_filepath = None
        try:
            import bpy

            blend_filepath = bpy.data.filepath
        except AttributeError:
            pass
        except Exception as e:
            logger.error("{e}", exc_info=True)

        if blend_filepath:
            # Blend file is saved, use directory next to it
            blend_dir = os.path.dirname(blend_filepath)
            narrations_dir = os.path.join(blend_dir, "_vocal_vse")
            try:
                os.makedirs(narrations_dir, exist_ok=True)
                logger.info(f"Using project-specific output dir: {narrations_dir}")
                return narrations_dir
            except OSError as e:
                logger.warning(
                    f"Failed to create project dir '{narrations_dir}', falling back to cache: {e}"
                )

        # Blend file is unsaved or creating project dir failed, use cache
        home = os.path.expanduser("~")
        if platform.system() == "Windows":
            cache_dir = os.path.join(home, "AppData", "Local", "cache")
        else:
            cache_dir = os.path.join(home, ".cache")
        narrations_dir = os.path.join(cache_dir, "vocal_vse")
        os.makedirs(narrations_dir, exist_ok=True)
        logger.info(f"Using fallback cache output dir: {narrations_dir}")
        return narrations_dir

    def _load_voices(self):
        """Load voice profiles from voices.toml."""
        # Check for tomllib (Python 3.11+) or fallback to toml library
        try:
            import tomllib  # Standard library in Python 3.11+
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                logger.error(
                    "Error: Either 'tomllib' (Python 3.11+) or 'tomli' library is required. Please install 'tomli' in Blender's Python environment."
                )
                return {}

        config_path = self.voices_config_path
        if not os.path.exists(config_path):
            create_default_voices_config(config_path)
            logger.info(f"Created default voices config at {config_path}")

        try:
            # tomllib.load requires a binary file handle
            with open(config_path, "rb") as f:
                config = tomllib.load(f)
            return config
        except Exception as e:
            logger.error(
                f"Error loading voices config from {config_path}: {e}", exc_info=True
            )
            return {}

    def _get_voices(self):
        return self._load_voices()

    def reload_voices(self):
        self.voices = self._load_voices()


def create_default_voices_config(config_path):
    """Create a default/example voices.toml file."""
    default_config = """# Example Vocal VSE Configuration
[pyttsx3]
name="pyttsx3 (default)"
synthesizer=".pyttsx3:Synthesizer"
# https://gtts.readthedocs.io/en/latest/module.html#module-gtts.tts
# example : {rate = 150, vioce="jp", volume=0.5}
params={volume = 1.0}

[gtts-default]
name="GTTS (default)"
synthesizer=".gtts:Synthesizer"
# https://gtts.readthedocs.io/en/latest/module.html#module-gtts.tts
# example : {lang = "en", tld="com", slow=True}
params={lang = "en"}
"""
    try:
        with open(config_path, "w") as f:
            f.write(default_config.strip())
    except Exception as e:
        logger.error(f"Error creating default config file: {e}", exc_info=True)


config = Config()
