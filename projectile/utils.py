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
import gpu
from gpu_extras.batch import batch_for_shader
import mathutils
import math

from . import ui


def toggle_trajectory_drawing():
    if bpy.context.scene.projectile_settings.draw_trajectories in {'all', 'selected'}:
        ui.PHYSICS_OT_projectle_draw.add_handler()
    else:
        ui.PHYSICS_OT_projectle_draw.remove_handler()

# Handler to run when UI property changes are made
def ui_prop_change_handler(*args):
    if bpy.context.scene.projectile_settings.draw_trajectories:
        draw_trajectory()

        # Tag View 3D to redraw if it is open
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

    # For each emitter, set settings dirty
    for ob in bpy.context.view_layer.objects:
        if ob.projectile_props.is_emitter:
            ob.projectile_props.is_dirty = True

    # run operator for each projectile object
    # active = bpy.context.view_layer.objects.active

    # for object in bpy.context.view_layer.objects:
    #     if object.projectile_props.is_emitter:
    #         bpy.context.view_layer.objects.active = object
    #         if bpy.context.scene.projectile_settings.auto_update:
    #             bpy.ops.rigidbody.projectile_execute()

    # bpy.context.view_layer.objects.active = active

# Unlink an object from each collection it is in
def unlink_object_from_all_collections(ob):
    name = ob.name

    for collection in bpy.data.collections:
        if name in collection.objects:
            collection.objects.unlink(ob)

def empty_collection(collection):
    for ob in collection.objects:
        bpy.data.objects.remove(ob, do_unlink=True)

def get_projectile_collection():
    if 'projectile_collection' not in bpy.context.scene.projectile_settings \
        or bpy.context.scene.projectile_settings['projectile_collection'] is None:

        projectile_collection = bpy.data.collections.new("Projectile Instances")
        bpy.context.scene.collection.children.link(projectile_collection)

        bpy.context.scene.projectile_settings['projectile_collection'] = projectile_collection

    return bpy.context.scene.projectile_settings['projectile_collection']

# Returns distance between two points in space
def distance_between_points(origin, destination):
    return math.sqrt(math.pow(destination.x - origin.x, 2) + math.pow(destination.y - origin.y, 2) + math.pow(destination.z - origin.z, 2))

# Raycast from origin to destination (Defaults to (nearly) infinite distance)
def raycast(context, origin, destination, distance=1.70141e+38):
    direction = (destination - origin).normalized()
    depsgraph = context.view_layer.depsgraph

    cast = context.scene.ray_cast(depsgraph, origin, direction, distance=distance)
    return cast

# Kinematic Equation to find displacement over time
# Used for drawing expected line
def kinematic_displacement(initial, velocity, time):
    frame_rate = bpy.context.scene.render.fps

    if not bpy.context.scene.use_gravity:
        gravity = mathutils.Vector((0.0, 0.0, 0.0))
    else:
        gravity = bpy.context.scene.gravity


    dt = (time * 1.0) / frame_rate
    ds = mathutils.Vector((0.0, 0.0, 0.0))

    ds.x = initial.x + (velocity.x * dt) + (0.5 * gravity.x * math.pow(dt, 2))
    ds.y = initial.y + (velocity.y * dt) + (0.5 * gravity.y * math.pow(dt, 2))
    ds.z = initial.z + (velocity.z * dt) + (0.5 * gravity.z * math.pow(dt, 2))

    return ds

# Kinematic Equation to set angular velocity
def kinematic_rotation(initial, angular_velocity, time):
    frame_rate = bpy.context.scene.render.fps

    dt = (time * 1.0) / frame_rate
    dr = mathutils.Vector((0.0, 0.0, 0.0))

    dr.x = initial.x + (angular_velocity.x * dt)
    dr.y = initial.y + (angular_velocity.y * dt)
    dr.z = initial.z + (angular_velocity.z * dt)

    return dr

# Convert spherical to cartesian coordinates
def spherical_to_cartesian(radius, incline, azimuth):
    v = mathutils.Vector((0.0, 0.0, 0.0))

    v.x = radius * math.sin(incline) * math.cos(azimuth)
    v.y = radius * math.sin(incline) * math.sin(azimuth)
    v.z = radius * math.cos(incline)

    return v

