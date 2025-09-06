# tts_narration/__init__.py
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
from .operators import generate, refresh, cleanup, copy_path
from .ui import panel, preferences  # Be careful with preferences.bl_idname

from .operators.generate import VSE_OT_generate_narration
from .operators.refresh import VSE_OT_refresh_narration
from .operators.cleanup import VSE_OT_cleanup_narration_files
from .operators.copy_path import VSE_OT_copy_audio_path
from .ui.panel import SEQUENCER_PT_tts_panel
from .ui.preferences import TTSNarrationPreferences

# List of modules containing classes to register
modules = [
    generate,
    refresh,
    cleanup,
    copy_path,
    panel,
    preferences,  # Ensure bl_idname in preferences.py is correct
]

# Collect all classes from the modules for registration
classes = []
for module in modules:
    # Assumes each module has classes named like VSE_OT_*, SEQUENCER_PT_*, etc.
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        # if isinstance(attr, type):
        #     print("attr", attr)
        if isinstance(attr, type) and (
            issubclass(attr, bpy.types.Operator)
            or issubclass(attr, bpy.types.Panel)
            or issubclass(attr, bpy.types.AddonPreferences)
            or issubclass(attr, bpy.types.PropertyGroup)
        ):  # Add other types if needed
            if (
                attr.__module__ == module.__name__
            ):  # Only register classes defined in this module
                classes.append(attr)
# print(classes)


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
