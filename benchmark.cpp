#include "rapidobj.hpp"

#include <algorithm>
#include <chrono>
#include <iostream>
#include <numeric>
#include <vector>

int main(int argc, char **argv) {
  if (argc < 2) {
    std::cerr << "Usage: " << argv[0] << " <obj_path> [iterations]\n";
    return 1;
  }

  const char *obj_path = argv[1];
  int iterations = argc > 2 ? std::stoi(argv[2]) : 5;

  std::cout << "Parsing: " << obj_path << "\n";
  std::cout << "Iterations: " << iterations << "\n";
  std::cout << "--------------------------------------------------\n";

  std::vector<double> times;
  rapidobj::Result result;

  for (int i = 0; i < iterations; ++i) {
    auto start = std::chrono::high_resolution_clock::now();

    result = rapidobj::ParseFile(obj_path);

    if (result.error) {
      std::cerr << "Error: " << result.error.code.message() << "\n";
      return 1;
    }

    rapidobj::Triangulate(result);

    auto end = std::chrono::high_resolution_clock::now();
    auto elapsed =
        std::chrono::duration<double, std::milli>(end - start).count();
    times.push_back(elapsed);
  }

  std::cout << "Parse times: [";
  for (size_t i = 0; i < times.size(); ++i) {
    if (i > 0)
      std::cout << ", ";
    std::cout << times[i];
  }
  std::cout << "] ms\n";

  double avg = std::accumulate(times.begin(), times.end(), 0.0) / times.size();
  double min_t = *std::min_element(times.begin(), times.end());
  double max_t = *std::max_element(times.begin(), times.end());

  std::cout << "Average: " << avg << " ms\n";
  std::cout << "Min: " << min_t << " ms\n";
  std::cout << "Max: " << max_t << " ms\n";

  // Count faces
  size_t face_count = 0;
  for (const auto &shape : result.shapes) {
    face_count += shape.mesh.indices.size() / 3;
  }

  std::cout << "\nVertices: (" << result.attributes.positions.size() / 3
            << ", 3)\n";
  std::cout << "Faces: (" << face_count << ", 3)\n";

  return 0;
}
