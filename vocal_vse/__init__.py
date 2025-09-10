bl_info = {
    "name": "Vocal VSE",
    "author": "Jet-Logic",
    "version": (0, 3, 1),
    "blender": (3, 0, 0),
    "location": "Sequencer > Add > Text-to-Speech",
    "description": "Generate narration from text strips with ID, refresh, and cleanup. Supports multiple TTS engines.",
    "warning": "Requires TTS engine libraries (e.g., pyttsx3, gTTS) and 'tomli' installed in Blender's Python environment.",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Sequencer",
}

try:
    import bpy
except ImportError:
    pass
else:
    from logging import getLogger

    logger = getLogger(__name__)
    # Import submodules
    from .operators.generate import VSE_OT_generate_narration
    from .operators.refresh import VSE_OT_refresh_narration
    from .operators.cleanup import VSE_OT_cleanup_narration_files
    from .operators.copy_path import VSE_OT_copy_audio_path
    from .operators.export_list import VSE_OT_export_narration_list
    from .operators.reload_voices import VOCAL_OT_reload_voices_config
    from .ui.panel import SEQUENCER_PT_tts_panel
    from .ui.preferences import VocalVSEPreferences

    # Collect all classes from the modules for registration
    classes = [
        VSE_OT_generate_narration,
        VSE_OT_refresh_narration,
        VSE_OT_cleanup_narration_files,
        VSE_OT_copy_audio_path,
        VSE_OT_export_narration_list,
        VOCAL_OT_reload_voices_config,
        SEQUENCER_PT_tts_panel,
        VocalVSEPreferences,
    ]

    def register():
        logger.info("Registering Vocal VSE Add-on...")
        for cls in classes:
            try:
                bpy.utils.register_class(cls)
            except Exception as e:
                logger.error(
                    f"Failed to register {cls}: {e}", exc_info=True
                )  # <-- Use logger.error

    def unregister():
        logger.info("Unregistering Vocal VSE Add-on...")
        # --- UNREGISTER IN REVERSE ORDER ---
        for cls in reversed(classes):
            try:
                bpy.utils.unregister_class(cls)
            except Exception as e:
                logger.error(f"Failed to unregister {cls}: {e}", exc_info=True)

    # Module reload support (optional, useful for development)
    if __name__ == "__main__":
        register()
