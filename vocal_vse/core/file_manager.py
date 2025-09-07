import os
import time
import uuid


# Move file-related functions here
def get_or_create_strip_id(strip):
    if "tts_id" not in strip:
        new_id = str(uuid.uuid4()).replace("-", "")[:16]
        strip["tts_id"] = new_id
    return strip["tts_id"]


def generate_audio_filename(output_dir, strip):
    strip_id = get_or_create_strip_id(strip)
    timestamp = int(time.time() % 100000)
    return os.path.join(output_dir, f"voc_{strip_id}_{timestamp}.wav")


def find_existing_audio_for_text(scene, text_strip):
    if "tts_id" not in text_strip:
        return None
    target_id = text_strip["tts_id"]
    for strip in scene.sequence_editor.sequences_all:
        if strip.type == "SOUND" and f"Voc_{target_id}" in strip.name:
            return strip
    return None


def get_all_narration_files(output_dir):
    if not os.path.exists(output_dir):
        return []
    return [
        f for f in os.listdir(output_dir) if f.startswith("voc_") and f.endswith(".wav")
    ]
