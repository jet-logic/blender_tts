import bpy
import os
import json
from ..core import config as tts_config
from ..core import file_manager


class VSE_OT_export_narration_list(bpy.types.Operator):
    """Export a list of TTS narrations (Text Strip ID -> Audio File) as JSON"""

    bl_idname = "sequencer.export_narration_list"
    bl_label = "Export Narration List (JSON)"
    bl_options = {"REGISTER", "UNDO"}
    bl_description = "Export a list of text strips, their IDs, text content, and generated audio files to a JSON file"

    # --- Properties ---
    filepath: bpy.props.StringProperty(
        name="File Path",
        description="Path to the export JSON file",
        default="",
        subtype="FILE_PATH",
    )
    filename_ext: bpy.props.StringProperty(default=".json", options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        return context.scene.sequence_editor is not None

    def invoke(self, context, event):
        prefs = context.preferences.addons["vocal_vse"].preferences
        default_output_dir = (
            prefs.output_directory or tts_config.get_default_output_dir()
        )

        blend_name = (
            bpy.path.basename(bpy.data.filepath) if bpy.data.filepath else "untitled"
        )
        default_filename = f"{blend_name}_narration_list.json"

        self.filepath = os.path.join(default_output_dir, default_filename)

        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        if not self.filepath:
            self.report({"ERROR"}, "No file path specified.")
            return {"CANCELLED"}

        if not self.filepath.endswith(".json"):
            self.filepath += ".json"

        # Determine audio output directory
        prefs = context.preferences.addons["vocal_vse"].preferences
        audio_output_dir = prefs.output_directory or tts_config.get_default_output_dir()

        # Ensure the target directory for the export file exists
        export_dir = os.path.dirname(self.filepath)
        if export_dir:
            os.makedirs(export_dir, exist_ok=True)

        # Gather data
        narration_data = []
        # Iterate through ALL sequences to find text strips with tts_id
        for strip in context.scene.sequence_editor.sequences_all:
            if strip.type == "TEXT" and "tts_id" in strip:
                tts_id = strip["tts_id"]
                strip_name = strip.name
                # --- Include the text content ---
                strip_text = strip.text
                # -----------------------------
                frame_start = strip.frame_final_start
                frame_end = strip.frame_final_end

                # Find corresponding audio files
                all_narration_files = file_manager.get_all_narration_files(
                    audio_output_dir
                )
                matching_files = [
                    f for f in all_narration_files if f.startswith(f"voc_{tts_id}_")
                ]
                matching_files.sort()  # Sort for consistency

                # Add entry for this text strip
                narration_data.append(
                    {
                        "text_strip_name": strip_name,
                        "tts_id": tts_id,
                        # --- Add text content to the entry ---
                        "text_content": strip_text,
                        # -----------------------------------
                        "frame_start": frame_start,
                        "frame_end": frame_end,
                        "audio_files": matching_files,
                    }
                )

        # Sort data for consistent output
        narration_data.sort(key=lambda x: x["tts_id"])

        # Export to JSON
        try:
            export_data = {
                "export_info": {
                    "blend_file": bpy.data.filepath or "Unsaved",
                    "export_timestamp": bpy.context.scene.frame_current,  # Simple timestamp
                    "audio_output_directory": audio_output_dir,
                },
                "narrations": narration_data,
            }

            with open(self.filepath, "w", encoding="utf-8") as jsonfile:
                json.dump(export_data, jsonfile, indent=4, ensure_ascii=False)

            self.report({"INFO"}, f"Narration list exported to '{self.filepath}'")
            return {"FINISHED"}
        except Exception as e:
            self.report({"ERROR"}, f"Failed to export narration list: {e}")
            return {"CANCELLED"}
