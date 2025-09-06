"""
Blender VSE Text-to-Speech Narration Add-on
Generates audio from text strips with unique IDs, refresh, and cleanup.
Supports multiple TTS engines via configurable voice profiles.
"""

bl_info = {
    "name": "VSE Text-to-Speech Narration",
    "author": "Jet-Logic",
    "version": (0, 2, 1),
    "blender": (3, 0, 0),
    "location": "Sequencer > Add > Text-to-Speech",
    "description": "Generate narration from text strips with ID, refresh, and cleanup. Supports multiple TTS engines.",
    "warning": "Requires TTS engine libraries (e.g., pyttsx3, gTTS) and 'toml' installed in Blender's Python environment.",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Sequencer",
}

import bpy

# Import submodules
from .operators.generate import VSE_OT_generate_narration
from .operators.refresh import VSE_OT_refresh_narration
from .operators.cleanup import VSE_OT_cleanup_narration_files
from .operators.copy_path import VSE_OT_copy_audio_path
from .ui.panel import SEQUENCER_PT_tts_panel
from .ui.preferences import TTSNarrationPreferences

# Collect all classes from the modules for registration
classes = [
    VSE_OT_generate_narration,
    VSE_OT_refresh_narration,
    VSE_OT_cleanup_narration_files,
    VSE_OT_copy_audio_path,
    SEQUENCER_PT_tts_panel,
    TTSNarrationPreferences,
]


def register():
    # print("Registering TTS Narration Add-on...")
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
            # print(f"Registered: {cls}")
        except Exception as e:
            print(f"Failed to register {cls}: {e}")

    bpy.types.SEQUENCER_MT_add.append(menu_func)


def unregister():
    # print("Unregistering TTS Narration Add-on...")
    bpy.types.SEQUENCER_MT_add.remove(menu_func)
    # Unregister in reverse order
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
            # print(f"Unregistered: {cls}")
        except Exception as e:
            print(f"Failed to unregister {cls}: {e}")


def menu_func(self, context):
    self.layout.operator_menu_enum("sequencer.generate_narration", "voice_profile")


# Module reload support (optional, useful for development)
if __name__ == "__main__":
    register()
