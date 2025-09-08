import os
import importlib
import queue
import threading
import traceback  # For better error reporting in threads
from tempfile import gettempdir
from ..core import config as tts_config
from ..core import file_manager
import bpy

# Define message types for clarity (optional but helpful)
MSG_PROGRESS = "progress_update"
MSG_ERROR = "error"
MSG_CRITICAL_ERROR = "critical_error"
MSG_RESULT = "result"  # If sending results via queue
MSG_FINISHED = "finished"
# --- Global state to manage ongoing operations (Consider using a class or bpy.types.PropertyGroup for better management) ---
# For simplicity here, using a module-level dict. In complex add-ons, a PropertyGroup is better.
# Key: unique operation ID, Value: {'thread': Thread, 'progress': int, 'total': int, 'results': list, 'errors': list}
ongoing_operations = {}


def background_synthesis(
    op_id,
    handler_instance,
    selected_sequences,
    output_dir,
    voice_profile_name,
    message_queue,  # Accept the queue
):
    """The actual synthesis work, run in a background thread."""
    # results = [] # If using queue for results, might not need this list locally
    # errors = []  # If using queue for errors, might not need this list locally
    total = len(selected_sequences)
    os.makedirs(output_dir, exist_ok=True)

    try:
        for i, strip in enumerate(selected_sequences):
            if strip.type != "TEXT" or not strip.text.strip():
                continue

            filepath = file_manager.generate_audio_filename(output_dir, strip)
            error_msg = ""
            try:
                handler_instance.synthesize(strip.text, filepath)
                # --- Send Result via Queue ---
                message_queue.put(
                    {
                        "type": MSG_RESULT,
                        "data": {
                            "strip_name": strip.name,
                            "filepath": filepath,
                            "text_strip": strip,
                        },
                    }
                )
                # ----------------------------
            except Exception as e:
                error_msg = f"Error generating audio for '{strip.name}': {e}\n{traceback.format_exc()}"
                # --- Send Error via Queue ---
                message_queue.put({"type": MSG_ERROR, "data": error_msg})
                # ---------------------------

            # --- Send Progress Update via Queue ---
            message_queue.put(
                {
                    "type": MSG_PROGRESS,
                    "data": {
                        "progress": i + 1,
                        "current_strip": strip.name,
                        "has_error": bool(
                            error_msg
                        ),  # Optional: indicate error in progress
                    },
                }
            )
            # -------------------------------------

        # --- Signal Completion via Queue ---
        # Send any final summary errors if needed, or just the finished signal
        # For simplicity, just send finished. Errors were sent individually.
        message_queue.put({"type": MSG_FINISHED})
        # -----------------------------------

    except Exception as e:
        # Handle unexpected errors in the thread
        critical_error_msg = f"Critical error in background thread (ID: {op_id}): {e}\n{traceback.format_exc()}"
        print(critical_error_msg)  # Still print to console for debugging
        # --- Send Critical Error via Queue ---
        message_queue.put({"type": MSG_CRITICAL_ERROR, "data": critical_error_msg})
        # --- Also Signal Finished (even with error) ---
        message_queue.put({"type": MSG_FINISHED})
        # ---------------------------------------------


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
            "results": [],  # Can potentially be removed if using queue for results
            "errors": [],  # Can potentially be removed if using queue for errors
            "critical_error": None,  # Can potentially be removed
            "current_strip": "Starting...",
            "handler_instance": handler_instance,
            "selected_sequences": selected_sequences,
            "voice_profile_name": self.voice_profile,
            # --- Add the Queue ---
            "message_queue": queue.Queue(),
            # ---------------------
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
                ongoing_operations[self._op_id]["message_queue"],
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
        message_queue = op_state["message_queue"]  # Get the queue
        # Check for timer events
        if event.type == "TIMER":
            # --- Process messages from the background thread ---
            finished_flag_received = False
            while True:
                try:
                    # Get message, non-blocking
                    message = message_queue.get_nowait()
                    msg_type = message.get("type")
                    msg_data = message.get("data")

                    if msg_type == MSG_PROGRESS:
                        # Update local op_state view
                        op_state["progress"] = msg_data["progress"]
                        op_state["current_strip"] = msg_data["current_strip"]
                        # Optionally update UI elements if you have them linked to op_state
                        # print(f"Progress: {op_state['progress']}/{op_state['total']} - {op_state['current_strip']}")

                    elif msg_type == MSG_ERROR:
                        # Store error locally in op_state for final reporting
                        op_state["errors"].append(
                            msg_data
                        )  # msg_data is the error string

                    elif msg_type == MSG_CRITICAL_ERROR:
                        # Store critical error
                        op_state["critical_error"] = (
                            msg_data  # msg_data is the error string
                        )

                    elif msg_type == MSG_RESULT:
                        # Store result locally in op_state for final processing
                        op_state["results"].append(
                            msg_data
                        )  # msg_data is the result dict

                    elif msg_type == MSG_FINISHED:
                        # Mark that we received the finished signal
                        finished_flag_received = True
                        # Note: Don't break here immediately, process any remaining messages first
                        # Or handle finished logic after the message loop

                except queue.Empty:
                    # No more messages in the queue right now
                    break

            # --- Check if finished signal was received ---
            if finished_flag_received:
                # Clean up timer
                if hasattr(self, "_timer") and self._timer:
                    context.window_manager.event_timer_remove(self._timer)

                # --- Handle Results (from op_state['results']) ---
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

                # --- Report Final Status (same as before, using errors/critical_error from op_state) ...
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
                # Clean up global state (thread safety for ongoing_operations access still needed here or via lock)
                # Consider using a lock here if direct dict access remains
                # with ongoing_operations_lock: # If you added a lock
                #     if self._op_id in ongoing_operations:
                #         del ongoing_operations[self._op_id]
                # Or if confident about single access point:
                if self._op_id in ongoing_operations:
                    del ongoing_operations[self._op_id]

                return {"FINISHED"}

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
