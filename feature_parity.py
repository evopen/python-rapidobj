import pymeshlab

meshset = pymeshlab.MeshSet()
meshset.load_new_mesh("/home/dhh/Downloads/rungholt/rungholt.obj")

print(meshset.current_mesh().vertex_number())
print(meshset.current_mesh().edge_number())
print(meshset.current_mesh().face_number())
