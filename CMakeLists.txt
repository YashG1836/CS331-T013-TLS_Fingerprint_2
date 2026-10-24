cmake_minimum_required(VERSION 3.20)
project(cn_project_2 LANGUAGES CXX)

option(QUIC_ENABLE_SANITIZERS "Enable AddressSanitizer and UndefinedBehaviorSanitizer" OFF)
option(QUIC_BUILD_TESTS "Build C++ tests" ON)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
find_package(OpenSSL 3.0 REQUIRED COMPONENTS Crypto)

add_subdirectory(src/quic_fingerprint)
if(QUIC_BUILD_TESTS)
  enable_testing()
  add_subdirectory(tests/cpp)
endif()
