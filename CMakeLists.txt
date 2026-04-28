cmake_minimum_required(VERSION 3.20)

project(zstack_sdcc NONE)

set(ZSTACK_PROFILE "balanced" CACHE STRING "ZNP SDCC profile to build")
set_property(CACHE ZSTACK_PROFILE PROPERTY STRINGS full balanced lean)

set(_default_sdcc_toolchain_root "")
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/../sdcc-build/bin/sdcc")
  set(_default_sdcc_toolchain_root "${CMAKE_CURRENT_SOURCE_DIR}/../sdcc-build")
elseif(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/../sdcc-linux/bin/sdcc")
  set(_default_sdcc_toolchain_root "${CMAKE_CURRENT_SOURCE_DIR}/../sdcc-linux")
endif()

set(
  SDCC_TOOLCHAIN_ROOT
  "${_default_sdcc_toolchain_root}"
  CACHE PATH
  "Existing SDCC toolchain root. Leave empty to download the published Linux AMD64 toolchain."
)
set(_default_sdcc_port_include_dir "")
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/../sdcc/device/include/mcs51")
  set(_default_sdcc_port_include_dir "${CMAKE_CURRENT_SOURCE_DIR}/../sdcc/device/include/mcs51")
endif()
set(
  SDCC_TOOLCHAIN_URL
  ""
  CACHE STRING
  "SDCC toolchain archive URL used when SDCC_TOOLCHAIN_ROOT is empty."
)
set(
  SDCC_PORT_INCLUDE_DIR
  "${_default_sdcc_port_include_dir}"
  CACHE PATH
  "Optional override for the SDCC mcs51 include directory when the toolchain root does not ship device/include/mcs51."
)
set(
  ZSTACK_WORK_ROOT
  "${CMAKE_BINARY_DIR}/work"
  CACHE PATH
  "Workspace used for staged SDK copies, generated toolchain overlay, and intermediate artifacts."
)
set(
  ZSTACK_IMPORT_BUNDLE_DIR
  ""
  CACHE PATH
  "Optional pre-generated import bundle directory produced by Tools/sdcc/iar_import.py."
)
set(
  ZSTACK_OUTPUT_BASE_DIR
  "${CMAKE_BINARY_DIR}/out/znp_cc2530_with_sbl"
  CACHE PATH
  "Base output directory for generated firmware artifacts."
)

set(_zstack_supported_profiles full balanced lean)
if(NOT ZSTACK_PROFILE IN_LIST _zstack_supported_profiles)
  message(
    FATAL_ERROR
    "Unsupported ZSTACK_PROFILE='${ZSTACK_PROFILE}'. Expected one of: ${_zstack_supported_profiles}"
  )
endif()
if(NOT SDCC_TOOLCHAIN_ROOT AND NOT SDCC_TOOLCHAIN_URL)
  message(
    FATAL_ERROR
    "Set either SDCC_TOOLCHAIN_ROOT or SDCC_TOOLCHAIN_URL before configuring."
  )
endif()

find_package(Python3 REQUIRED COMPONENTS Interpreter)

include("${CMAKE_CURRENT_SOURCE_DIR}/cmake/ZStackSDCC.cmake")

zstack_add_znp_cc2530_with_sbl_target(
  NAME znp_cc2530_with_sbl
  PROFILE "${ZSTACK_PROFILE}"
  SOURCE_ROOT "${CMAKE_CURRENT_SOURCE_DIR}"
  TOOLCHAIN_ROOT "${SDCC_TOOLCHAIN_ROOT}"
  TOOLCHAIN_URL "${SDCC_TOOLCHAIN_URL}"
  PORT_INCLUDE_DIR "${SDCC_PORT_INCLUDE_DIR}"
  WORK_ROOT "${ZSTACK_WORK_ROOT}"
  IMPORT_BUNDLE_DIR "${ZSTACK_IMPORT_BUNDLE_DIR}"
  OUTPUT_BASE_DIR "${ZSTACK_OUTPUT_BASE_DIR}"
  PYTHON_EXECUTABLE "${Python3_EXECUTABLE}"
)

message(STATUS "Z-Stack SDCC profile: ${ZSTACK_PROFILE}")
message(STATUS "Firmware artifacts: ${ZSTACK_OUTPUT_BASE_DIR}/${ZSTACK_PROFILE}")
