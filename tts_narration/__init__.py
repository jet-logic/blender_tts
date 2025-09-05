"""
Blender VSE Text-to-Speech Narration Add-on
Generates audio from text strips with unique IDs, refresh, and cleanup.
Supports multiple TTS engines via configurable voice profiles.
"""

bl_info = {
    "name": "VSE Text-to-Speech Narration",
    "author": "Jet-Logic",
    "version": (0, 2, 0),  # Updated version
    "blender": (3, 0, 0),
    "location": "Sequencer > Add > Text-to-Speech",
    "description": "Generate narration from text strips with ID, refresh, and cleanup. Supports multiple TTS engines.",
    "warning": "Requires TTS engine libraries (e.g., pyttsx3, gTTS) installed in Blender's Python environment.",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Sequencer",
}

import bpy
import os
import time
import uuid
import platform
import importlib
import sys

# --- Core Configuration and Utilities ---


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
    try:
        import tomllib
    except ImportError:
        print(
            "Error: 'tomllib' library is required for voice configuration. Please install it in Blender's Python environment."
        )
        return {}

    config_path = get_voices_config_path()
    if not os.path.exists(config_path):
        create_default_voices_config(config_path)
        print(f"Created default voices config at {config_path}")

    try:
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
params={volume = 1.0,voice_gender = "female"}

[pyttsx3-male]
handler="pyttsx3"
name="Male (default)"
params={volume = 1.0,voice_gender = "male"}

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


def get_default_output_dir():
    home = os.path.expanduser("~")
    if platform.system() == "Windows":
        cache_dir = os.path.join(home, "AppData", "Local", "cache")
    else:
        cache_dir = os.path.join(home, ".cache")
    narrations_dir = os.path.join(cache_dir, "blender_narrations")
    os.makedirs(narrations_dir, exist_ok=True)
    return narrations_dir


def get_or_create_strip_id(strip):
    if "tts_id" not in strip:
        new_id = str(uuid.uuid4()).replace("-", "")[:16]
        strip["tts_id"] = new_id
    return strip["tts_id"]


def generate_audio_filename(output_dir, strip):
    strip_id = get_or_create_strip_id(strip)
    timestamp = int(time.time() % 100000)
    return os.path.join(output_dir, f"narration_{strip_id}_{timestamp}.wav")


def find_existing_audio_for_text(scene, text_strip):
    if "tts_id" not in text_strip:
        return None
    target_id = text_strip["tts_id"]
    for strip in scene.sequence_editor.sequences_all:
        if strip.type == "SOUND" and f"Narr_{target_id}" in strip.name:
            return strip
    return None


def get_all_narration_files(output_dir):
    if not os.path.exists(output_dir):
        return []
    return [
        f
        for f in os.listdir(output_dir)
        if f.startswith("narration_") and f.endswith(".wav")
    ]


# --- OPERATORS ---


