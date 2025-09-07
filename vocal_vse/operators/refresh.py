import bpy


class VSE_OT_refresh_narration(bpy.types.Operator):
    bl_idname = "sequencer.refresh_narration"
    bl_label = "Refresh Narration"
    bl_options = {"REGISTER", "UNDO"}
    bl_description = "Re-generate narration audio for selected text strips using their last used voice profile"

    def execute(self, context):
        bpy.ops.sequencer.generate_narration("INVOKE_DEFAULT")
        return {"FINISHED"}


# Register/Unregister locally if preferred
