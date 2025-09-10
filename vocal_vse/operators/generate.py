import os
import importlib
import queue
import concurrent.futures
import threading
import traceback  # For better error reporting in threads
from logging import getLogger
from tempfile import gettempdir
from ..core import config as config, file_manager
import bpy

logger = getLogger(__name__)
# --- Message Types for Queue Communication ---
MSG_PROGRESS = "progress_update"
MSG_ERROR = "error"
MSG_CRITICAL_ERROR = "critical_error"
MSG_RESULT = "result"
MSG_FINISHED = "finished"
# ---------------------------------------------


def background_synthesis_task(
    handler_instance,
    selected_sequences,
    output_dir,  # Use the output_dir passed in, not context
    message_queue,
    stop_event,  # threading.Event to check for cancellation
):
    """
    The actual synthesis work, run in a thread managed by ThreadPoolExecutor.
    Communicates back via message_queue.
    Checks stop_event periodically to allow early exit.
    """
    total = len(selected_sequences)
    os.makedirs(output_dir, exist_ok=True)

    try:
        for i, strip in enumerate(selected_sequences):
            # --- Check for cancellation ---
            if stop_event.is_set():
                logger.warning(f"Background task was cancelled.")
                # It's good practice to signal finish even if cancelled
                # so the main thread knows the worker is done.
                message_queue.put({"type": MSG_FINISHED})
                return  # Exit the function early
            # --------------------------------

            if strip.type != "TEXT" or not strip.text.strip():
                continue

            filepath = file_manager.generate_audio_filename(output_dir, strip)
            error_msg = ""
            try:
                # This is the potentially long-running call
                handler_instance.synthesize(strip.text, filepath)
                # --- Send Result via Queue ---
                message_queue.put(
                    {
                        "type": MSG_RESULT,
                        "data": {
                            "strip_name": strip.name,
                            "filepath": filepath,
                            "text_strip": strip,  # Pass the strip object reference
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

        # --- Signal Completion (if not cancelled) ---
        # If loop finished normally, send finished signal
        # Redundant check, but safe
        if not stop_event.is_set():
            message_queue.put({"type": MSG_FINISHED})
        # ------------------------------------------

    except Exception as e:
        # Handle unexpected errors in the thread
        critical_error_msg = (
            f"Critical error in background task: {e}\n{traceback.format_exc()}"
        )
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

    # --- Properties ---
    def get_voice_profiles(self, context):
        voices_config = config.voices
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

    # --- Instance variables for state (instead of global dict) ---
    # These will be initialized in invoke()
    # executor: concurrent.futures.ThreadPoolExecutor
    # future: concurrent.futures.Future
    # message_queue: queue.Queue
    # stop_event: threading.Event
    # total: int
    # voice_profile_name: str
    # collected_results: list # Store results from queue
    # collected_errors: list  # Store errors from queue
    # critical_error: str     # Store critical error
    # task_finished: bool     # Custom flag from MSG_FINISHED
    # selected_sequences: list # Store for use in modal

    @classmethod
    def poll(cls, context):
        return context.scene.sequence_editor is not None and any(
            s.type == "TEXT" for s in context.selected_sequences
        )

    def invoke(self, context, event):
        # --- Validate voice_profile ---
        voices_config = config.voices
        if (
            not self.voice_profile
            or self.voice_profile == "NONE"
            or self.voice_profile not in voices_config
        ):
            self.report({"ERROR"}, "Invalid or no voice profile selected.")
            return {"CANCELLED"}

        selected_voice_config = voices_config[self.voice_profile].copy()
        synthesizer_spec = selected_voice_config.pop("synthesizer", None)
        if not synthesizer_spec:
            self.report(
                {"ERROR"},
                f"Synthesizer not specified for voice profile '{self.voice_profile}'.",
            )
            return {"CANCELLED"}

        # --- Initialize Synthesizer ---
        handler_instance = None
        try:
            # --- Parse synthesizer spec ---
            # Format: "module_name:ClassName" or ".relative_module:ClassName"
            if ":" in synthesizer_spec:
                module_part, class_part = synthesizer_spec.rsplit(":", 1)
            else:
                # Fallback if format is incorrect or old, assume Handler class
                # This helps with backward compatibility if needed, though spec requires :
                self.report(
                    {"ERROR"},
                    f"Invalid synthesizer spec '{synthesizer_spec}' for profile '{self.voice_profile}'. Expected format 'module:ClassName'.",
                )
                return {"CANCELLED"}

            if module_part.startswith("."):
                handler_module_name = f"vocal_vse.tts{module_part}"
            else:
                handler_module_name = synthesizer_spec

            # --- Import and Instantiate ---

            handler_module = importlib.import_module(handler_module_name)
            SynthesizerClass = getattr(handler_module, class_part)
            handler_params = selected_voice_config.get("params", {})
            handler_instance = SynthesizerClass(**handler_params)

            if not handler_instance.is_available():
                self.report(
                    {"ERROR"},
                    f"Synthesizer '{synthesizer_spec}' is not available. Please check dependencies (e.g., install required library).",
                )
                return {"CANCELLED"}

        except Exception as e:
            self.report(
                {"ERROR"}, f"Error initializing handler '{synthesizer_spec}': {e}"
            )
            return {"CANCELLED"}

        # --- Prepare for Background Execution ---
        import uuid  # For unique executor name if needed

        self.selected_sequences = [
            s for s in context.selected_sequences if s.type == "TEXT" and s.text.strip()
        ]

        if not self.selected_sequences:
            self.report({"WARNING"}, "No valid text strips selected for generation.")
            return {"CANCELLED"}

        # --- Setup ThreadPoolExecutor and Communication ---
        # Create a ThreadPoolExecutor.
        # Using max_workers=1 ensures one task at a time per operator instance.
        # Consider if a shared executor (e.g., module-level) is better for multiple concurrent ops.
        # Include a unique part in the thread name for debugging.
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=1, thread_name_prefix=f"VocalVSE_Task_{uuid.uuid4().hex[:8]}"
        )

        # Create a queue for messages from the background task
        self.message_queue = queue.Queue()

        # Create an event to signal the background task to stop
        self.stop_event = threading.Event()

        # Store other necessary state on self
        self.total = len(self.selected_sequences)
        self.voice_profile_name = self.voice_profile  # Store profile name for reporting
        # Initialize lists/dict to collect data from the queue in modal
        self.collected_results = []
        self.collected_errors = []
        self.critical_error = None
        self.task_finished = False  # Custom flag for MSG_FINISHED

        # --- Submit Task to Executor ---
        # Note: We pass the stop_event and the pre-determined output_dir to the task function
        self.future = self.executor.submit(
            background_synthesis_task,
            handler_instance,
            self.selected_sequences,
            config.default_output_dir,  # Pass the determined output_dir
            self.message_queue,
            self.stop_event,  # Pass the stop event
        )
        # --------------------------------

        # --- Start Modal Timer ---
        # This will call modal() every 0.1 seconds to check progress
        self._timer = context.window_manager.event_timer_add(0.1, window=context.window)
        context.window_manager.modal_handler_add(self)

        self.report(
            {"INFO"},
            f"Starting narration generation ({self.total} strips) using '{self.voice_profile_name}'...",
        )
        return {"RUNNING_MODAL"}  # Important: Operator now runs modally

    def modal(self, context, event):
        # --- Handle Timer Events ---
        if event.type == "TIMER":
            # --- Process messages from the background task ---
            # Drain all available messages from the queue
            while True:
                try:
                    message = self.message_queue.get_nowait()
                    msg_type = message.get("type")
                    msg_data = message.get("data")

                    if msg_type == MSG_PROGRESS:
                        # Update local view (could be used by a panel if exposed)
                        # For now, just process the data
                        # self.progress = msg_data["progress"] # If you add a progress prop
                        # self.current_strip = msg_data["current_strip"] # If you add a current_strip prop
                        # print(f"Progress Update: {msg_data['progress']}/{self.total} - {msg_data['current_strip']}")
                        pass  # Processing done by reading msg_data directly when needed

                    elif msg_type == MSG_ERROR:
                        # Store error locally for final reporting
                        self.collected_errors.append(
                            msg_data
                        )  # msg_data is the error string

                    elif msg_type == MSG_CRITICAL_ERROR:
                        # Store critical error
                        self.critical_error = msg_data  # msg_data is the error string

                    elif msg_type == MSG_RESULT:
                        # Store result locally for final processing
                        self.collected_results.append(
                            msg_data
                        )  # msg_data is the result dict

                    elif msg_type == MSG_FINISHED:
                        # Mark that the task signalled it's finished
                        self.task_finished = True
                        # Note: Don't break here immediately,
                        # process any remaining messages first
                        # Or handle finished logic after the message loop

                except queue.Empty:
                    # No more messages in the queue right now
                    break  # Exit the message processing loop
            # -----------------------------------------------

            # --- Check if task is done (finished or cancelled) ---
            # The future's done() status reflects if the function returned or raised an exception
            # Using the custom self.task_finished flag (from MSG_FINISHED) is often more reliable
            # for custom completion signals or if the task exits early.
            if self.future.done() or self.task_finished:
                # --- Clean up timer ---
                if hasattr(self, "_timer") and self._timer:
                    context.window_manager.event_timer_remove(self._timer)
                # ---------------------

                # --- Shutdown Executor ---
                # It's good practice to shut down the executor when done.
                # shutdown(wait=False) signals shutdown without blocking the main thread.
                self.executor.shutdown(wait=False)
                # -------------------------

                # --- Gather final data (already collected on self) ---
                results = self.collected_results
                errors = self.collected_errors
                critical_error = self.critical_error
                voice_profile_name = self.voice_profile_name
                # was_user_cancelled = self.stop_event.is_set() # Check if stop event was set
                # However, we set it on ESC, so checking the flag set by MSG_FINISHED or future.done()
                # in conjunction with checking if stop_event was set *before* finishing is more accurate.
                # Let's assume if task_finished or future.done() is true, we process results.
                # Cancellation reporting is handled in the ESC path.
                # ------------------------

                # --- Add sound strips to VSE (must be done on the main thread!) ---
                created_count = 0
                # Re-check for errors when adding strips, just in case
                final_errors = list(errors)  # Start with errors collected from queue
                for result in results:
                    strip_name = result["strip_name"]
                    filepath = result["filepath"]
                    text_strip = result["text_strip"]  # Get the original strip object

                    try:
                        # Add sound strip logic
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
                        logger.error(
                            f"Failed to add sound strip for '{strip_name}': {e}",
                            exc_info=True,
                        )
                        final_errors.append(error_msg)

                # --- Report Final Status ---
                # Check if stop event was set before finishing normally for cancellation report
                # This is a bit nuanced. If the user hits ESC, stop_event is set.
                # The task might finish naturally before checking the event again,
                # or it might check and exit early (signalling MSG_FINISHED).
                # We reported "Cancelling..." on ESC press.
                # If we get here and stop_event was set, it means cancellation was requested.
                # The task might have finished quickly or exited early.
                # Let's report cancellation if the event was set, otherwise success/errors.
                if self.stop_event.is_set():
                    self.report(
                        {"WARNING"}, "Narration generation was cancelled by user."
                    )
                elif critical_error:
                    self.report(
                        {"ERROR"}, f"Critical error during generation: {critical_error}"
                    )
                elif final_errors:
                    error_summary = "; ".join(final_errors[:3])  # Show first few errors
                    log_path = os.path.join(gettempdir(), "vocal_vse.log")
                    try:
                        with open(log_path, "a") as log_file:
                            for err in final_errors:
                                log_file.write(err + "\n")
                        self.report(
                            {"ERROR"},
                            f"Generation completed with errors ({len(final_errors)}). See log: {log_path}. First few: {error_summary}",
                        )
                    except Exception as log_write_error:
                        # Fallback if log writing fails
                        self.report(
                            {"ERROR"},
                            f"Generation completed with errors ({len(final_errors)}). Also failed to write log: {log_write_error}. First few errors: {error_summary}",
                        )

                else:
                    self.report(
                        {"INFO"},
                        f"Generated {created_count} narration(s) using '{voice_profile_name}'",
                    )
                # --------------------------

                return {"FINISHED"}  # Modal operator finished

        # --- Handle User Cancellation (ESC) ---
        elif event.type in {"ESC"}:
            # Signal the background task to stop
            self.stop_event.set()

            # Clean up timer immediately
            if hasattr(self, "_timer") and self._timer:
                context.window_manager.event_timer_remove(self._timer)

            # Immediate feedback to user that cancellation is requested
            self.report({"WARNING"}, "Cancelling narration generation...")
            # Don't return CANCELLED yet.
            # Let the task finish (or acknowledge cancellation via MSG_FINISHED/future.done)
            # in the next TIMER event for proper cleanup and final reporting.
            # Keep the modal handler active until then.
            return {
                "RUNNING_MODAL"
            }  # Keep modal running to process final messages/finish
        # ------------------------------------

        # Continue running modally, waiting for TIMER or ESC
        return {"PASS_THROUGH"}  # Let other events pass through

    # Optional: execute method if called without invoke (e.g., from script)
    def execute(self, context):
        # Fallback or direct execution - might block if not handled carefully
        # It's better to force use of invoke for UI interaction
        self.report(
            {"ERROR"}, "Please use the UI panel or search menu to invoke this operator."
        )
        return {"CANCELLED"}
