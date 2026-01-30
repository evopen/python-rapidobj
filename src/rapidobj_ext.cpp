#include "rapidobj.hpp"

#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>

#include <vector>

namespace nb = nanobind;

// Keep the rapidobj::Result alive - it owns all the data
// We only need to build the flattened face/wedge arrays
struct ObjData {
  rapidobj::Result result;
  std::vector<int> faces;                  // flat: [v0,v1,v2, ...]
  std::vector<int> wedge_texcoord_indices; // per-wedge index into texcoords
  std::vector<std::string> texture_paths;

  bool ok() const { return !result.error; }
  std::string error_message() const {
    return result.error ? result.error.code.message() : "";
  }
};

static ObjData *parse_obj_internal(const std::string &filename) {
  auto *data = new ObjData();
  data->result = rapidobj::ParseFile(filename);

  if (data->result.error) {
    return data;
  }

  // Collect texture paths from materials
  for (const auto &material : data->result.materials) {
    data->texture_paths.push_back(material.diffuse_texname);
  }

  // Triangulate in place
  rapidobj::Triangulate(data->result);

  // Pre-allocate faces and wedge indices
  size_t total_indices = 0;
  for (const auto &shape : data->result.shapes) {
    total_indices += shape.mesh.indices.size();
  }
  data->faces.reserve(total_indices);
  data->wedge_texcoord_indices.reserve(total_indices);

  // Build flattened face and wedge texcoord index arrays
  for (const auto &shape : data->result.shapes) {
    for (const auto &index : shape.mesh.indices) {
      data->faces.push_back(index.position_index);
      data->wedge_texcoord_indices.push_back(index.texcoord_index);
    }
  }

  return data;
}

// Python-exposed class that wraps ObjData with capsule ownership
class ObjParseResult {
public:
  ObjData *data;
  nb::capsule owner;

  ObjParseResult(ObjData *d)
      : data(d), owner(d, [](void *p) noexcept { delete (ObjData *)p; }) {}

  bool ok() const { return data->ok(); }
  std::string error_message() const { return data->error_message(); }

  int vertex_count() const {
    return static_cast<int>(data->result.attributes.positions.size() / 3);
  }
  int normal_count() const {
    return static_cast<int>(data->result.attributes.normals.size() / 3);
  }
  int uv_count() const {
    return static_cast<int>(data->result.attributes.texcoords.size() / 2);
  }
  int shape_count() const {
    return static_cast<int>(data->result.shapes.size());
  }
  int material_count() const {
    return static_cast<int>(data->result.materials.size());
  }
  const std::vector<std::string> &texture_paths() const {
    return data->texture_paths;
  }

  // Return vertices - ZERO COPY, points directly to rapidobj's Array
  nb::ndarray<nb::numpy, float, nb::shape<-1, 3>> vertices() {
    size_t n_vertices = data->result.attributes.positions.size() / 3;
    return nb::ndarray<nb::numpy, float, nb::shape<-1, 3>>(
        data->result.attributes.positions.data(), {n_vertices, 3}, owner);
  }

  // Return faces - points to our flattened vector
  nb::ndarray<nb::numpy, int, nb::shape<-1, 3>> faces() {
    size_t n_faces = data->faces.size() / 3;
    return nb::ndarray<nb::numpy, int, nb::shape<-1, 3>>(data->faces.data(),
                                                         {n_faces, 3}, owner);
  }

  // Return texcoords - ZERO COPY, points directly to rapidobj's Array
  nb::ndarray<nb::numpy, float, nb::shape<-1, 2>> texcoords() {
    size_t n_texcoords = data->result.attributes.texcoords.size() / 2;
    return nb::ndarray<nb::numpy, float, nb::shape<-1, 2>>(
        data->result.attributes.texcoords.data(), {n_texcoords, 2}, owner);
  }

  // Return wedge texcoord indices - points to our flattened vector
  nb::ndarray<nb::numpy, int, nb::shape<-1>> wedge_texcoord_indices() {
    return nb::ndarray<nb::numpy, int, nb::shape<-1>>(
        data->wedge_texcoord_indices.data(),
        {data->wedge_texcoord_indices.size()}, owner);
  }
};

ObjParseResult parse_obj(const std::string &filename) {
  return ObjParseResult(parse_obj_internal(filename));
}

NB_MODULE(rapidobj_ext, m) {
  m.doc() = "Fast OBJ file parser using rapidobj";

  nb::class_<ObjParseResult>(m, "ObjParseResult")
      .def_prop_ro("ok", &ObjParseResult::ok)
      .def_prop_ro("error_message", &ObjParseResult::error_message)
      .def_prop_ro("vertex_count", &ObjParseResult::vertex_count)
      .def_prop_ro("normal_count", &ObjParseResult::normal_count)
      .def_prop_ro("uv_count", &ObjParseResult::uv_count)
      .def_prop_ro("shape_count", &ObjParseResult::shape_count)
      .def_prop_ro("material_count", &ObjParseResult::material_count)
      .def_prop_ro("texture_paths", &ObjParseResult::texture_paths)
      .def_prop_ro("vertices", &ObjParseResult::vertices,
                   nb::rv_policy::reference)
      .def_prop_ro("faces", &ObjParseResult::faces, nb::rv_policy::reference)
      .def_prop_ro("texcoords", &ObjParseResult::texcoords,
                   nb::rv_policy::reference)
      .def_prop_ro("wedge_texcoord_indices",
                   &ObjParseResult::wedge_texcoord_indices,
                   nb::rv_policy::reference);

  m.def("parse_obj", &parse_obj, nb::arg("filename"),
        "Parse an OBJ file and return the result");
}
