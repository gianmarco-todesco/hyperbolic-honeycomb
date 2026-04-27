import bpy
from mathutils import Matrix

POINT_CLOUD_NAME = "HyperbolicPoints"
HMATRIX_ATTR_NAME = "hmatrix"
GN_GROUP_NAME = "HyperbolicInstances_GN"
GN_MODIFIER_NAME = "HyperbolicInstances"


def _to_float4x4_matrix(value):
	"""Convert supported inputs to a mathutils.Matrix(4x4)."""
	if isinstance(value, Matrix):
		if len(value.row) != 4 or any(len(row) != 4 for row in value.row):
			raise ValueError("matrix must be 4x4")
		return value

	if hasattr(value, "mat"):
		try:
			value = value.mat.tolist()
		except Exception as exc:
			raise ValueError("matrix element with .mat is not convertible to a 4x4 list") from exc

	try:
		matrix = Matrix(value)
	except Exception as exc:
		raise ValueError("matrix element is not convertible to Matrix") from exc

	if len(matrix.row) != 4 or any(len(row) != 4 for row in matrix.row):
		raise ValueError("matrix must be 4x4")
	return matrix


def ensure_geometry_io(node_group):
	if hasattr(node_group, "interface"):
		input_names = [
			item.name for item in node_group.interface.items_tree
			if hasattr(item, "in_out") and item.in_out == 'INPUT'
		]
		output_names = [
			item.name for item in node_group.interface.items_tree
			if hasattr(item, "in_out") and item.in_out == 'OUTPUT'
		]
		if "Geometry" not in input_names:
			node_group.interface.new_socket(
				name="Geometry",
				in_out='INPUT',
				socket_type='NodeSocketGeometry',
			)
		if "Geometry" not in output_names:
			node_group.interface.new_socket(
				name="Geometry",
				in_out='OUTPUT',
				socket_type='NodeSocketGeometry',
			)
	else:
		if "Geometry" not in node_group.inputs:
			node_group.inputs.new("NodeSocketGeometry", "Geometry")
		if "Geometry" not in node_group.outputs:
			node_group.outputs.new("NodeSocketGeometry", "Geometry")


def find_socket(sockets, names):
	for name in names:
		socket = sockets.get(name)
		if socket is not None:
			return socket
	for socket in sockets:
		if socket.name in names:
			return socket
	return None


def require_socket(node, io_kind, names):
	sockets = node.inputs if io_kind == "in" else node.outputs
	socket = find_socket(sockets, names)
	if socket is None:
		raise RuntimeError(f"Socket not found on {node.bl_idname}: one of {names}")
	return socket


def require_socket_index(node, io_kind, index):
	sockets = node.inputs if io_kind == "in" else node.outputs
	if index < 0 or index >= len(sockets):
		raise RuntimeError(f"Socket index {index} not found on {node.bl_idname}")
	return sockets[index]


def link_by_name(links, from_node, from_names, to_node, to_names):
	from_socket = require_socket(from_node, "out", from_names)
	to_socket = require_socket(to_node, "in", to_names)
	links.new(from_socket, to_socket)


def create_point_cloud_with_hmatrix(
	matrices,
	name=POINT_CLOUD_NAME,
	attr_name=HMATRIX_ATTR_NAME,
	point_position=(0.0, 0.0, 0.0),
):
	"""Create one point per matrix and assign a per-point FLOAT4X4 attribute."""
	if matrices is None or len(matrices) == 0:
		raise ValueError("matrices must contain at least one 4x4 matrix")

	if len(point_position) != 3:
		raise ValueError("point_position must be a 3D tuple/list")

	position = (float(point_position[0]), float(point_position[1]), float(point_position[2]))

	obj = bpy.data.objects.get(name)
	if obj is not None:
		data = obj.data
		bpy.data.objects.remove(obj, do_unlink=True)
		if data is not None and hasattr(data, "users") and data.users == 0:
			bpy.data.meshes.remove(data, do_unlink=True)

	mesh = bpy.data.meshes.get(name)
	if mesh is not None:
		bpy.data.meshes.remove(mesh, do_unlink=True)

	positions = [position] * len(matrices)

	mesh = bpy.data.meshes.new(name)
	mesh.from_pydata(positions, [], [])
	mesh.update()

	obj = bpy.data.objects.new(name, mesh)
	bpy.context.collection.objects.link(obj)

	attr = mesh.attributes.new(name=attr_name, type='FLOAT4X4', domain='POINT')
	for index, matrix_value in enumerate(matrices):
		try:
			attr.data[index].value = _to_float4x4_matrix(matrix_value)
		except Exception as exc:
			raise ValueError(f"invalid matrix at index {index}: {exc}") from exc

	print(f"Point cloud '{name}' created with {len(matrices)} points and '{attr_name}' attribute.")
	return obj


