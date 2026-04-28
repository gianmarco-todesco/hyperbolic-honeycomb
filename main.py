import importlib
import os
import sys

import bpy

# Blender can run scripts with a different working directory.
# Ensure sibling modules (like h3.py) are importable.
if "__file__" in globals():
	script_dir = os.path.dirname(os.path.abspath(__file__))
else:
	script_dir = bpy.path.abspath("//")

if script_dir and script_dir not in sys.path:
	sys.path.insert(0, script_dir)


def load_local_module(basename):
	module_name = f"{__package__}.{basename}" if __package__ else basename
	if module_name in sys.modules:
		return importlib.reload(sys.modules[module_name])
	return importlib.import_module(module_name)


_h3 = load_local_module("h3")
for name in dir(_h3):
	if not name.startswith("_"):
		globals()[name] = getattr(_h3, name)

_mesh = load_local_module("mesh_generation")
_pcn = load_local_module("point_cloud_nodes")

draw_lines = _mesh.draw_lines
make_mesh = _mesh.make_mesh
create_texture_atlas = _mesh.create_texture_atlas
get_or_create_material = _mesh.get_or_create_material
create_point_cloud_with_hmatrix = _pcn.create_point_cloud_with_hmatrix
build_and_assign_hyperbolic_instances = _pcn.build_and_assign_hyperbolic_instances

UNIT = 60.0
MESH_SUBDIV = 10
POINT_CLOUD_NAME = _pcn.POINT_CLOUD_NAME
HMATRIX_ATTR_NAME = _pcn.HMATRIX_ATTR_NAME
GN_GROUP_NAME = _pcn.GN_GROUP_NAME
GN_MODIFIER_NAME = _pcn.GN_MODIFIER_NAME


# lines_obj = draw_lines(lines, UNIT, name="dod", thickness=0.14)

atlas = create_texture_atlas(pillar_segments=MESH_SUBDIV)
mat = get_or_create_material(image=atlas)

mesh_data = make_mesh_data(m=MESH_SUBDIV)
mesh_obj = make_mesh(mesh_data, UNIT, name="dod_mesh", material=mat)

#small_mesh_data = make_mesh_data(m=2)
#small_mesh_obj = make_mesh(small_mesh_data, UNIT, name="small_dod_mesh", material=mat)

#matrices = [matrix for matrix in base_matrices]
# matrices = [HMatrix()]

# matrices = [HMatrix()] + [HReflection(dod.centers[0].toH())] #  base_matrices 
# matrices = [HMatrix()] + base_matrices 
# matrices = generate_matrices(n=12, maxDist=0.999) 
matrices = generate_matrices(10,0.8) # 0.9985)

#def get_dist(matrix):
#	return (matrix*HPoint(0,0,0,1)).toP().length()
#	
#threshold = 0.9
#matrices1 = []
#matrices2 = []
#for mat in matrices:
#	if get_dist(mat) < threshold:
#		matrices1.append(mat)
#	else:        
#  	    matrices2.append(mat)


points1_obj = create_point_cloud_with_hmatrix(matrices, name="HyperbolicPoints_1")
build_and_assign_hyperbolic_instances(
    mesh_obj, points1_obj, UNIT,
    group_name=GN_GROUP_NAME + "_1",
    modifier_name=GN_MODIFIER_NAME + "_1",
)


#points2_obj = create_point_cloud_with_hmatrix(matrices2, name="HyperbolicPoints_2")
#build_and_assign_hyperbolic_instances(
#    small_mesh_obj, points2_obj, UNIT,
#    group_name=GN_GROUP_NAME + "_2",
#    modifier_name=GN_MODIFIER_NAME + "_2",
#)
