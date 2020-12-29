# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import bpy

from . import utils


# This class holds the handler for drawing trajectories in the 3D view.
# It is wrapped in an operator (singleton) to make it easier to create
# and destroy the handler.
class PHYSICS_OT_projectle_draw(bpy.types.Operator):
    bl_idname = "rigidbody.projectile_draw"
    bl_label = "Draw"
    bl_description = "Trajectory draw handler"

    _handle = None

    @staticmethod
    def add_handler():
        if PHYSICS_OT_projectle_draw._handle is None:
            PHYSICS_OT_projectle_draw._handle = bpy.types.SpaceView3D.draw_handler_add(
                utils.draw_trajectory,
                (),
                'WINDOW',
                'POST_VIEW')

    @staticmethod
    def remove_handler():
        if PHYSICS_OT_projectle_draw._handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(PHYSICS_OT_projectle_draw._handle, 'WINDOW')

        PHYSICS_OT_projectle_draw._handle = None

    def execute(self, context):
        return {'FINISHED'}


def execute_all_poll(context):
    objects = context.scene.objects
    for ob in objects:
        if ob.projectile_props.is_emitter and ob.projectile_props.is_dirty:
            return True
    return False


class PHYSICS_PT_projectile(bpy.types.Panel):
    bl_label = "Projectile"
    bl_category = "Physics"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        settings = context.scene.projectile_settings

        ob = context.object
        if ob and ob.projectile_props.is_emitter:
            row = layout.row()
            row.operator('rigidbody.projectile_remove_emitter', icon='REMOVE')
        elif ob and ob.type in {'MESH'}:
            row = layout.row()
            row.operator('rigidbody.projectile_add_emitter', icon='ADD')
        else:
            row = layout.row()
            row.label(text="Select a mesh to create an emitter", icon="QUESTION")

        if ob and ob.projectile_props.is_emitter:
            col = layout.column(align=True)
            col.prop(ob.projectile_props, 'start_frame')
            col.prop(ob.projectile_props, 'end_frame')

            row = layout.row()
            row.prop(ob.projectile_props, 'instance_count')

            row = layout.row()
            row.prop(ob.projectile_props, 'start_hidden')

            row = layout.row()
            row.prop(ob.projectile_props, 'lifetime')

            if settings.spherical:
                col = layout.column(align=True)
                col.prop(ob.projectile_props, 'radius', text="Velocity Radius")
                col.prop(ob.projectile_props, 'incline')
                col.prop(ob.projectile_props, 'azimuth')
            else:
                row = layout.row()
                row.prop(ob.projectile_props, 'v')

            row = layout.row()
            row.prop(ob.projectile_props, 'w')

            row = layout.row()
            row.operator('rigidbody.projectile_execute')

            if execute_all_poll(context):
                row = layout.row()
                row.operator('rigidbody.projectile_execute_all')

            if ob.projectile_props.is_dirty:
                box = layout.box()
                box.label(text="Settings have changed", icon='ERROR')

        elif execute_all_poll(context):
            row = layout.row()
            row.operator('rigidbody.projectile_execute_all')


class PHYSICS_PT_projectile_rb_settings(bpy.types.Panel):
    bl_label = "Rigid Body Settings"
    bl_parent_id = "PHYSICS_PT_projectile"
    bl_category = "Physics"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        ob = context.object
        if ob and ob.projectile_props.is_emitter:
            row = layout.row()
            row.prop(ob.projectile_props, 'friction')

            row = layout.row()
            row.prop(ob.projectile_props, 'bounciness')

            row = layout.row()
            row.prop(ob.projectile_props, 'collision_shape')

class PHYSICS_PT_projectile_settings(bpy.types.Panel):
    bl_label = "Projectile Settings"
    bl_parent_id = "PHYSICS_PT_projectile"
    bl_category = "Physics"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        settings = context.scene.projectile_settings

        row = layout.row()
        row.prop(settings, 'spherical')

        row = layout.row()
        row.prop(settings, "quality", expand=True)

        row = layout.row()
        row.prop(settings, 'draw_trajectories', expand=True)


classes = (
    PHYSICS_PT_projectile,
    PHYSICS_PT_projectile_rb_settings,
    PHYSICS_PT_projectile_settings,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