def create_hyperbolic_instances_gn_tree(
	points_obj,
	unit_scale,
	attr_name=HMATRIX_ATTR_NAME,
):
	node_group = bpy.data.node_groups.new(GN_GROUP_NAME, "GeometryNodeTree")
	ensure_geometry_io(node_group)

	nodes = node_group.nodes
	links = node_group.links
	nodes.clear()

	def new_math(operation, location, value0=None, value1=None):
		node = nodes.new("ShaderNodeMath")
		node.operation = operation
		node.location = location
		if value0 is not None:
			node.inputs[0].default_value = value0
		if value1 is not None:
			node.inputs[1].default_value = value1
		return node

	def new_vector_math(operation, location, value0=None, value1=None, scale=None):
		node = nodes.new("ShaderNodeVectorMath")
		node.operation = operation
		node.location = location
		if value0 is not None:
			node.inputs[0].default_value = value0
		if value1 is not None and len(node.inputs) > 1:
			node.inputs[1].default_value = value1
		if scale is not None:
			for socket in node.inputs:
				if socket.name == "Scale":
					socket.default_value = scale
					break
		return node

	group_in = nodes.new("NodeGroupInput")
	group_in.location = (-1800, 160)

	group_out = nodes.new("NodeGroupOutput")
	group_out.location = (1520, 160)

	object_info = nodes.new("GeometryNodeObjectInfo")
	object_info.location = (-1560, 360)
	require_socket(object_info, "in", ["Object"]).default_value = points_obj
	if hasattr(object_info, "as_instance"):
		object_info.as_instance = False

	instance_on_points = nodes.new("GeometryNodeInstanceOnPoints")
	instance_on_points.location = (-1280, 160)

	store_matrix = nodes.new("GeometryNodeStoreNamedAttribute")
	store_matrix.location = (-1020, 160)
	store_matrix.data_type = 'FLOAT4X4'
	if hasattr(store_matrix, "domain"):
		store_matrix.domain = 'INSTANCE'
	require_socket(store_matrix, "in", ["Name"]).default_value = attr_name

	realize_instances = nodes.new("GeometryNodeRealizeInstances")
	realize_instances.location = (-760, 160)

	set_position = nodes.new("GeometryNodeSetPosition")
	set_position.location = (1280, 160)

	source_attr = nodes.new("GeometryNodeInputNamedAttribute")
	source_attr.location = (-1280, -120)
	source_attr.data_type = 'FLOAT4X4'
	require_socket(source_attr, "in", ["Name"]).default_value = attr_name

	stored_attr = nodes.new("GeometryNodeInputNamedAttribute")
	stored_attr.location = (-760, -300)
	stored_attr.data_type = 'FLOAT4X4'
	require_socket(stored_attr, "in", ["Name"]).default_value = attr_name

	position = nodes.new("GeometryNodeInputPosition")
	position.location = (-1560, -420)

	position_scale = new_vector_math("SCALE", (-1320, -420), scale=1.0/unit_scale)
	dot_product = new_vector_math("DOT_PRODUCT", (-1080, -420))
	one_minus_r2 = new_math("SUBTRACT", (-860, -480), 1.0)
	two_over_denominator = new_math("DIVIDE", (-640, -480), 2.0)
	one_plus_r2 = new_math("ADD", (-860, -360), 1.0)
	hyperboloid_w = new_math("DIVIDE", (-640, -360))
	hyperboloid_xyz = new_vector_math("SCALE", (-420, -420))
	separate_xyz = nodes.new("ShaderNodeSeparateXYZ")
	separate_xyz.location = (-200, -420)

	separate_matrix = nodes.new("FunctionNodeSeparateMatrix")
	separate_matrix.location = (-440, -120)

	column_0 = nodes.new("ShaderNodeCombineXYZ")
	column_0.location = (-160, 160)
	column_1 = nodes.new("ShaderNodeCombineXYZ")
	column_1.location = (-160, 0)
	column_2 = nodes.new("ShaderNodeCombineXYZ")
	column_2.location = (-160, -160)
	column_3 = nodes.new("ShaderNodeCombineXYZ")
	column_3.location = (-160, -320)

	vector_mul_x = new_vector_math("SCALE", (120, 160))
	vector_mul_y = new_vector_math("SCALE", (120, 0))
	vector_mul_z = new_vector_math("SCALE", (120, -160))
	vector_mul_w = new_vector_math("SCALE", (120, -320))
	vector_add_0 = new_vector_math("ADD", (380, 80))
	vector_add_1 = new_vector_math("ADD", (600, 20))
	vector_add_2 = new_vector_math("ADD", (820, -40))

	scalar_mul_x = new_math("MULTIPLY", (160, -520))
	scalar_mul_y = new_math("MULTIPLY", (160, -620))
	scalar_mul_z = new_math("MULTIPLY", (160, -720))
	scalar_mul_w = new_math("MULTIPLY", (160, -820))
	scalar_add_0 = new_math("ADD", (400, -560))
	scalar_add_1 = new_math("ADD", (620, -640))
	scalar_add_2 = new_math("ADD", (840, -720))

	one_plus_transformed_w = new_math("ADD", (1040, -720), 1.0)
	poincare_factor = new_math("DIVIDE", (1240, -720), unit_scale)
	final_position = new_vector_math("SCALE", (1040, -80))

	link_by_name(links, object_info, ["Geometry"], instance_on_points, ["Points"])
	link_by_name(links, group_in, ["Geometry"], instance_on_points, ["Instance"])
	link_by_name(links, instance_on_points, ["Instances", "Geometry"], store_matrix, ["Geometry"])
	link_by_name(links, source_attr, ["Attribute", "Matrix"], store_matrix, ["Value"])
	link_by_name(links, store_matrix, ["Geometry"], realize_instances, ["Geometry"])
	link_by_name(links, realize_instances, ["Geometry"], set_position, ["Geometry"])
	link_by_name(links, set_position, ["Geometry"], group_out, ["Geometry"])

	links.new(require_socket(position, "out", ["Position"]), require_socket_index(position_scale, "in", 0))
	links.new(require_socket_index(position_scale, "out", 0), require_socket_index(dot_product, "in", 0))
	links.new(require_socket_index(position_scale, "out", 0), require_socket_index(dot_product, "in", 1))
	links.new(require_socket_index(dot_product, "out", 1), require_socket_index(one_minus_r2, "in", 1))
	links.new(require_socket_index(one_minus_r2, "out", 0), require_socket_index(two_over_denominator, "in", 1))
	links.new(require_socket_index(dot_product, "out", 1), require_socket_index(one_plus_r2, "in", 1))
	links.new(require_socket_index(one_plus_r2, "out", 0), require_socket_index(hyperboloid_w, "in", 0))
	links.new(require_socket_index(one_minus_r2, "out", 0), require_socket_index(hyperboloid_w, "in", 1))
	links.new(require_socket_index(position_scale, "out", 0), require_socket_index(hyperboloid_xyz, "in", 0))
	links.new(require_socket_index(two_over_denominator, "out", 0), require_socket(hyperboloid_xyz, "in", ["Scale"]))
	links.new(require_socket_index(hyperboloid_xyz, "out", 0), require_socket_index(separate_xyz, "in", 0))

	link_by_name(links, stored_attr, ["Attribute", "Matrix"], separate_matrix, ["Matrix"])

	separate_outputs = [require_socket_index(separate_matrix, "out", index) for index in range(16)]
	for combine_node, offset in zip((column_0, column_1, column_2, column_3), (0, 4, 8, 12)):
		links.new(separate_outputs[offset + 0], require_socket_index(combine_node, "in", 0))
		links.new(separate_outputs[offset + 1], require_socket_index(combine_node, "in", 1))
		links.new(separate_outputs[offset + 2], require_socket_index(combine_node, "in", 2))

	for scalar_socket, vector_mul in zip(
		(
			require_socket_index(separate_xyz, "out", 0),
			require_socket_index(separate_xyz, "out", 1),
			require_socket_index(separate_xyz, "out", 2),
			require_socket_index(hyperboloid_w, "out", 0),
		),
		(vector_mul_x, vector_mul_y, vector_mul_z, vector_mul_w),
	):
		links.new(scalar_socket, require_socket(vector_mul, "in", ["Scale"]))

	links.new(require_socket_index(column_0, "out", 0), require_socket_index(vector_mul_x, "in", 0))
	links.new(require_socket_index(column_1, "out", 0), require_socket_index(vector_mul_y, "in", 0))
	links.new(require_socket_index(column_2, "out", 0), require_socket_index(vector_mul_z, "in", 0))
	links.new(require_socket_index(column_3, "out", 0), require_socket_index(vector_mul_w, "in", 0))
	links.new(require_socket_index(vector_mul_x, "out", 0), require_socket_index(vector_add_0, "in", 0))
	links.new(require_socket_index(vector_mul_y, "out", 0), require_socket_index(vector_add_0, "in", 1))
	links.new(require_socket_index(vector_add_0, "out", 0), require_socket_index(vector_add_1, "in", 0))
	links.new(require_socket_index(vector_mul_z, "out", 0), require_socket_index(vector_add_1, "in", 1))
	links.new(require_socket_index(vector_add_1, "out", 0), require_socket_index(vector_add_2, "in", 0))
	links.new(require_socket_index(vector_mul_w, "out", 0), require_socket_index(vector_add_2, "in", 1))

	for scalar_socket, matrix_socket, mul_node in zip(
		(
			require_socket_index(separate_xyz, "out", 0),
			require_socket_index(separate_xyz, "out", 1),
			require_socket_index(separate_xyz, "out", 2),
			require_socket_index(hyperboloid_w, "out", 0),
		),
		(
			separate_outputs[3],
			separate_outputs[7],
			separate_outputs[11],
			separate_outputs[15],
		),
		(scalar_mul_x, scalar_mul_y, scalar_mul_z, scalar_mul_w),
	):
		links.new(scalar_socket, require_socket_index(mul_node, "in", 0))
		links.new(matrix_socket, require_socket_index(mul_node, "in", 1))

	links.new(require_socket_index(scalar_mul_x, "out", 0), require_socket_index(scalar_add_0, "in", 0))
	links.new(require_socket_index(scalar_mul_y, "out", 0), require_socket_index(scalar_add_0, "in", 1))
	links.new(require_socket_index(scalar_add_0, "out", 0), require_socket_index(scalar_add_1, "in", 0))
	links.new(require_socket_index(scalar_mul_z, "out", 0), require_socket_index(scalar_add_1, "in", 1))
	links.new(require_socket_index(scalar_add_1, "out", 0), require_socket_index(scalar_add_2, "in", 0))
	links.new(require_socket_index(scalar_mul_w, "out", 0), require_socket_index(scalar_add_2, "in", 1))

	links.new(require_socket_index(scalar_add_2, "out", 0), require_socket_index(one_plus_transformed_w, "in", 1))
	links.new(require_socket_index(one_plus_transformed_w, "out", 0), require_socket_index(poincare_factor, "in", 1))
	links.new(require_socket_index(vector_add_2, "out", 0), require_socket_index(final_position, "in", 0))
	links.new(require_socket_index(poincare_factor, "out", 0), require_socket(final_position, "in", ["Scale"]))
	links.new(require_socket_index(final_position, "out", 0), require_socket(set_position, "in", ["Position"]))

	return node_group


