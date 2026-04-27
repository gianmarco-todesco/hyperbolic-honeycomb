import bpy

UNIT = 60.0


def draw_lines(lines, name="HLines", thickness=0.1, unit_scale=UNIT):
	curve_data = bpy.data.curves.new(name=f"{name}_Source", type="CURVE")
	curve_data.dimensions = "3D"
	curve_data.resolution_u = 12
	curve_data.bevel_depth = thickness
	curve_data.bevel_resolution = 4

	for line in lines:
		if len(line) < 2:
			raise ValueError("each line must contain at least 2 points")

		spline = curve_data.splines.new(type="POLY")
		spline.points.add(len(line) - 1)
		for index, point in enumerate(line):
			spline.points[index].co = (point.x*unit_scale, point.y*unit_scale, point.z*unit_scale, 1.0)

	temp_obj = bpy.data.objects.new(f"{name}_Source", curve_data)
	bpy.context.collection.objects.link(temp_obj)

	depsgraph = bpy.context.evaluated_depsgraph_get()
	evaluated_obj = temp_obj.evaluated_get(depsgraph)
	mesh_data = bpy.data.meshes.new_from_object(evaluated_obj, depsgraph=depsgraph)
	mesh_data.name = name

	mesh_obj = bpy.data.objects.new(name, mesh_data)
	bpy.context.collection.objects.link(mesh_obj)

	bpy.data.objects.remove(temp_obj, do_unlink=True)
	bpy.data.curves.remove(curve_data, do_unlink=True)
	return mesh_obj


def get_or_create_material(name="HMaterial", color=(0.2, 0.6, 1.0, 1.0)):
	mat = bpy.data.materials.get(name)
	if mat is None:
		mat = bpy.data.materials.new(name)
		mat.use_nodes = True
		bsdf = mat.node_tree.nodes.get("Principled BSDF")
		if bsdf is not None:
			bsdf.inputs["Base Color"].default_value = color
	return mat


def make_mesh(mesh_data, name="HMesh", unit_scale=UNIT, material=None):
	vertices, faces = mesh_data
	verts = [(p.x * unit_scale, p.y * unit_scale, p.z * unit_scale) for p in vertices]

	mesh = bpy.data.meshes.new(name)
	mesh.from_pydata(verts, [], faces)
	mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
	mesh.update()

	if material is not None:
		mesh.materials.append(material)

	obj = bpy.data.objects.new(name, mesh)
	bpy.context.collection.objects.link(obj)
	return obj	
