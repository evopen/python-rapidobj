import pymeshlab

meshset = pymeshlab.MeshSet()
meshset.load_new_mesh("/home/dhh/Downloads/rungholt/house.obj")

mesh = meshset.current_mesh()

print(mesh.vertex_number())
print(mesh.edge_number())
print(mesh.face_number())
print(mesh.has_wedge_tex_coord())

# print the required matrix

vertex_matrix = mesh.vertex_matrix()
assert vertex_matrix.shape[0] == mesh.vertex_number()
assert vertex_matrix.shape[1] == 3

face_matrix = mesh.face_matrix()
assert face_matrix.shape[0] == mesh.face_number()
assert face_matrix.shape[1] == 3

textures: dict[str, pymeshlab.pmeshlab.Image] = mesh.textures()

print(type(textures))

assert type(textures) == dict

wedge_tex_coord_matrix = mesh.wedge_tex_coord_matrix()

print(wedge_tex_coord_matrix)

print(textures)

print(vertex_matrix)
print(face_matrix)