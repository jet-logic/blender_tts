# tts_narration/operators/generate.py
import bpy
import os
import importlib
import sys
from ..core import config as tts_config
from ..core import file_manager  # Or import functions directly


class VSE_OT_generate_narration(bpy.types.Operator):
    bl_idname = "sequencer.generate_narration"
    bl_label = "Generate Narration from Text"
    bl_options = {"REGISTER", "UNDO"}

    # --- Properties ---
    def get_voice_profiles(self, context):
        voices_config = tts_config.load_voices_config()
        items = [
            (k, v.get("name", k), f"Voice profile: {k}")
            for (k, v) in voices_config.items()
        ]
        if not items:
            items = [
                (
                    "NONE",
                    "No Profiles Found",
                    "Please configure voices in ~/.config/blender_tts/voices.toml",
                )
            ]
        return items

    voice_profile: bpy.props.EnumProperty(
        name="Voice Profile",
        description="Select a configured voice profile",
        items=get_voice_profiles,
    )

    def execute(self, context):
        # --- Load Configuration ---
        voices_config = tts_config.load_voices_config()
        if self.voice_profile not in voices_config:
            self.report(
                {"ERROR"}, f"Voice profile '{self.voice_profile}' not found in config."
            )
            return {"CANCELLED"}

        selected_voice_config = voices_config[self.voice_profile].copy()
        handler_name = selected_voice_config.pop("handler", None)
        if not handler_name:
            self.report(
                {"ERROR"},
                f"Handler not specified for voice profile '{self.voice_profile}'.",
            )
            return {"CANCELLED"}

        # --- Preferences and Output ---
        prefs = context.preferences.addons[
            __name__.split(".")[0]
        ].preferences  # Adjusted for subpackage
        output_dir = prefs.output_directory or tts_config.get_default_output_dir()
        os.makedirs(output_dir, exist_ok=True)

        # --- Dynamic Handler Import and Execution ---
        handler_instance = None
        try:
            handler_module_name = f"tts_narration.handlers.{handler_name}"
            if handler_module_name in sys.modules:
                importlib.reload(sys.modules[handler_module_name])
            handler_module = importlib.import_module(handler_module_name)
            HandlerClass = getattr(handler_module, "Handler")

            handler_instance = HandlerClass(**selected_voice_config.get("params", {}))

        except ImportError as e:
            self.report(
                {"ERROR"},
                f"Handler module '{handler_module_name}' could not be imported. Is the library installed? Error: {e}",
            )
            return {"CANCELLED"}
        except AttributeError:
            self.report(
                {"ERROR"},
                f"Handler class 'Handler' not found in module '{handler_module_name}'.",
            )
            return {"CANCELLED"}
        except Exception as e:
            self.report({"ERROR"}, f"Error initializing handler '{handler_name}': {e}")
            return {"CANCELLED"}

        # --- Generate Audio ---
        created = 0
        for strip in context.selected_sequences:
            if strip.type != "TEXT" or not strip.text.strip():
                continue

            filepath = file_manager.generate_audio_filename(
                output_dir, strip
            )  # Use imported function
            try:
                success = handler_instance.synthesize(strip.text, filepath)

                if success and os.path.exists(filepath):
                    channel = strip.channel + 1
                    frame_start = strip.frame_final_start
                    sound_name = f"Narr_{file_manager.get_or_create_strip_id(strip)}"  # Use imported function

                    old_strip = file_manager.find_existing_audio_for_text(
                        context.scene, strip
                    )  # Use imported function
                    if old_strip:
                        context.scene.sequence_editor.sequences.remove(old_strip)

                    context.scene.sequence_editor.sequences.new_sound(
                        name=sound_name,
                        filepath=filepath,
                        channel=channel,
                        frame_start=frame_start,
                    )
                    created += 1
                    self.report(
                        {"INFO"},
                        f"Generated narration for '{strip.name}' using '{self.voice_profile}'",
                    )
                else:
                    self.report(
                        {"ERROR"},
                        f"Handler failed to generate audio for '{strip.name}' with '{self.voice_profile}'",
                    )

            except Exception as e:
                self.report(
                    {"ERROR"}, f"Error generating audio for '{strip.name}': {e}"
                )

        self.report(
            {"INFO"}, f"Generated {created} narration(s) using '{self.voice_profile}'"
        )
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


# Register function for this operator if needed separately, or handle in main __init__.py
# def register():
#     bpy.utils.register_class(VSE_OT_generate_narration)
# def unregister():
#     bpy.utils.unregister_class(VSE_OT_generate_narration)