def assign_gn_modifier(obj, node_group, modifier_name=GN_MODIFIER_NAME):
	if obj is None:
		raise ValueError("obj must exist")

	for modifier in list(obj.modifiers):
		if modifier.type != 'NODES':
			continue
		group = getattr(modifier, "node_group", None)
		if modifier.name == modifier_name or (group is not None and group.name == GN_GROUP_NAME):
			obj.modifiers.remove(modifier)

	modifier = obj.modifiers.new(name=modifier_name, type='NODES')
	modifier.node_group = node_group
	return modifier


def build_and_assign_hyperbolic_instances(
	lines_obj,
	points_obj,
	unit_scale,
	attr_name=HMATRIX_ATTR_NAME,
	group_name=GN_GROUP_NAME,
	modifier_name=GN_MODIFIER_NAME,
):
	if lines_obj is None:
		raise ValueError("lines_obj must exist")
	if points_obj is None:
		raise ValueError("points_obj must exist")

	mesh = getattr(points_obj, "data", None)
	attributes = getattr(mesh, "attributes", None)
	if attributes is None or attributes.get(attr_name) is None:
		raise ValueError(f"point cloud must contain attribute '{attr_name}'")

	existing_group = bpy.data.node_groups.get(group_name)
	if existing_group is not None:
		bpy.data.node_groups.remove(existing_group, do_unlink=True)

	node_group = create_hyperbolic_instances_gn_tree(
		points_obj,
		unit_scale,
		attr_name=attr_name,
	)
	modifier = assign_gn_modifier(lines_obj, node_group, modifier_name=modifier_name)
	return modifier, node_group
