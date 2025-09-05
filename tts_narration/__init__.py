"""
Blender VSE Text-to-Speech Narration Add-on
Generates audio from text strips with unique IDs, refresh, and cleanup.
"""

bl_info = {
    "name": "VSE Text-to-Speech Narration",
    "author": "Jet-Logic",
    "version": (0, 1, 0),
    "blender": (3, 0, 0),
    "location": "Sequencer > Add > Text-to-Speech",
    "description": "Generate narration from text strips with ID, refresh, and cleanup",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Sequencer",
}

# Import the main module (same file)
import bpy
import os
import time
import uuid
import platform

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

# Global engine
tts_engine = None


def get_tts_engine():
    global tts_engine
    if tts_engine is None and pyttsx3:
        try:
            tts_engine = pyttsx3.init()
        except Exception as e:
            print(f"TTS Engine init failed: {e}")
    return tts_engine


def get_default_output_dir():
    home = os.path.expanduser("~")
    if platform.system() == "Windows":
        cache_dir = os.path.join(home, "AppData", "Local", "cache")
    else:
        cache_dir = os.path.join(home, ".cache")
    narrations_dir = os.path.join(cache_dir, "blender_narrations")
    os.makedirs(narrations_dir, exist_ok=True)
    return narrations_dir


def get_or_create_strip_id(strip):
    if "tts_id" not in strip:
        new_id = str(uuid.uuid4()).replace("-", "")[:16]
        strip["tts_id"] = new_id
    return strip["tts_id"]


def generate_audio_filename(output_dir, strip):
    strip_id = get_or_create_strip_id(strip)
    timestamp = int(time.time() % 100000)
    return os.path.join(output_dir, f"narration_{strip_id}_{timestamp}.wav")


def find_existing_audio_for_text(scene, text_strip):
    if "tts_id" not in text_strip:
        return None
    target_id = text_strip["tts_id"]
    for strip in scene.sequence_editor.sequences_all:
        if strip.type == "SOUND" and f"Narr_{target_id}" in strip.name:
            return strip
    return None


def get_all_narration_files(output_dir):
    if not os.path.exists(output_dir):
        return []
    return [
        f
        for f in os.listdir(output_dir)
        if f.startswith("narration_") and f.endswith(".wav")
    ]


# --- OPERATORS ---


class VSE_OT_generate_narration(bpy.types.Operator):
    bl_idname = "sequencer.generate_narration"
    bl_label = "Generate Narration from Text"
    bl_options = {"REGISTER", "UNDO"}

    rate: bpy.props.IntProperty(name="Speech Rate", default=150, min=50, max=300)
    volume: bpy.props.FloatProperty(name="Volume", default=1.0, min=0.0, max=1.0)
    voice_type: bpy.props.EnumProperty(
        name="Voice",
        items=[("MALE", "Male", ""), ("FEMALE", "Female", "")],
        default="MALE",
    )

    def execute(self, context):
        if not pyttsx3:
            self.report({"ERROR"}, "pyttsx3 not installed.")
            return {"CANCELLED"}

        engine = get_tts_engine()
        if not engine:
            return {"CANCELLED"}

        engine.setProperty("rate", self.rate)
        engine.setProperty("volume", self.volume)

        voices = engine.getProperty("voices")
        for v in voices:
            if (self.voice_type == "FEMALE" and "female" in v.name.lower()) or (
                self.voice_type == "MALE" and "male" in v.name.lower()
            ):
                engine.setProperty("voice", v.id)
                break

        prefs = context.preferences.addons[__name__].preferences
        output_dir = prefs.output_directory or get_default_output_dir()
        os.makedirs(output_dir, exist_ok=True)

        created = 0
        for strip in context.selected_sequences:
            if strip.type != "TEXT" or not strip.text.strip():
                continue

            filepath = generate_audio_filename(output_dir, strip)
            try:
                engine.save_to_file(strip.text, filepath)
                engine.runAndWait()

                if os.path.exists(filepath):
                    channel = strip.channel + 1
                    frame_start = strip.frame_final_start
                    sound_name = f"Narr_{strip['tts_id']}"

                    old_strip = find_existing_audio_for_text(context.scene, strip)
                    if old_strip:
                        context.scene.sequence_editor.sequences.remove(old_strip)

                    context.scene.sequence_editor.sequences.new_sound(
                        name=sound_name,
                        filepath=filepath,
                        channel=channel,
                        frame_start=frame_start,
                    )
                    created += 1
                else:
                    self.report({"ERROR"}, f"Failed to create: {filepath}")
            except Exception as e:
                self.report({"ERROR"}, f"Error on '{strip.name}': {str(e)}")

        self.report({"INFO"}, f"Generated {created} narration(s)")
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


