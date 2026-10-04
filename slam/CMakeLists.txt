cmake_minimum_required(VERSION 3.16)
project(mini3_offline_mono LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

find_package(OpenCV REQUIRED)
find_package(Eigen3 REQUIRED)
find_package(Pangolin REQUIRED)

get_filename_component(REPO_ROOT "${CMAKE_SOURCE_DIR}/.." ABSOLUTE)
set(THIRD_PARTY_ROOT ${REPO_ROOT}/third_party)
set(ORB_ROOT ${THIRD_PARTY_ROOT}/ORB_SLAM3)

add_executable(offline_mono src/offline_mono.cpp)
target_compile_options(offline_mono PRIVATE -include ${CMAKE_SOURCE_DIR}/patches/pangolin_gcc13.h)
target_include_directories(offline_mono PRIVATE
  ${ORB_ROOT}
  ${ORB_ROOT}/include
  ${ORB_ROOT}/include/CameraModels
  ${ORB_ROOT}/Thirdparty/Sophus
  ${EIGEN3_INCLUDE_DIR}
  ${Pangolin_INCLUDE_DIRS}
)
target_link_libraries(offline_mono PRIVATE
  ${OpenCV_LIBS}
  ${ORB_ROOT}/lib/libORB_SLAM3.so
  ${ORB_ROOT}/Thirdparty/DBoW2/lib/libDBoW2.so
  ${ORB_ROOT}/Thirdparty/g2o/lib/libg2o.so
  ${Pangolin_LIBRARIES}
  boost_serialization
  crypto
)

set(_slam_rpath
  "$ORIGIN/../third_party/ORB_SLAM3/lib"
  "$ORIGIN/../third_party/ORB_SLAM3/Thirdparty/DBoW2/lib"
  "$ORIGIN/../third_party/ORB_SLAM3/Thirdparty/g2o/lib"
  "$ORIGIN/../third_party/pangolin-install/lib"
)
set_target_properties(offline_mono PROPERTIES
  RUNTIME_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}
  BUILD_RPATH "${ORB_ROOT}/lib;${ORB_ROOT}/Thirdparty/DBoW2/lib;${ORB_ROOT}/Thirdparty/g2o/lib;${THIRD_PARTY_ROOT}/pangolin-install/lib"
  INSTALL_RPATH "${_slam_rpath}"
)
