add_library(quic_core
  packet_parser.cpp
  initial_crypto.cpp
  frame_parser.cpp
  crypto_reassembly.cpp
  client_hello.cpp)
target_include_directories(quic_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(quic_core PUBLIC OpenSSL::Crypto)
target_compile_options(quic_core PRIVATE -Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion)

if(QUIC_ENABLE_SANITIZERS AND CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(quic_core PUBLIC -fsanitize=address,undefined -fno-omit-frame-pointer)
  target_link_options(quic_core PUBLIC -fsanitize=address,undefined)
endif()

add_executable(quic-fingerprint main.cpp)
target_link_libraries(quic-fingerprint PRIVATE quic_core)
