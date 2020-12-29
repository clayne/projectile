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


def enum_prop_to_py(enum_prop):
    items = []
    for item in enum_prop:
        items.append((
            item.identifier,
            item.name,
            item.description,
            item.icon,
            item.value
        ))
    return items


def subscribe_to_rna_props():
    bpy.types.Scene.props_msgbus_handler = object()

    # Subscribe to scene gravity changes
    subscribe_to = bpy.types.Scene, "gravity"
    bpy.msgbus.subscribe_rna(
        key=subscribe_to,
        owner=bpy.types.Scene.props_msgbus_handler,
        args=(),
        notify=utils.ui_prop_change_handler,
    )

    # Subscribe to scene gravity toggle
    subscribe_to = bpy.types.Scene, "use_gravity"
    bpy.msgbus.subscribe_rna(
        key=subscribe_to,
        owner=bpy.types.Scene.props_msgbus_handler,
        args=(),
        notify=utils.ui_prop_change_handler,
    )

    # Subscribe to scene frame rate changes
    subscribe_to = bpy.types.RenderSettings, "fps"
    bpy.msgbus.subscribe_rna(
        key=subscribe_to,
        owner=bpy.types.Scene.props_msgbus_handler,
        args=(),
        notify=utils.ui_prop_change_handler,
    )

def unsubscribe_to_rna_props():
    # Unsubscribe from all RNA msgbus props
    bpy.msgbus.clear_by_owner(bpy.types.Scene.props_msgbus_handler)

# Called when a property is changed
def props_dirty(self, context):
    ob = context.object
    if ob:
        ob.projectile_props.is_dirty = True

def call_multiple_functions(funcs, self, context):
    for f in funcs:
        f(self, context)

class ProjectileObject(bpy.types.PropertyGroup):
    is_emitter: bpy.props.BoolProperty(
        name="Is Projectile",
        description="Is this object a projectile (for internal use)",
        default=False
    )

    is_dirty: bpy.props.BoolProperty(
        name="Is Dirty",
        description="Are emitter props dirty (for internal use)",
        default=False
    )

    start_frame: bpy.props.IntProperty(
        name="Start Frame",
        description="Frame to start velocity initialization on",
        default=1,
        min=1,
        options={'HIDDEN'},
        update=props_dirty
    )

    end_frame: bpy.props.IntProperty(
        name="End Frame",
        description="Frame to end projectile instancing",
        default=50,
        min=1,
        options={'HIDDEN'},
        update=props_dirty
    )

    instance_count: bpy.props.IntProperty(
        name="Number",
        description="Instances of the projectile",
        default=1,
        options={'HIDDEN'},
        update=props_dirty
    )

    v: bpy.props.FloatVectorProperty(
        name="Velocity",
        description="Velocity for the object",
        subtype='VELOCITY',
        precision=4,
        options={'HIDDEN'},
        update = lambda self, context : call_multiple_functions([utils.velocity_callback, props_dirty], self, context)
    )

    w: bpy.props.FloatVectorProperty(
        name="Angular Velocity",
        description="Angular velocity for the object",
        subtype='EULER',
        precision=4,
        options={'HIDDEN'},
        update=props_dirty
    )

    start_hidden: bpy.props.BoolProperty(
        name="Start Hidden",
        description="Hide the object before the start frame",
        default=False,
        options={'HIDDEN'},
        update=props_dirty
    )

    lifetime: bpy.props.IntProperty(
        name="Lifetime",
        description="Lifetime of the rigidbody (lifetime of 0 to disable)",
        default=0,
        min=0,
        options={'HIDDEN'},
        update=props_dirty
    )

    radius: bpy.props.FloatProperty(
        name="Radius",
        description="Radius (magnitude) of velocity",
        default=0.0,
        unit='VELOCITY',
        options={'HIDDEN'},
        update=lambda self, context : call_multiple_functions([utils.spherical_callback, props_dirty], self, context)
    )

    incline: bpy.props.FloatProperty(
        name="Incline",
        description="Incline (theta) for velocity",
        default=0.0,
        unit='ROTATION',
        options={'HIDDEN'},
        update=lambda self, context : call_multiple_functions([utils.spherical_callback, props_dirty], self, context)
    )

    azimuth: bpy.props.FloatProperty(
        name="Azimuth",
        description="Azimuth (phi) for velocity",
        default=0.0,
        unit='ROTATION',
        options={'HIDDEN'},
        update=lambda self, context : call_multiple_functions([utils.spherical_callback, props_dirty], self, context)
    )

    # Instance Physics Settings
    friction: bpy.props.FloatProperty(
        name="Friction",
        description="Resistance of object to movement",
        default=0.5,
        soft_min=0.0,
        soft_max=1.0,
        step=1,
        precision=3,
        subtype='FACTOR',
        update=props_dirty,
    )

    bounciness: bpy.props.FloatProperty(
        name="Bounciness",
        description="Tendency of object to bounce after colliding with another",
        default=0.0,
        soft_min=0.0,
        soft_max=1.0,
        step=1,
        precision=3,
        subtype='FACTOR',
        update=props_dirty,
    )

    collision_shape: bpy.props.EnumProperty(
        name="Collision Shape",
        description="Collision Shape of object in Rigid Body Simulations",
        items=enum_prop_to_py(bpy.types.RigidBodyObject.bl_rna.properties['collision_shape'].enum_items),
        default='CONVEX_HULL',
        update=props_dirty,
    )


# Removes draw handler when draw trajectories is disabled
def draw_trajectories_callback(self, context):
    utils.toggle_trajectory_drawing()

def set_quality_callback(self, context):
    utils.set_quality(context)

class ProjectileSettings(bpy.types.PropertyGroup):
    draw_trajectories: bpy.props.EnumProperty(
        name="Draw Trajectories",
        items=[("all", "All", "Draw trajectories for all emitters"),
                ("selected", "Selected", "Draw trajectories for selected emitters"),
                ("none", "None", "Do not draw trajectories")],
        default='selected',
        options={'HIDDEN'},
        update=draw_trajectories_callback
    )

    quality: bpy.props.EnumProperty(
        name="Quality",
        items=[("very_low", "Particle", "Very low quality can help with instancing that behaves like particles"),
               ("low", "Low", "Use low quality solver settings"),
               ("medium", "Medium", "Use medium quality solver settings"),
               ("high", "High", "Use high quality solver settings")],
        default='very_low',
        options={'HIDDEN'},
        update=set_quality_callback)

    spherical: bpy.props.BoolProperty(
        name="Spherical Coordinates",
        description="Set velocity with spherical coordinates",
        options={'HIDDEN'},
        default=True
    )


classes = (
    ProjectileObject,
    ProjectileSettings,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Object.projectile_props = bpy.props.PointerProperty(type=ProjectileObject)
    bpy.types.Scene.projectile_settings = bpy.props.PointerProperty(type=ProjectileSettings)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    del bpy.types.Object.projectile_props
    del bpy.types.Scene.projectile_settings
