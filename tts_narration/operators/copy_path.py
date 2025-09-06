# tts_narration/operators/copy_path.py
import bpy
import os
from ..core import config as tts_config
from ..core import file_manager  # Or import functions


class VSE_OT_copy_audio_path(bpy.types.Operator):
    bl_idname = "sequencer.copy_audio_path"
    bl_label = "Copy Audio File Path"

    def execute(self, context):
        for strip in context.selected_sequences:
            if strip.type == "TEXT" and "tts_id" in strip:
                prefs = context.preferences.addons[
                    __name__.split(".")[0]
                ].preferences  # Adjusted
                output_dir = (
                    prefs.output_directory or tts_config.get_default_output_dir()
                )
                files = [
                    f
                    for f in file_manager.get_all_narration_files(
                        output_dir
                    )  # Use imported function
                    if strip["tts_id"] in f
                ]
                if files:
                    latest = sorted(files)[-1]
                    path = os.path.join(output_dir, latest)
                    context.window_manager.clipboard = path
                    self.report({"INFO"}, f"Copied: {path}")
                    return {"FINISHED"}
        self.report({"WARNING"}, "No audio path found")
        return {"CANCELLED"}


# Register/Unregister locally if preferred
