cmake_minimum_required(VERSION 3.18...3.27)
project(rapidobj LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Bind against whichever interpreter the build frontend selected.
find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)

# Fetch nanobind
include(FetchContent)
FetchContent_Declare(
  nanobind
  GIT_REPOSITORY https://github.com/wjakob/nanobind
  GIT_TAG        v2.4.0
)
FetchContent_MakeAvailable(nanobind)

# Build the extension module
nanobind_add_module(rapidobj src/rapidobj_ext.cpp)

target_include_directories(rapidobj PRIVATE ${CMAKE_SOURCE_DIR}/src)

# Install the extension module
install(TARGETS rapidobj LIBRARY DESTINATION .)

# Install typing metadata for IDE autocomplete and static checkers.
install(FILES
  ${CMAKE_SOURCE_DIR}/rapidobj.pyi
  ${CMAKE_SOURCE_DIR}/py.typed
  DESTINATION .
)
