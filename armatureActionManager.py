bl_info = {
    "name": "Armature Action Manager",
    "author": "254599003117715457 (Discord ID)",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "3D Viewport > Sidebar > AAM",
    "description": "Manage and export armature actions to FBX",
    "warning": "",
    "wiki_url": "",
    "category": "Animation"
}


import bpy
import os

# View what actions are usable by selected Armature.
def get_usable_actions(armature):
    usable = []
    if not armature or armature.type != 'ARMATURE':
        return usable
    for action in bpy.data.actions:
        for fcurve in action.fcurves:
            if fcurve.data_path.startswith("pose.bones"):
                bone_name = fcurve.data_path.split('"')[1]
                if bone_name in armature.pose.bones:
                    usable.append(action)
                    break
    return usable
# Fields that show up in the panel UI.
class MyAddonProperties(bpy.types.PropertyGroup):
    armature: bpy.props.PointerProperty(
        name="Armature",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'ARMATURE'
    )
    action: bpy.props.PointerProperty(name="Action", type=bpy.types.Action)
    use_base_action: bpy.props.BoolProperty(name="Set base before exporting?")
    base_action: bpy.props.PointerProperty(name="Base", type=bpy.types.Action) 
    fbx_global_scale: bpy.props.FloatProperty(
        name="FBX Scale",
        description="Scale factor for FBX export (NOTE: Does not scale the actual mesh it self, this value should match scale value that the mesh was exported in)",
        default=1.0,
        min=0.01,
        max=100.0,
        precision=2
    )
# Export all operator button
class MYADDON_OT_ExportAllActions(bpy.types.Operator):
    bl_idname = "myaddon.export_all_actions"
    bl_label = "Export All Actions"
    bl_description = "Export all actions as FBX file to a specific "
    bl_options = {'REGISTER', 'UNDO'}

    directory: bpy.props.StringProperty(
        name="Export Folder",
        description="Choose folder for FBX exports",
        default="//",
        subtype='DIR_PATH'
    )

    def execute(self, context):
        props = context.scene.armature_props
        armature = props.armature
        use_base = props.use_base_action
        base_action = props.base_action
        scale = props.fbx_global_scale

        if not armature or armature.type != 'ARMATURE':
            self.report({'WARNING'}, "No valid armature selected")
            return {'CANCELLED'}

        usable_actions = get_usable_actions(armature)
        if not usable_actions:
            self.report({'INFO'}, "No usable actions to export")
            return {'CANCELLED'}

        export_dir = bpy.path.abspath(self.directory)
        os.makedirs(export_dir, exist_ok=True)


        bpy.ops.object.select_all(action='DESELECT')
        armature.select_set(True)
        for obj in armature.children:
            obj.select_set(True)
        context.view_layer.objects.active = armature

        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'SOLID'

        for action in usable_actions:
            if use_base and base_action:
                armature.animation_data.action = base_action
                bpy.context.view_layer.update()

            armature.animation_data.action = action
            bpy.context.view_layer.update()
            # Safe file name measures
            safe_name = action.name.replace(" ", "_")
            export_path = os.path.join(export_dir, f"{armature.name}_{safe_name}.fbx")

            bpy.ops.export_scene.fbx(
                filepath=export_path,
                use_selection=True,
                bake_anim=True,
                bake_anim_use_all_actions=False,
                bake_anim_use_nla_strips=False,
                bake_anim_use_all_bones=True,
                bake_anim_force_startend_keying=True,
                bake_anim_step=1.00,
                object_types={'ARMATURE'},
                apply_scale_options='FBX_SCALE_NONE',
                global_scale=scale,
                path_mode="AUTO"
            )

        self.report({'INFO'}, f"Exported {len(usable_actions)} actions to {export_dir}")
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class MYADDON_OT_SetAction(bpy.types.Operator):
    bl_idname = "myaddon.set_action"
    bl_label = "Change Action"
    bl_description = "Assign the selected action to the chosen armature"

    def execute(self, context):
        props = context.scene.armature_props
        armature = props.armature
        action = props.action

        if not armature or armature.type != 'ARMATURE':
            self.report({'WARNING'}, "No valid armature selected")
            return {'CANCELLED'}
        if not action:
            self.report({'WARNING'}, "No action selected")
            return {'CANCELLED'}

        if not armature.animation_data:
            armature.animation_data_create()

        armature.animation_data.action = action
        self.report({'INFO'}, f"Assigned action '{action.name}' to {armature.name}")
        return {'FINISHED'}
# Panel UI visibility and presentation to user.
class MYADDON_PT_Panel(bpy.types.Panel):
    bl_label = "Armature Action Manager"
    bl_idname = "MYADDON_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'AAM'

    def draw(self, context):
        layout = self.layout
        props = context.scene.armature_props
        armature = props.armature
        layout.prop(props, "armature")
        layout.prop(props, "fbx_global_scale")

        # When an armature gets selected, display others
        if armature:
            usable = get_usable_actions(armature)
            if usable:
                layout.label(text="Usable Actions:")
                layout.prop_search(props, "action", bpy.data, "actions")
                if props.action and props.action not in usable:
                    layout.label(text="⚠ Selected action does not match this armature!", icon='ERROR')

                layout.operator("myaddon.set_action", icon='PLAY')
                layout.prop(props, "use_base_action")
                
                row2 = layout.row()
                row2.enabled = props.use_base_action
                row2.prop_search(props, "base_action", bpy.data, "actions")

                layout.operator("myaddon.export_all_actions", icon='EXPORT')
            else:
                layout.label(text="No usable actions found", icon='INFO')

classes = [MyAddonProperties, MYADDON_OT_ExportAllActions, MYADDON_OT_SetAction, MYADDON_PT_Panel]


# Blender add-on visibility.
def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.armature_props = bpy.props.PointerProperty(type=MyAddonProperties)

def unregister():
    del bpy.types.Scene.armature_props
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()

