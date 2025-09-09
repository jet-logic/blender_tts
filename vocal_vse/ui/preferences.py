import bpy
from ..core import (
    config as tts_config,
)  # For get_config_directory, get_default_output_dir


class VocalVSEPreferences(bpy.types.AddonPreferences):
    bl_idname = "vocal_vse"
    # bl_idname for AddonPreferences should match the name of the add-on's main package/folder.
    # If your add-on folder is named 'vocal_vse', this should likely be 'vocal_vse'.
    # This class can be kept for potential future preferences or actions,
    # even if it currently has no properties.

    def draw(self, context):
        layout = self.layout
        # Inform the user about the default output location
        layout.label(
            text=f"Audio files are saved to: {tts_config.get_default_output_dir()}",
            icon="INFO",  # Add an icon for better visibility
        )
        layout.operator("wm.url_open", text="Open Config Folder").url = (
            f"file://{tts_config.get_config_directory()}"  # Use imported function
        )


# Register/Unregister locally if preferred
