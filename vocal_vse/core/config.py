import os
import platform
from logging import getLogger

logger = getLogger(__name__)


def get_config_directory():
    """Get the standard config directory for the add-on."""
    home = os.path.expanduser("~")
    if os.name == "nt":  # Windows
        config_dir = os.path.join(home, "AppData", "Roaming")
    else:  # Linux/macOS
        config_dir = os.path.join(home, ".config")
    addon_config_dir = os.path.join(config_dir, "vocal_vse")
    os.makedirs(addon_config_dir, exist_ok=True)
    return addon_config_dir


def get_voices_config_path():
    """Get the path to the voices.toml file."""
    config_dir = get_config_directory()
    return os.path.join(config_dir, "voices.toml")


def load_voices_config():
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

    config_path = get_voices_config_path()
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


def create_default_voices_config(config_path):
    """Create a default/example voices.toml file."""
    default_config = """# Example Vocal VSE Configuration
[pyttsx3]
name="pyttsx3 (default)"
synthesizer=".pyttsx3:Synthesizer"
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


def get_default_output_dir():
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
