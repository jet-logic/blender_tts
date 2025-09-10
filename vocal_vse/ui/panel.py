import os
import bpy
from ..core import config as config


class SEQUENCER_PT_tts_panel(bpy.types.Panel):
    bl_label = "Vocal VSE Tools"
    bl_space_type = "SEQUENCE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Tools"

    def draw(self, context):
        layout = self.layout
        selected_sequences = context.selected_sequences  # Cache selected sequences
        voices_path = config.voices_config_path  # Get the path
        # --- Dynamic Voice Profile Buttons ---
        voices_map = config.voices
        if voices_map:
            box = layout.box()
            box.label(text="Generate Narration:")
            # Use a column for buttons
            col = box.column(align=True)
            for profile_key, profile_data in voices_map.items():
                # Create a button for each profile
                # Use the profile name from config, fallback to key
                button_text = profile_data.get("name", profile_key)
                # Create the operator button
                op = col.operator(
                    "sequencer.generate_narration", text=button_text, icon="PLAY_SOUND"
                )  # Add icon
                # Set the voice_profile property for this specific button
                op.voice_profile = profile_key

            # --- Add "Open Config File" button below the generation buttons ---
            # Check if the file exists before adding the operator
            if os.path.exists(voices_path):
                box.operator(
                    "wm.path_open", text="Open voices.toml", icon="TEXT"
                ).filepath = voices_path
            else:
                # Optional: Button to create/edit the file even if it doesn't exist yet
                # This will likely open it in the system's default text editor or prompt
                box.operator(
                    "wm.path_open", text="Create/Edit voices.toml", icon="FILE_TEXT"
                ).filepath = voices_path
            # ---------------------------------------------------------------------

        else:
            # Inform user if no profiles are found
            box = layout.box()
            box.label(text="No TTS profiles found.", icon="ERROR")
            # Provide a way to open the config directory
            box.operator("wm.path_open", text="Open Config Folder").filepath = (
                config.config_dir
            )
        box.operator(
            "vocal_vse.reload_voices_config", text="Reload Voices", icon="FILE_REFRESH"
        )
        # --- Other Tools (conditional on selected text with tts_id) ---
        if any(s.type == "TEXT" and "tts_id" in s for s in selected_sequences):
            layout.separator()  # Add visual separation
            col = layout.column(align=True)
            col.operator(
                "sequencer.refresh_narration",
                icon="FILE_REFRESH",
                text="Refresh Selected",
            )
            col.operator(
                "sequencer.copy_audio_path", icon="COPYDOWN", text="Copy Audio Path"
            )
        # --- General Tools ---
        layout.separator()
        if col := layout.column(align=True):
            col.operator(
                "sequencer.export_narration_list",
                text="Export Narrations",
                icon="EXPORT",
            )
            col.operator(
                "sequencer.cleanup_narration_files",
                icon="TRASH",
                text="Cleanup Unused Files",
            )


# Register function not needed here if handled in main __init__.py
