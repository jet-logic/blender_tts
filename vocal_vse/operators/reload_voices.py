import bpy
from ..core import config as config


class VOCAL_OT_reload_voices_config(bpy.types.Operator):
    bl_idname = "vocal_vse.reload_voices_config"
    bl_label = "Reload Vocal VSE Config"
    bl_description = "Reload the voices.toml configuration file"

    def execute(self, context):
        config.reload_voices()  # Call the reload function
        # Trigger a redraw of regions if needed immediately
        for area in context.screen.areas:
            if area.type == "SEQUENCE_EDITOR":
                area.tag_redraw()
        self.report({"INFO"}, "Vocal VSE configuration reloaded.")
        return {"FINISHED"}
