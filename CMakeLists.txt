cmake_minimum_required(VERSION 3.18...3.27)
project(rapidobj_ext LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find Python and nanobind
find_package(Python 3.12 COMPONENTS Interpreter Development.Module REQUIRED)

# Fetch nanobind
include(FetchContent)
FetchContent_Declare(
  nanobind
  GIT_REPOSITORY https://github.com/wjakob/nanobind
  GIT_TAG        v2.4.0
)
FetchContent_MakeAvailable(nanobind)

# Build the extension module
nanobind_add_module(rapidobj_ext src/rapidobj_ext.cpp)

target_include_directories(rapidobj_ext PRIVATE ${CMAKE_SOURCE_DIR}/src)

# Install the extension module
install(TARGETS rapidobj_ext LIBRARY DESTINATION .)
