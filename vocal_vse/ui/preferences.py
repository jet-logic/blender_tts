import bpy
from ..core import (
    config as tts_config,
)  # For get_config_directory, get_default_output_dir


class VocalVSEPreferences(bpy.types.AddonPreferences):
    bl_idname = "vocal_vse"
    # bl_idname for AddonPreferences should match the name of the add-on's main package/folder.
    # If your add-on folder is named 'vocal_vse', this should likely be 'vocal_vse'.

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
