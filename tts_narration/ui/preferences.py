# tts_narration/ui/preferences.py
import bpy
from ..core import (
    config as tts_config,
)  # For get_config_directory, get_default_output_dir


class TTSNarrationPreferences(bpy.types.AddonPreferences):
    bl_idname = "tts_narration"  # This needs careful handling, see below.

    # bl_idname for AddonPreferences should match the name of the add-on's main package/folder.
    # If your add-on folder is named 'tts_narration', this should likely be 'tts_narration'.
    # bl_idname = "tts_narration" # Preferred if add-on folder is 'tts_narration'

    output_directory: bpy.props.StringProperty(
        name="Output Directory",
        subtype="DIR_PATH",
        default=tts_config.get_default_output_dir(),  # Use imported function
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "output_directory")
        layout.label(
            text=f"Default: {tts_config.get_default_output_dir()}"
        )  # Use imported function
        layout.operator("wm.url_open", text="Open Config Folder").url = (
            f"file://{tts_config.get_config_directory()}"  # Use imported function
        )


# Register/Unregister locally if preferred
