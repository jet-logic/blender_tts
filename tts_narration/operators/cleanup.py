# tts_narration/operators/cleanup.py
import bpy
import os
from ..core import config as tts_config
from ..core import file_manager  # Or import functions


class VSE_OT_cleanup_narration_files(bpy.types.Operator):
    bl_idname = "sequencer.cleanup_narration_files"
    bl_label = "Cleanup Unused Narration Files"
    bl_options = {"REGISTER"}
    bl_description = (
        "Delete narration audio files not linked to text strips "
        "and not used by any sound strip in the VSE"
    )

    def execute(self, context):
        prefs = context.preferences.addons[__name__.split(".")[0]].preferences
        output_dir = prefs.output_directory or tts_config.get_default_output_dir()

        if not os.path.exists(output_dir):
            self.report({"INFO"}, "Output directory does not exist.")
            return {"CANCELLED"}

        # --- 1. Get paths of audio files currently used by SOUND strips ---
        used_sound_strip_paths = set()
        for strip in context.scene.sequence_editor.sequences_all:
            if strip.type == "SOUND":
                # Get the absolute path of the sound file used by the strip
                # bpy.path.abspath handles relative paths (e.g., //audio.wav)
                abs_filepath = bpy.path.abspath(
                    strip.sound.filepath, library=strip.sound.library
                )
                # Normalize the path for comparison
                normalized_path = os.path.normpath(abs_filepath)
                used_sound_strip_paths.add(normalized_path)
                # Debug: print(f"Sound strip '{strip.name}' uses: {normalized_path}")

        # --- 2. Get paths of all narration files in the output directory ---
        all_narration_filenames = file_manager.get_all_narration_files(output_dir)
        all_narration_paths = {
            os.path.normpath(os.path.join(output_dir, filename))
            for filename in all_narration_filenames
        }
        # Debug: print(f"All narration paths: {all_narration_paths}")

        # --- 3. Identify unused narration files ---
        # Files in all_narration_paths but NOT in used_sound_strip_paths
        unused_narration_paths = all_narration_paths - used_sound_strip_paths
        # Debug: print(f"Unused narration paths: {unused_narration_paths}")

        # --- 4. Delete the unused files ---
        deleted_count = 0
        for file_path in unused_narration_paths:
            try:
                os.remove(file_path)
                # Debug: print(f"Deleted: {file_path}")
                deleted_count += 1
            except OSError as e:
                self.report({"WARNING"}, f"Could not delete {file_path}: {e}")

        self.report(
            {"INFO"},
            f"Deleted {deleted_count} unused narration file(s) from '{output_dir}'.",
        )
        # Optionally, report if no files were deleted
        # if deleted_count == 0:
        #     self.report({"INFO"}, "No unused narration files found.")
        return {"FINISHED"}