class VSE_OT_generate_narration(bpy.types.Operator):
    bl_idname = "sequencer.generate_narration"
    bl_label = "Generate Narration from Text"
    bl_options = {"REGISTER", "UNDO"}

    # --- Properties ---
    def get_voice_profiles(self, context):
        voices_config = load_voices_config()
        items = [
            (k, v.get("name", k), f"Voice profile: {k}")
            for (k, v) in voices_config.items()
        ]
        if not items:
            items = [
                (
                    "NONE",
                    "No Profiles Found",
                    "Please configure voices in ~/.config/blender_tts/voices.toml",
                )
            ]
        return items

    # Remove old voice_type enum
    voice_profile: bpy.props.EnumProperty(
        name="Voice Profile",
        description="Select a configured voice profile",
        items=get_voice_profiles,
    )
    # Rate and Volume can be kept for *additional* per-generation control if desired,
    # but the primary settings come from the voice profile config.
    # rate: bpy.props.IntProperty(name="Speech Rate", default=150, min=50, max=300)
    # volume: bpy.props.FloatProperty(name="Volume", default=1.0, min=0.0, max=1.0)

    def execute(self, context):
        # --- Load Configuration ---
        voices_config = load_voices_config()
        if self.voice_profile not in voices_config:
            self.report(
                {"ERROR"}, f"Voice profile '{self.voice_profile}' not found in config."
            )
            return {"CANCELLED"}

        selected_voice_config = voices_config[
            self.voice_profile
        ].copy()  # Work on a copy
        handler_name = selected_voice_config.pop(
            "handler", None
        )  # Remove 'handler' from kwargs
        if not handler_name:
            self.report(
                {"ERROR"},
                f"Handler not specified for voice profile '{self.voice_profile}'.",
            )
            return {"CANCELLED"}

        # --- Preferences and Output ---
        prefs = context.preferences.addons[__name__].preferences
        output_dir = prefs.output_directory or get_default_output_dir()
        os.makedirs(output_dir, exist_ok=True)

        # --- Dynamic Handler Import and Execution ---
        handler_instance = None
        try:
            # Import the handler module from the 'handlers' subpackage
            handler_module_name = f"tts_narration.handlers.{handler_name}"
            if handler_module_name in sys.modules:
                importlib.reload(sys.modules[handler_module_name])
            handler_module = importlib.import_module(handler_module_name)
            HandlerClass = getattr(handler_module, "Handler")

            # Instantiate the handler with config kwargs (excluding 'handler')
            handler_instance = HandlerClass(**selected_voice_config.get("params", {}))

        except ImportError as e:
            self.report(
                {"ERROR"},
                f"Handler module '{handler_module_name}' could not be imported. Is the library installed? Error: {e}",
            )
            return {"CANCELLED"}
        except AttributeError:
            self.report(
                {"ERROR"},
                f"Handler class 'Handler' not found in module '{handler_module_name}'.",
            )
            return {"CANCELLED"}
        except Exception as e:
            self.report({"ERROR"}, f"Error initializing handler '{handler_name}': {e}")
            return {"CANCELLED"}

        # --- Generate Audio for each selected text strip ---
        created = 0
        for strip in context.selected_sequences:
            if strip.type != "TEXT" or not strip.text.strip():
                continue

            filepath = generate_audio_filename(output_dir, strip)
            try:
                # Call the handler's synthesize method
                success = handler_instance.synthesize(strip.text, filepath)

                if success and os.path.exists(filepath):
                    channel = strip.channel + 1
                    frame_start = strip.frame_final_start
                    sound_name = f"Narr_{strip['tts_id']}"

                    old_strip = find_existing_audio_for_text(context.scene, strip)
                    if old_strip:
                        context.scene.sequence_editor.sequences.remove(old_strip)

                    context.scene.sequence_editor.sequences.new_sound(
                        name=sound_name,
                        filepath=filepath,
                        channel=channel,
                        frame_start=frame_start,
                    )
                    created += 1
                    self.report(
                        {"INFO"},
                        f"Generated narration for '{strip.name}' using '{self.voice_profile}'",
                    )
                else:
                    self.report(
                        {"ERROR"},
                        f"Handler failed to generate audio for '{strip.name}' with '{self.voice_profile}'",
                    )

            except Exception as e:
                self.report(
                    {"ERROR"}, f"Error generating audio for '{strip.name}': {e}"
                )

        self.report(
            {"INFO"}, f"Generated {created} narration(s) using '{self.voice_profile}'"
        )
        return {"FINISHED"}

    def invoke(self, context, event):
        # Repopulate enum items in case config changed?
        # self.voice_profile = "" # Reset?
        return context.window_manager.invoke_props_dialog(self)


class VSE_OT_refresh_narration(bpy.types.Operator):
    bl_idname = "sequencer.refresh_narration"
    bl_label = "Refresh Narration"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        # This operator now needs to know which voice profile was used originally.
        # A simple approach: Re-run the main generate operator.
        # A more advanced approach: Store the profile name on the text strip or find the audio strip's source.
        # For simplicity, re-invoke the generate dialog. User needs to select the same profile.
        bpy.ops.sequencer.generate_narration("INVOKE_DEFAULT")
        # Original logic was simpler but also re-invoked the dialog.
        # found = 0
        # regenerated = 0
        # for strip in context.selected_sequences:
        #     if strip.type != "TEXT" or "tts_id" not in strip:
        #         continue
        #     found += 1
        #     old_audio = find_existing_audio_for_text(context.scene, strip)
        #     if old_audio:
        #         # This re-invokes the dialog, user needs to select voice again.
        #         bpy.ops.sequencer.generate_narration("INVOKE_DEFAULT")
        #         regenerated += 1
        # self.report({"INFO"}, f"Refreshed {regenerated} of {found} text strips")
        return {"FINISHED"}


