import bpy


def draw_lines(lines, unit_scale, name="HLines", thickness=0.1):
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


def create_texture_atlas(
	name="HTextureAtlas",
	size=1024,
	pillar_color=(0.65, 0.82, 0.78, 1.0),
	cube_color=(0.18, 0.48, 0.90, 1.0),
	line_color=(0.06, 0.06, 0.06, 1.0),
	line_width=0.03,
	pillar_segments=10,
):
	size = max(2, int(size))
	_ = max(1, int(pillar_segments))
	line_px = max(1, int(round(float(line_width) * size)))

	image = bpy.data.images.get(name)
	if image is None:
		image = bpy.data.images.new(name=name, width=size, height=size, alpha=True)
	elif image.size[0] != size or image.size[1] != size:
		image.scale(size, size)

	image.alpha_mode = "STRAIGHT"

	pixels = [0.0] * (size * size * 4)

	def fill_rect(u0, v0, u1, v1, color):
		x0 = max(0, min(size, int(u0 * size)))
		y0 = max(0, min(size, int(v0 * size)))
		x1 = max(x0, min(size, int(u1 * size + 0.999999)))
		y1 = max(y0, min(size, int(v1 * size + 0.999999)))
		for y in range(y0, y1):
			for x in range(x0, x1):
				idx = (y * size + x) * 4
				pixels[idx + 0] = color[0]
				pixels[idx + 1] = color[1]
				pixels[idx + 2] = color[2]
				pixels[idx + 3] = color[3]

	# Background rectangles.
	fill_rect(0.0, 0.0, 0.5, 1.0, pillar_color)
	fill_rect(0.5, 0.0, 1.0, 1.0, cube_color)

	line_u = line_px / size
	line_u2 = line_u * 0.25
	

	# Cube borders on all four sides.
	fill_rect(0.5, 0.0, 0.5 + line_u2, 1.0, line_color)
	#fill_rect(1.0 - line_u, 0.0, 1.0, 1.0, (1.0, 0.06, 0.06, 1.0))
	fill_rect(0.5, 0.0, 1.0, line_u2*2, line_color)
	#fill_rect(0.5, 1.0 - line_u, 1.0, 1.0, (0.06, 0.06, 1.0, 1.0))

	t = 0.66
	fill_rect(0.5+t*0.5, t, 1.0, 1.0, line_color)

	# Pillar quads: highlight only the shared-side edge.
	fill_rect(0.5 - line_u, 0.0, 0.5, 1.0, line_color)

	image.pixels = pixels
	image.update()
	return image


def get_or_create_material(name="HMaterial", base_color=(0.2, 0.6, 1.0, 1.0), image=None):
	mat = bpy.data.materials.get(name)
	if mat is None:
		mat = bpy.data.materials.new(name)

	mat.use_nodes = True
	nodes = mat.node_tree.nodes
	links = mat.node_tree.links

	bsdf = nodes.get("Principled BSDF")
	if bsdf is None:
		bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")

	output = nodes.get("Material Output")
	if output is None:
		output = nodes.new(type="ShaderNodeOutputMaterial")

	has_surface_link = False
	for link in links:
		if link.from_node == bsdf and link.to_node == output and link.to_socket == output.inputs["Surface"]:
			has_surface_link = True
			break
	if not has_surface_link:
		links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

	bsdf.inputs["Base Color"].default_value = base_color

	if image is not None:
		tex = nodes.get("HTexture")
		if tex is None or tex.type != "TEX_IMAGE":
			tex = nodes.new(type="ShaderNodeTexImage")
		tex.name = "HTexture"
		tex.label = "HTexture"
		tex.image = image

		for link in list(links):
			if link.to_node == bsdf and link.to_socket == bsdf.inputs["Base Color"]:
				links.remove(link)

		links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])

	return mat


def assign_uvs_by_face_types(mesh, face_types=None):
	if face_types is None:
		face_types = ["cube"] * len(mesh.polygons)

	uv_layer = mesh.uv_layers.active
	if uv_layer is None:
		uv_layer = mesh.uv_layers.new(name="UVMap")

	for poly_index, poly in enumerate(mesh.polygons):
		face_type = face_types[poly_index] if poly_index < len(face_types) else "cube"

		if face_type == "cube":
			u0, u1 = 0.5, 1.0
			quad_uvs = ((u0, 0.0), (u1, 0.0), (u1, 1.0), (u0, 1.0))
		elif face_type == "pillar_b":
			u0, u1 = 0.0, 0.5
			quad_uvs = ((u1, 0.0), (u0, 0.0), (u0, 1.0), (u1, 1.0))
		else:
			u0, u1 = 0.0, 0.5
			quad_uvs = ((u0, 0.0), (u1, 0.0), (u1, 1.0), (u0, 1.0))
		for corner_index, loop_index in enumerate(poly.loop_indices):
			uv_layer.data[loop_index].uv = quad_uvs[corner_index % 4]


def make_mesh(mesh_data, unit_scale, name="HMesh", material=None):
	if len(mesh_data) == 2:
		vertices, faces = mesh_data
		face_types = ["cube"] * len(faces)
	elif len(mesh_data) == 3:
		vertices, faces, face_types = mesh_data
	else:
		raise ValueError("mesh_data must be (vertices, faces) or (vertices, faces, face_types)")

	verts = [(p.x * unit_scale, p.y * unit_scale, p.z * unit_scale) for p in vertices]

	mesh = bpy.data.meshes.new(name)
	mesh.from_pydata(verts, [], faces)
	mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
	mesh.update()

	assign_uvs_by_face_types(mesh, face_types)

	if material is not None:
		mesh.materials.append(material)

	obj = bpy.data.objects.new(name, mesh)
	bpy.context.collection.objects.link(obj)
	return obj	
