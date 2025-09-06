# tts_narration/ui/panel.py
import bpy


class SEQUENCER_PT_tts_panel(bpy.types.Panel):
    bl_label = "TTS Narration Tools"
    bl_space_type = "SEQUENCE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Tools"

    def draw(self, context):
        layout = self.layout
        selected = context.selected_sequences

        col = layout.column(align=True)
        col.operator_menu_enum("sequencer.generate_narration", "voice_profile")

        has_text = any(s.type == "TEXT" and "tts_id" in s for s in selected)
        if has_text:
            col.operator("sequencer.refresh_narration", icon="FILE_REFRESH")
            col.operator("sequencer.copy_audio_path", icon="COPYDOWN")

        layout.operator("sequencer.cleanup_narration_files", icon="TRASH")


# Register/Unregister locally if preferred
