# tts_narration/operators/cleanup.py
import bpy
import os
from ..core import config as tts_config
from ..core import file_manager  # Or import functions


class VSE_OT_cleanup_narration_files(bpy.types.Operator):
    bl_idname = "sequencer.cleanup_narration_files"
    bl_label = "Cleanup Unused Narration Files"
    bl_options = {"REGISTER"}

    def execute(self, context):
        prefs = context.preferences.addons[
            __name__.split(".")[0]
        ].preferences  # Adjusted
        output_dir = prefs.output_directory or tts_config.get_default_output_dir()

        if not os.path.exists(output_dir):
            self.report({"INFO"}, "Output directory does not exist.")
            return {"CANCELLED"}

        used_ids = set()
        for strip in context.scene.sequence_editor.sequences_all:
            if strip.type == "TEXT" and "tts_id" in strip:
                used_ids.add(strip["tts_id"])

        deleted = 0
        files = file_manager.get_all_narration_files(
            output_dir
        )  # Use imported function
        for f in files:
            filepath = os.path.join(output_dir, f)
            if "_" in f:
                file_id = f.split("_")[1]
                if file_id not in used_ids:
                    try:
                        os.remove(filepath)
                        deleted += 1
                    except OSError as e:
                        self.report({"WARNING"}, f"Could not delete {filepath}: {e}")

        self.report({"INFO"}, f"Deleted {deleted} unused audio files")
        return {"FINISHED"}


# Register/Unregister locally if preferred