# Convert cartesian to spherical coordinates
def cartesian_to_spherical(v):
    radius = math.sqrt(pow(v.x, 2) + pow(v.y, 2) + pow(v.z, 2))

    incline = 0
    if radius != 0:
        incline = math.acos(v.z / radius)

    azimuth = 0
    if v.x != 0:
        azimuth = math.atan(v.y / v.x)

    return radius, incline, azimuth

# Custom getattr for using with Blender dict attributes
def get_attr(ob, name, default):
    if name in ob:
        return ob[name]
    return default

# Check if an object is emitted from a given emitter
def is_emitter_instance(emitter, ob):
    emitter_prop = get_attr(ob.projectile_props, "emitter", False)
    if emitter_prop:
        return emitter_prop == emitter
    return False

def calculate_trajectory(context, emitter):
    s = emitter.location

    # Generate coordinates
    cast = []
    coordinates = []
    v = kinematic_displacement(s, emitter.projectile_props.v, 0)
    coord = mathutils.Vector((v.x, v.y, v.z))
    coordinates.append(coord)

    for frame in range(1, context.scene.frame_end):
        v = kinematic_displacement(s, emitter.projectile_props.v, frame)
        coord = mathutils.Vector((v.x, v.y, v.z))

        # Get distance between previous and current position
        distance = distance_between_points(coordinates[-1], coord)

        # Check if anything is in the way
        cast = raycast(context, coordinates[-1], coord, distance)

        # If so, set that position as final position
        if cast[0] and not is_emitter_instance(emitter, cast[4]):
            coordinates.append(cast[1])
            break

        coordinates.append(coord)
        coordinates.append(coord)

    if not cast[0]:
        v = kinematic_displacement(s, emitter.projectile_props.v, context.scene.frame_end)
        coord = mathutils.Vector((v.x, v.y, v.z))
        coordinates.append(coord)

    return coordinates

SHADER = 'UNIFORM_COLOR' if bpy.app.version[0] >= 4 else '3D_UNIFORM_COLOR'

# Draws trajectories from all emitters
def draw_trajectory():
    context = bpy.context
    data = bpy.data
    draw_trajectories = context.scene.projectile_settings.draw_trajectories

    if draw_trajectories == 'all':
        emitters = [ob for ob in data.objects if ob.projectile_props.is_emitter]
    else:
        # Only draw selected
        emitters = [ob for ob in context.selected_objects if ob.projectile_props.is_emitter]

    # Generate a list of all coordinates for all trajectories
    coordinates = []
    for emitter in emitters:
        coordinates += calculate_trajectory(context, emitter)

    # Draw all trajectories
    shader = gpu.shader.from_builtin(SHADER)
    batch = batch_for_shader(shader, 'LINES', {"pos": coordinates})

    shader.bind()
    shader.uniform_float("color", (1, 1, 1, 1))

    batch.draw(shader)

# A global to determine if the property is set from the UI to avoid recursion
FROM_UI = True

# Convert cartesian to spherical coordinates for the active object
def velocity_callback(self, context):
    global FROM_UI

    if FROM_UI:
        FROM_UI = False
        return

    ob = context.object

    if ob and ob.projectile_props.is_emitter:
        radius, incline, azimuth = cartesian_to_spherical(ob.projectile_props.v)

        FROM_UI = True
        ob.projectile_props.radius = radius
        FROM_UI = True
        ob.projectile_props.incline = incline
        FROM_UI = True
        ob.projectile_props.azimuth = azimuth

# Convert spherical to cartesian coordinates for the active object
def spherical_callback(self, context):
    global FROM_UI

    if FROM_UI:
        FROM_UI = False
        return

    ob = context.object

    if ob and ob.projectile_props.is_emitter:
        radius = ob.projectile_props.radius
        incline = ob.projectile_props.incline
        azimuth = ob.projectile_props.azimuth

        FROM_UI = True
        ob.projectile_props.v = spherical_to_cartesian(radius, incline, azimuth)

def set_quality(context):
    frame_rate = context.scene.render.fps
    quality = context.scene.projectile_settings.quality

    if quality == 'very_low':
        context.scene.rigidbody_world.substeps_per_frame = frame_rate * 1
    elif quality == 'low':
        context.scene.rigidbody_world.substeps_per_frame = frame_rate * 4
    elif quality == 'medium':
        context.scene.rigidbody_world.substeps_per_frame = frame_rate * 10
    elif quality == 'high':
        context.scene.rigidbody_world.substeps_per_frame = frame_rate * 20

    context.scene.rigidbody_world.solver_iterations = 20
