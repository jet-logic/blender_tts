import os
import importlib
import threading
import traceback  # For better error reporting in threads
from tempfile import gettempdir
from ..core import config as tts_config
from ..core import file_manager
import bpy

# --- Global state to manage ongoing operations (Consider using a class or bpy.types.PropertyGroup for better management) ---
# For simplicity here, using a module-level dict. In complex add-ons, a PropertyGroup is better.
# Key: unique operation ID, Value: {'thread': Thread, 'progress': int, 'total': int, 'results': list, 'errors': list}
ongoing_operations = {}


def background_synthesis(
    op_id, handler_instance, selected_sequences, output_dir, voice_profile_name
):
    """The actual synthesis work, run in a background thread."""
    results = []
    errors = []
    os.makedirs(output_dir, exist_ok=True)  # Ensure exists before thread work

    try:
        for i, strip in enumerate(selected_sequences):
            if strip.type != "TEXT" or not strip.text.strip():
                continue

            filepath = file_manager.generate_audio_filename(output_dir, strip)
            error_msg = ""
            try:
                # This is the potentially long-running call
                handler_instance.synthesize(strip.text, filepath)
                results.append(
                    {
                        "strip_name": strip.name,
                        "filepath": filepath,
                        "text_strip": strip,  # Pass the strip object reference
                    }
                )
            except Exception as e:
                error_msg = f"Error generating audio for '{strip.name}': {e}\n{traceback.format_exc()}"
                errors.append(error_msg)

            # Update global state (needs thread safety consideration)
            # Simple approach: assume single operation for now, or use locks/queues
            if op_id in ongoing_operations:
                ongoing_operations[op_id]["progress"] = i + 1
                ongoing_operations[op_id]["current_strip"] = strip.name
                if error_msg:
                    ongoing_operations[op_id]["errors"].append(
                        error_msg
                    )  # Append errors

        # Signal completion
        if op_id in ongoing_operations:
            ongoing_operations[op_id]["finished"] = True
            ongoing_operations[op_id]["results"] = results
            ongoing_operations[op_id]["errors"].extend(errors)  # Add any final errors

    except Exception as e:
        # Handle unexpected errors in the thread
        critical_error = (
            f"Critical error in background thread: {e}\n{traceback.format_exc()}"
        )
        print(critical_error)  # Print to console
        if op_id in ongoing_operations:
            ongoing_operations[op_id]["finished"] = True
            ongoing_operations[op_id]["critical_error"] = critical_error


