import bpy
from ..core import config as config


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
            text=f"Audio files are saved to: {config.default_output_dir}",
            icon="INFO",  # Add an icon for better visibility
        )
        layout.operator("wm.path_open", text="Open Save Folder").filepath = (
            config.default_output_dir
        )
        layout.operator("wm.path_open", text="Open Config Folder").filepath = (
            config.config_dir
        )


# Register/Unregister locally if preferred
