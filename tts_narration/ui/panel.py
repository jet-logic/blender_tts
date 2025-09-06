# tts_narration/ui/panel.py

import bpy
from ..core import config as tts_config  # Import for loading config


class SEQUENCER_PT_tts_panel(bpy.types.Panel):
    bl_label = "TTS Narration Tools"
    bl_space_type = "SEQUENCE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Tools"

    def draw(self, context):
        layout = self.layout
        selected_sequences = context.selected_sequences  # Cache selected sequences

        # --- Dynamic Voice Profile Buttons ---
        voices_config = tts_config.load_voices_config()
        if voices_config:
            box = layout.box()
            box.label(text="Generate Narration:")
            # Use a column for buttons
            col = box.column(align=True)
            for profile_key, profile_data in voices_config.items():
                # Create a button for each profile
                # Use the profile name from config, fallback to key
                button_text = profile_data.get("name", profile_key)
                # Create the operator button
                op = col.operator(
                    "sequencer.generate_narration", text=button_text, icon="PLAY_SOUND"
                )  # Add icon
                # Set the voice_profile property for this specific button
                op.voice_profile = profile_key
        else:
            # Inform user if no profiles are found
            box = layout.box()
            box.label(text="No TTS profiles found.", icon="ERROR")
            # Provide a way to open the config directory
            box.operator("wm.url_open", text="Open Config Folder").url = (
                f"file://{tts_config.get_config_directory()}"
            )

        # --- Other Tools (conditional on selected text with tts_id) ---
        has_text_with_id = any(
            s.type == "TEXT" and "tts_id" in s for s in selected_sequences
        )
        if has_text_with_id:
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
        # Add the Export button
        col.operator_menu_enum(
            "sequencer.export_narration_list", "export_format"
        )  # Shows submenu for format

        # # --- Cleanup (always available) ---
        # layout.separator()
        # layout.operator(
        #     "sequencer.cleanup_narration_files",
        #     icon="TRASH",
        #     text="Cleanup Unused Files",
        # )

        # --- General Tools ---
        layout.separator()
        box = layout.box()
        box.label(text="General Tools:")
        col = box.column(align=True)
        # --- Add the Export button ---
        col.operator(
            "sequencer.export_narration_list",
            text="Export Narration List",
            icon="EXPORT",
        )
        # -----------------------------
        col.operator(
            "sequencer.cleanup_narration_files",
            icon="TRASH",
            text="Cleanup Unused Files",
        )


# Register function not needed here if handled in main __init__.py