class VSE_OT_generate_narration(bpy.types.Operator):
    bl_idname = "sequencer.generate_narration"
    bl_label = "Generate Narration (Vocal VSE)"
    bl_options = {
        "REGISTER"
    }  # Remove UNDO if adding strips in thread is complex, or handle it carefully
    bl_description = (
        "Generate narration using a configured voice profile (non-blocking)"
    )

    # --- Properties (same as before) ---
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
                    "Please configure voices in ~/.config/vocal_vse/voices.toml",
                )
            ]
        return items

    voice_profile: bpy.props.EnumProperty(
        name="Voice Profile",
        description="Select a configured voice profile",
        items=get_voice_profiles,
    )

    # --- Unique ID for this operation instance ---
    _op_id: str = None

    @classmethod
    def poll(cls, context):
        return context.scene.sequence_editor is not None and any(
            s.type == "TEXT" for s in context.selected_sequences
        )

    def invoke(self, context, event):
        # --- Validate voice_profile (similar to before) ---
        voices_config = tts_config.load_voices_config()
        if (
            not self.voice_profile
            or self.voice_profile == "NONE"
            or self.voice_profile not in voices_config
        ):
            self.report({"ERROR"}, f"Invalid or no voice profile selected.")
            return {"CANCELLED"}

        selected_voice_config = voices_config[self.voice_profile].copy()
        handler_name = selected_voice_config.pop("handler", None)
        if not handler_name:
            self.report(
                {"ERROR"},
                f"Handler not specified for voice profile '{self.voice_profile}'.",
            )
            return {"CANCELLED"}

        # --- Initialize Handler (similar to before, but check availability synchronously) ---
        handler_instance = None
        try:
            if handler_name.startswith("."):
                handler_module_name = f"vocal_vse.tts{handler_name}"
            else:
                handler_module_name = handler_name
            handler_module = importlib.import_module(handler_module_name)
            HandlerClass = getattr(handler_module, "Handler")
            handler_params = selected_voice_config.get("params", {})
            handler_instance = HandlerClass(**handler_params)

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

        # --- Prepare for Background Execution ---
        import uuid

        self._op_id = str(uuid.uuid4())
        selected_sequences = [
            s for s in context.selected_sequences if s.type == "TEXT" and s.text.strip()
        ]

        if not selected_sequences:
            self.report({"WARNING"}, "No valid text strips selected for generation.")
            return {"CANCELLED"}

        # Store initial state
        ongoing_operations[self._op_id] = {
            "thread": None,
            "progress": 0,
            "total": len(selected_sequences),
            "finished": False,
            "results": [],
            "errors": [],
            "critical_error": None,
            "current_strip": "Starting...",
            "handler_instance": handler_instance,  # Store handler instance
            "selected_sequences": selected_sequences,  # Store sequences
            "voice_profile_name": self.voice_profile,  # Store profile name for reporting
        }

        # --- Start Background Thread ---
        thread = threading.Thread(
            target=background_synthesis,
            args=(
                self._op_id,
                handler_instance,
                selected_sequences,
                context.preferences.addons["vocal_vse"].preferences.output_directory
                or tts_config.get_default_output_dir(),
                self.voice_profile,
            ),
            name=f"VocalVSE_{self._op_id}",
        )
        thread.daemon = True  # Dies when main program exits
        ongoing_operations[self._op_id]["thread"] = thread
        thread.start()

        # --- Start Modal Timer ---
        # This will call modal() every 0.1 seconds to check progress
        self._timer = context.window_manager.event_timer_add(0.1, window=context.window)
        context.window_manager.modal_handler_add(self)

        self.report(
            {"INFO"},
            f"Starting narration generation ({len(selected_sequences)} strips) using '{self.voice_profile}'...",
        )
        return {"RUNNING_MODAL"}  # Important: Operator now runs modally

    def modal(self, context, event):
        # Check if the operation ID is still valid
        if self._op_id not in ongoing_operations:
            # Shouldn't happen, but clean up timer
            if hasattr(self, "_timer") and self._timer:
                context.window_manager.event_timer_remove(self._timer)
            return {"CANCELLED"}

        op_state = ongoing_operations[self._op_id]

        # Check for timer events
        if event.type == "TIMER":
            # Update progress in UI (e.g., via a progress bar if you add one, or just report occasionally)
            # For now, we mostly wait for completion
            # You could add a progress indicator in the panel or report every N strips
            # if op_state['progress'] % 5 == 0 or op_state['progress'] == op_state['total']:
            #     print(f"Progress: {op_state['progress']}/{op_state['total']} - {op_state['current_strip']}")

            # Check if the background thread has finished
            if op_state["finished"]:
                # Clean up timer
                if hasattr(self, "_timer") and self._timer:
                    context.window_manager.event_timer_remove(self._timer)

                # --- Handle Results ---
                results = op_state["results"]
                errors = op_state["errors"]
                critical_error = op_state.get("critical_error")
                voice_profile_name = op_state["voice_profile_name"]

                # Add sound strips to the VSE (must be done on the main thread!)
                created_count = 0
                for result in results:
                    strip_name = result["strip_name"]
                    filepath = result["filepath"]
                    text_strip = result["text_strip"]  # Get the original strip object

                    try:
                        # Add sound strip logic (similar to before, but using stored data)
                        channel = text_strip.channel + 1
                        frame_start = text_strip.frame_final_start
                        sound_name = (
                            f"Voc_{file_manager.get_or_create_strip_id(text_strip)}"
                        )

                        # Remove old strip if exists
                        old_strip = file_manager.find_existing_audio_for_text(
                            context.scene, text_strip
                        )
                        if old_strip:
                            context.scene.sequence_editor.sequences.remove(old_strip)

                        # Add new sound strip
                        context.scene.sequence_editor.sequences.new_sound(
                            name=sound_name,
                            filepath=filepath,
                            channel=channel,
                            frame_start=frame_start,
                        )
                        created_count += 1
                        # Report individual success if desired (might be verbose)
                        # self.report({"INFO"}, f"Added audio for '{strip_name}'")
                    except Exception as e:
                        error_msg = f"Failed to add sound strip for '{strip_name}': {e}"
                        errors.append(error_msg)
                        print(error_msg)  # Log to console

                # --- Report Final Status ---
                if critical_error:
                    self.report(
                        {"ERROR"}, f"Critical error during generation: {critical_error}"
                    )
                elif errors:
                    error_summary = "; ".join(errors[:3])  # Show first few errors
                    with open(os.path.join(gettempdir(), "vocal_vse.log"), "a") as o:
                        for x in errors:
                            o.write(x)
                            o.write("\n")

                    if len(errors) > 3:
                        error_summary += f"... (and {len(errors) - 3} more errors)"
                    self.report(
                        {"ERROR"},
                        f"Generation completed with errors ({len(errors)}). {error_summary}",
                    )
                else:
                    self.report(
                        {"INFO"},
                        f"Generated {created_count} narration(s) using '{voice_profile_name}'",
                    )

                # Clean up global state
                del ongoing_operations[self._op_id]

                return {"FINISHED"}  # Modal operator finished

        # Check for user cancellation (ESC key)
        elif event.type in {"ESC"}:
            # Attempt to stop the thread (note: stopping threads in Python is tricky)
            # Setting a flag and checking it inside the thread loop is the common way
            # For simplicity here, we'll just clean up the timer and state
            # The thread might continue running in the background until it finishes naturally
            if hasattr(self, "_timer") and self._timer:
                context.window_manager.event_timer_remove(self._timer)
            if self._op_id in ongoing_operations:
                del ongoing_operations[self._op_id]  # Remove state
            self.report({"WARNING"}, "Narration generation cancelled by user.")
            return {"CANCELLED"}

        # Continue running modally
        return {"PASS_THROUGH"}  # Let other events pass through

    # Optional: execute method if called without invoke (e.g., from script)
    def execute(self, context):
        # Fallback or direct execution - might block if not handled carefully
        # It's better to force use of invoke for UI interaction
        self.report(
            {"ERROR"}, "Please use the UI panel or search menu to invoke this operator."
        )
        return {"CANCELLED"}
