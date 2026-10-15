cmake_minimum_required(VERSION 3.16)
project(paintpro_native LANGUAGES CXX)
add_library(paintpro_native SHARED paintpro.cpp)
target_compile_features(paintpro_native PRIVATE cxx_std_17)
set_target_properties(paintpro_native PROPERTIES
    CXX_VISIBILITY_PRESET hidden
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/bin"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/bin")
foreach(config DEBUG RELEASE RELWITHDEBINFO MINSIZEREL)
    set_target_properties(paintpro_native PROPERTIES
        LIBRARY_OUTPUT_DIRECTORY_${config} "${CMAKE_CURRENT_SOURCE_DIR}/bin"
        RUNTIME_OUTPUT_DIRECTORY_${config} "${CMAKE_CURRENT_SOURCE_DIR}/bin")
endforeach()
if(MSVC)
    target_compile_options(paintpro_native PRIVATE /W4 /EHsc)
else()
    target_compile_options(paintpro_native PRIVATE -Wall -Wextra -Wpedantic)
endif()
