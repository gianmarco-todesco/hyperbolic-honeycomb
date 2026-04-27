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
get_or_create_material = _mesh.get_or_create_material
create_point_cloud_with_hmatrix = _pcn.create_point_cloud_with_hmatrix
build_and_assign_hyperbolic_instances = _pcn.build_and_assign_hyperbolic_instances

UNIT = _mesh.UNIT
POINT_CLOUD_NAME = _pcn.POINT_CLOUD_NAME
HMATRIX_ATTR_NAME = _pcn.HMATRIX_ATTR_NAME
GN_GROUP_NAME = _pcn.GN_GROUP_NAME
GN_MODIFIER_NAME = _pcn.GN_MODIFIER_NAME
POINCARE_INPUT_SCALE = _pcn.POINCARE_INPUT_SCALE


# lines_obj = draw_lines(lines, name="dod", thickness=0.14, unit_scale=UNIT)

mat = get_or_create_material()

mesh_data = make_mesh_data(m=10)
mesh_obj = make_mesh(mesh_data, name="dod_mesh", material=mat)

#matrices = [matrix for matrix in base_matrices]
# matrices = [HMatrix()]

# matrices = [HMatrix()] + [HReflection(dod.centers[0].toH())] #  base_matrices 
# matrices = [HMatrix()] + base_matrices 
matrices = generate_matrices(n=8)

points_obj = create_point_cloud_with_hmatrix(matrices)
build_and_assign_hyperbolic_instances(mesh_obj, points_obj)