class VSE_OT_refresh_narration(bpy.types.Operator):
    bl_idname = "sequencer.refresh_narration"
    bl_label = "Refresh Narration"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        found = 0
        regenerated = 0
        for strip in context.selected_sequences:
            if strip.type != "TEXT" or "tts_id" not in strip:
                continue
            found += 1
            old_audio = find_existing_audio_for_text(context.scene, strip)
            if old_audio:
                bpy.ops.sequencer.generate_narration("INVOKE_DEFAULT")
                regenerated += 1
        self.report({"INFO"}, f"Refreshed {regenerated} of {found} text strips")
        return {"FINISHED"}


class VSE_OT_cleanup_narration_files(bpy.types.Operator):
    bl_idname = "sequencer.cleanup_narration_files"
    bl_label = "Cleanup Unused Narration Files"
    bl_options = {"REGISTER"}

    def execute(self, context):
        prefs = context.preferences.addons[__name__].preferences
        output_dir = prefs.output_directory or get_default_output_dir()

        if not os.path.exists(output_dir):
            self.report({"INFO"}, "Output directory does not exist.")
            return {"CANCELLED"}

        used_ids = set()
        for strip in context.scene.sequence_editor.sequences_all:
            if strip.type == "TEXT" and "tts_id" in strip:
                used_ids.add(strip["tts_id"])

        deleted = 0
        files = get_all_narration_files(output_dir)
        for f in files:
            filepath = os.path.join(output_dir, f)
            if "_" in f:
                file_id = f.split("_")[1]
                if file_id not in used_ids:
                    os.remove(filepath)
                    deleted += 1

        self.report({"INFO"}, f"Deleted {deleted} unused audio files")
        return {"FINISHED"}


class VSE_OT_copy_audio_path(bpy.types.Operator):
    bl_idname = "sequencer.copy_audio_path"
    bl_label = "Copy Audio File Path"

    def execute(self, context):
        for strip in context.selected_sequences:
            if strip.type == "TEXT" and "tts_id" in strip:
                prefs = context.preferences.addons[__name__].preferences
                output_dir = prefs.output_directory or get_default_output_dir()
                files = [
                    f
                    for f in get_all_narration_files(output_dir)
                    if strip["tts_id"] in f
                ]
                if files:
                    latest = sorted(files)[-1]
                    path = os.path.join(output_dir, latest)
                    context.window_manager.clipboard = path
                    self.report({"INFO"}, f"Copied: {path}")
                    return {"FINISHED"}
        self.report({"WARNING"}, "No audio path found")
        return {"CANCELLED"}


# --- PANEL ---


class SEQUENCER_PT_tts_panel(bpy.types.Panel):
    bl_label = "TTS Narration Tools"
    bl_space_type = "SEQUENCE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Tools"

    def draw(self, context):
        layout = self.layout
        selected = context.selected_sequences

        col = layout.column(align=True)
        col.operator("sequencer.generate_narration", icon="RENDER_STILL")

        has_text = any(s.type == "TEXT" and "tts_id" in s for s in selected)
        if has_text:
            col.operator("sequencer.refresh_narration", icon="FILE_REFRESH")
            col.operator("sequencer.copy_audio_path", icon="COPYDOWN")

        layout.operator("sequencer.cleanup_narration_files", icon="TRASH")


# --- PREFERENCES ---


class TTSNarrationPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    output_directory: bpy.props.StringProperty(
        name="Output Directory", subtype="DIR_PATH", default=get_default_output_dir()
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "output_directory")
        layout.label(text=f"Default: {get_default_output_dir()}")


# --- REGISTER ---

classes = (
    VSE_OT_generate_narration,
    VSE_OT_refresh_narration,
    VSE_OT_cleanup_narration_files,
    VSE_OT_copy_audio_path,
    SEQUENCER_PT_tts_panel,
    TTSNarrationPreferences,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.SEQUENCER_MT_add.append(menu_func)


def unregister():
    bpy.types.SEQUENCER_MT_add.remove(menu_func)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


def menu_func(self, context):
    self.layout.operator(VSE_OT_generate_narration.bl_idname)


# Module reload support
if __name__ == "__main__":
    register()