class VSE_OT_cleanup_narration_files(bpy.types.Operator):
    bl_idname = "sequencer.cleanup_narration_files"
    bl_label = "Cleanup Unused Narration Files"
    bl_options = {"REGISTER"}

    def execute(self, context):
        prefs = context.preferences.addons[__name__].preferences
        output_dir = prefs.output_directory or get_default_output_dir()

        if not os.path.exists(output_dir):
            self.report({"INFO"}, "Output directory does not exist.")
            return {"CANCELLED"}

        used_ids = set()
        for strip in context.scene.sequence_editor.sequences_all:
            if strip.type == "TEXT" and "tts_id" in strip:
                used_ids.add(strip["tts_id"])

        deleted = 0
        files = get_all_narration_files(output_dir)
        for f in files:
            filepath = os.path.join(output_dir, f)
            if "_" in f:
                file_id = f.split("_")[1]  # Extract ID from filename: narration_<id>_
                if file_id not in used_ids:
                    try:
                        os.remove(filepath)
                        deleted += 1
                    except OSError as e:
                        self.report({"WARNING"}, f"Could not delete {filepath}: {e}")

        self.report({"INFO"}, f"Deleted {deleted} unused audio files")
        return {"FINISHED"}


class VSE_OT_copy_audio_path(bpy.types.Operator):
    bl_idname = "sequencer.copy_audio_path"
    bl_label = "Copy Audio File Path"

    def execute(self, context):
        for strip in context.selected_sequences:
            if strip.type == "TEXT" and "tts_id" in strip:
                prefs = context.preferences.addons[__name__].preferences
                output_dir = prefs.output_directory or get_default_output_dir()
                files = [
                    f
                    for f in get_all_narration_files(output_dir)
                    if strip["tts_id"] in f
                ]
                if files:
                    latest = sorted(files)[-1]  # Get most recent file
                    path = os.path.join(output_dir, latest)
                    context.window_manager.clipboard = path
                    self.report({"INFO"}, f"Copied: {path}")
                    return {"FINISHED"}
        self.report({"WARNING"}, "No audio path found")
        return {"CANCELLED"}


# --- PANEL ---


class SEQUENCER_PT_tts_panel(bpy.types.Panel):
    bl_label = "TTS Narration Tools"
    bl_space_type = "SEQUENCE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Tools"

    def draw(self, context):
        layout = self.layout
        selected = context.selected_sequences

        col = layout.column(align=True)
        # The operator will show the voice_profile enum in its dialog
        col.operator_menu_enum("sequencer.generate_narration", "voice_profile")
        # Or use operator if you want the dialog on button click:
        # col.operator("sequencer.generate_narration", icon="RENDER_STILL")

        has_text = any(s.type == "TEXT" and "tts_id" in s for s in selected)
        if has_text:
            col.operator("sequencer.refresh_narration", icon="FILE_REFRESH")
            col.operator("sequencer.copy_audio_path", icon="COPYDOWN")

        layout.operator("sequencer.cleanup_narration_files", icon="TRASH")


# --- PREFERENCES ---


class TTSNarrationPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    output_directory: bpy.props.StringProperty(
        name="Output Directory", subtype="DIR_PATH", default=get_default_output_dir()
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "output_directory")
        layout.label(text=f"Default: {get_default_output_dir()}")
        layout.operator("wm.url_open", text="Open Config Folder").url = (
            f"file://{get_config_directory()}"
        )


# --- REGISTER ---

classes = (
    VSE_OT_generate_narration,
    VSE_OT_refresh_narration,
    VSE_OT_cleanup_narration_files,
    VSE_OT_copy_audio_path,
    SEQUENCER_PT_tts_panel,
    TTSNarrationPreferences,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.SEQUENCER_MT_add.append(menu_func)


def unregister():
    bpy.types.SEQUENCER_MT_add.remove(menu_func)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


def menu_func(self, context):
    self.layout.operator_menu_enum("sequencer.generate_narration", "voice_profile")
    # Or: self.layout.operator(VSE_OT_generate_narration.bl_idname)


# Module reload support
if __name__ == "__main__":
    register()
