# tts_narration/core/config.py
import os
import platform


def get_config_directory():
    """Get the standard config directory for the add-on."""
    home = os.path.expanduser("~")
    if os.name == "nt":  # Windows
        config_dir = os.path.join(home, "AppData", "Roaming")
    else:  # Linux/macOS
        config_dir = os.path.join(home, ".config")
    addon_config_dir = os.path.join(config_dir, "blender_tts")
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
            print(
                "Error: Either 'tomllib' (Python 3.11+) or 'tomli' library is required. Please install 'tomli' in Blender's Python environment."
            )
            return {}

    config_path = get_voices_config_path()
    if not os.path.exists(config_path):
        create_default_voices_config(config_path)
        print(f"Created default voices config at {config_path}")

    try:
        # tomllib.load requires a binary file handle
        mode = (
            "rb"
            if hasattr(tomllib, "load") and tomllib is not __import__("tomllib")
            else "r"
        )
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
        return config
    except Exception as e:
        print(f"Error loading voices config from {config_path}: {e}")
        return {}


def create_default_voices_config(config_path):
    """Create a default/example voices.toml file."""
    default_config = """# Example Voice Configuration for Blender TTS Add-on
[pyttsx3-female]
name="Female (default)"
handler = "pyttsx3"
params={volume = 1.0, voice_gender = "female"}

[pyttsx3-male]
handler="pyttsx3"
name="Male (default)"
params={volume = 1.0, voice_gender = "male"}

[gtts-default]
name="GTTS (en)"
handler="gtts"
params={lang = "en"}
"""
    try:
        with open(config_path, "w") as f:
            f.write(default_config.strip())
    except Exception as e:
        print(f"Error creating default config file: {e}")


# Move utility functions here if they don't fit better in file_manager.py
# get_default_output_dir could go here or in a file_manager module
def get_default_output_dir():
    home = os.path.expanduser("~")
    if platform.system() == "Windows":
        cache_dir = os.path.join(home, "AppData", "Local", "cache")
    else:
        cache_dir = os.path.join(home, ".cache")
    narrations_dir = os.path.join(cache_dir, "blender_narrations")
    os.makedirs(narrations_dir, exist_ok=True)
    return narrations_dir
