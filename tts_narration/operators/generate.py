# tts_narration/operators/generate.py
import bpy
import os
import importlib
import sys
from ..core import config as tts_config
from ..core import file_manager


class VSE_OT_generate_narration(bpy.types.Operator):
    bl_idname = "sequencer.generate_narration"
    bl_label = "Generate Narration from Text"
    bl_options = {"REGISTER", "UNDO"}
    # Optional: Add a more descriptive bl_description
    # bl_description = "Generate narration using a configured voice profile"

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

    @classmethod
    def poll(cls, context):
        # Only allow operator if VSE is active and text strips are selected
        return context.scene.sequence_editor is not None and any(
            s.type == "TEXT" for s in context.selected_sequences
        )

    def invoke(self, context, event):
        # Check if voice_profile is pre-set (e.g., from panel button)
        # and if it's a valid profile from the current config.
        voices_config = tts_config.load_voices_config()
        if (
            self.voice_profile
            and self.voice_profile != "NONE"  # Check for our 'None' value
            and self.voice_profile in voices_config
        ):
            # If set and valid, execute directly without showing dialog
            return self.execute(context)
        else:
            # If not set, invalid, or called generically (e.g. from search),
            # show the dialog for user selection.
            return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        # --- Validate voice_profile ---
        voices_config = tts_config.load_voices_config()
        # Double-check validity, even if invoked directly
        if (
            not self.voice_profile
            or self.voice_profile == "NONE"
            or self.voice_profile not in voices_config
        ):
            self.report({"ERROR"}, f"Invalid or no voice profile selected.")
            return {"CANCELLED"}

        # --- Rest of execute logic (remains largely the same) ---
        selected_voice_config = voices_config[self.voice_profile].copy()
        handler_name = selected_voice_config.pop("handler", None)
        if not handler_name:
            self.report(
                {"ERROR"},
                f"Handler not specified for voice profile '{self.voice_profile}'.",
            )
            return {"CANCELLED"}

        # --- Preferences and Output ---
        # Correctly get the addon name for preferences
        prefs = context.preferences.addons["tts_narration"].preferences
        output_dir = prefs.output_directory or tts_config.get_default_output_dir()
        os.makedirs(output_dir, exist_ok=True)

        # --- Dynamic Handler Import and Execution ---
        handler_instance = None
        try:
            if handler_name.startswith("."):
                handler_module_name = f"tts_narration.handlers{handler_name}"
            else:
                handler_module_name = handler_name
            # Reload logic might need adjustment based on dev needs
            # if handler_module_name in sys.modules:
            #     importlib.reload(sys.modules[handler_module_name])
            handler_module = importlib.import_module(handler_module_name)
            HandlerClass = getattr(handler_module, "Handler")

            # Pass params from the config
            handler_params = selected_voice_config.get("params", {})
            handler_instance = HandlerClass(**handler_params)

            # Check if handler is available (NEW CHECK)
            if not handler_instance.is_available():
                self.report(
                    {"ERROR"},
                    f"Handler '{handler_name}' is not available. Please check dependencies (e.g., install required library).",
                )
                return {"CANCELLED"}

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

        # --- Generate Audio for selected strips ---
        created = 0
        # Ensure output directory exists (redundant check, but safe)
        os.makedirs(output_dir, exist_ok=True)

        for strip in context.selected_sequences:
            if strip.type != "TEXT" or not strip.text.strip():
                continue

            filepath = file_manager.generate_audio_filename(output_dir, strip)
            try:
                success = handler_instance.synthesize(strip.text, filepath)

                if success and os.path.exists(filepath):
                    channel = strip.channel + 1
                    frame_start = strip.frame_final_start
                    sound_name = f"Narr_{file_manager.get_or_create_strip_id(strip)}"

                    old_strip = file_manager.find_existing_audio_for_text(
                        context.scene, strip
                    )
                    if old_strip:
                        context.scene.sequence_editor.sequences.remove(old_strip)

                    context.scene.sequence_editor.sequences.new_sound(
                        name=sound_name,
                        filepath=filepath,
                        channel=channel,
                        frame_start=frame_start,
                    )
                    created += 1
                    # Consider less verbose reporting for many strips?
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

        if created > 0:
            self.report(
                {"INFO"},
                f"Generated {created} narration(s) using '{self.voice_profile}'",
            )
        # else report handled inside loop or by checks
        return {"FINISHED"}
