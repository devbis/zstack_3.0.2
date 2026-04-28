include(CMakeParseArguments)

function(zstack_add_znp_cc2530_with_sbl_target)
  set(options)
  set(oneValueArgs NAME PROFILE SOURCE_ROOT TOOLCHAIN_ROOT PORT_INCLUDE_DIR WORK_ROOT IMPORT_BUNDLE_DIR OUTPUT_BASE_DIR PYTHON_EXECUTABLE)
  cmake_parse_arguments(ARG "${options}" "${oneValueArgs}" "" ${ARGN})

  foreach(required_arg NAME PROFILE SOURCE_ROOT TOOLCHAIN_ROOT WORK_ROOT OUTPUT_BASE_DIR PYTHON_EXECUTABLE)
    if(NOT ARG_${required_arg})
      message(FATAL_ERROR "zstack_add_znp_cc2530_with_sbl_target missing required argument: ${required_arg}")
    endif()
  endforeach()

  set(repo_root "${ARG_SOURCE_ROOT}")
  set(sdk_source_dir "${repo_root}/z-stack_3.0.2")
  set(patch_file "${repo_root}/firmware_CC2531_CC2530.patch")
  set(sdcc_tools_dir "${sdk_source_dir}/Tools/sdcc")
  set(importer_script "${sdcc_tools_dir}/iar_import.py")
  set(native_plan_script "${sdcc_tools_dir}/gen_native_cmake_plan.py")
  set(znp_project_file "${sdk_source_dir}/Projects/zstack/ZNP/CC253x/CC2530.ewp")
  set(znp_config_name "ZNP-with-SBL")
  set(project_name "CC2530ZNP-with-SBL")

  if(NOT EXISTS "${sdk_source_dir}")
    message(FATAL_ERROR "Missing vendored SDK tree: ${sdk_source_dir}")
  endif()
  if(NOT EXISTS "${patch_file}")
    message(FATAL_ERROR "Missing vendor patch: ${patch_file}")
  endif()
  if(NOT EXISTS "${importer_script}")
    message(FATAL_ERROR "Missing IAR import script: ${importer_script}")
  endif()
  if(NOT EXISTS "${native_plan_script}")
    message(FATAL_ERROR "Missing native CMake plan script: ${native_plan_script}")
  endif()

  set_property(
    DIRECTORY
    APPEND
    PROPERTY CMAKE_CONFIGURE_DEPENDS
    "${importer_script}"
    "${znp_project_file}"
    "${patch_file}"
  )

  set(work_root "${ARG_WORK_ROOT}")
  set(stamps_dir "${work_root}/stamps")
  set(artifact_dir "${ARG_OUTPUT_BASE_DIR}/${ARG_PROFILE}")
  set(sdcc_work_dir "${work_root}/sdcc-work")
  set(hex_file "${artifact_dir}/${project_name}.hex")
  set(ihx_file "${artifact_dir}/${project_name}.ihx")
  set(mem_file "${artifact_dir}/${project_name}.mem")
  set(logical_hex_file "${artifact_dir}/${project_name}.logical.hex")

  if(ARG_IMPORT_BUNDLE_DIR)
    set(import_bundle_dir "${ARG_IMPORT_BUNDLE_DIR}")
  else()
    set(import_bundle_dir "${work_root}/import/${ARG_PROFILE}")
  endif()
  set(import_stamp "${stamps_dir}/import-${ARG_PROFILE}.stamp")
  set(imported_source_root "${import_bundle_dir}/src")
  set(imported_manifest "${import_bundle_dir}/metadata/manifest.json")
  set(imported_cfg_header "${import_bundle_dir}/include/cc2530-znp-with-sbl-sdcc-cfg.h")
  set(imported_compile_plan "${import_bundle_dir}/compile-plan.json")

  if(NOT ARG_IMPORT_BUNDLE_DIR)
    execute_process(
      COMMAND
        "${ARG_PYTHON_EXECUTABLE}" "${importer_script}"
        --project "${znp_project_file}"
        --config "${znp_config_name}"
        --profile "${ARG_PROFILE}"
        --out-dir "${import_bundle_dir}"
        --patch "${patch_file}"
      RESULT_VARIABLE configure_import_rv
      OUTPUT_VARIABLE configure_import_stdout
      ERROR_VARIABLE configure_import_stderr
    )
    if(NOT configure_import_rv EQUAL 0)
      message(
        FATAL_ERROR
        "Failed to generate configure-time import bundle for profile '${ARG_PROFILE}'.\n${configure_import_stdout}${configure_import_stderr}"
      )
    endif()
  endif()

  if(NOT EXISTS "${ARG_TOOLCHAIN_ROOT}/bin/sdcc")
    message(FATAL_ERROR "SDCC_TOOLCHAIN_ROOT does not contain bin/sdcc: ${ARG_TOOLCHAIN_ROOT}")
  endif()
  set(toolchain_root "${ARG_TOOLCHAIN_ROOT}")

  if(ARG_IMPORT_BUNDLE_DIR)
    if(NOT EXISTS "${imported_source_root}")
      message(FATAL_ERROR "Provided ZSTACK_IMPORT_BUNDLE_DIR does not contain src/: ${import_bundle_dir}")
    endif()
    if(NOT EXISTS "${imported_manifest}")
      message(FATAL_ERROR "Provided ZSTACK_IMPORT_BUNDLE_DIR does not contain metadata/manifest.json: ${import_bundle_dir}")
    endif()
    if(NOT EXISTS "${imported_cfg_header}")
      message(FATAL_ERROR "Provided ZSTACK_IMPORT_BUNDLE_DIR does not contain include/cc2530-znp-with-sbl-sdcc-cfg.h: ${import_bundle_dir}")
    endif()
    if(NOT EXISTS "${imported_compile_plan}")
      message(FATAL_ERROR "Provided ZSTACK_IMPORT_BUNDLE_DIR does not contain compile-plan.json: ${import_bundle_dir}")
    endif()

    file(GLOB_RECURSE import_bundle_inputs CONFIGURE_DEPENDS "${import_bundle_dir}/*")
    add_custom_command(
      OUTPUT "${import_stamp}"
      COMMAND "${CMAKE_COMMAND}" -E make_directory "${stamps_dir}"
      COMMAND "${CMAKE_COMMAND}" -E touch "${import_stamp}"
      DEPENDS ${import_bundle_inputs}
      COMMENT "Using pre-generated IAR import bundle"
      VERBATIM
    )
  else()
    file(GLOB_RECURSE sdk_import_inputs CONFIGURE_DEPENDS "${sdk_source_dir}/*")
    file(GLOB_RECURSE sdcc_tool_inputs CONFIGURE_DEPENDS "${sdcc_tools_dir}/*")

    add_custom_command(
      OUTPUT "${import_stamp}"
      COMMAND "${CMAKE_COMMAND}" -E make_directory "${stamps_dir}"
      COMMAND
        "${ARG_PYTHON_EXECUTABLE}" "${importer_script}"
        --project "${znp_project_file}"
        --config "${znp_config_name}"
        --profile "${ARG_PROFILE}"
        --out-dir "${import_bundle_dir}"
        --patch "${patch_file}"
      COMMAND "${CMAKE_COMMAND}" -E touch "${import_stamp}"
      DEPENDS
        ${sdk_import_inputs}
        ${sdcc_tool_inputs}
        "${patch_file}"
      COMMENT "Importing IAR project bundle"
      VERBATIM
    )
  endif()

  set(native_dir "${CMAKE_CURRENT_BINARY_DIR}/native/${ARG_PROFILE}")
  set(native_entries_dir "${native_dir}/entries")
  set(native_plan_cmake "${native_dir}/plan.cmake")

  execute_process(
    COMMAND
      "${ARG_PYTHON_EXECUTABLE}" "${native_plan_script}"
      --compile-plan "${imported_compile_plan}"
      --workspace-root "${import_bundle_dir}"
      --obj-dir "${artifact_dir}/obj"
      --entries-dir "${native_entries_dir}"
      --cmake-out "${native_plan_cmake}"
    RESULT_VARIABLE native_plan_rv
    OUTPUT_VARIABLE native_plan_stdout
    ERROR_VARIABLE native_plan_stderr
  )
  if(NOT native_plan_rv EQUAL 0)
    message(
      FATAL_ERROR
      "Failed to generate native compile plan for profile '${ARG_PROFILE}'.\n${native_plan_stdout}${native_plan_stderr}"
    )
  endif()
  include("${native_plan_cmake}")

  set(build_env
    "PYTHON_BIN=${ARG_PYTHON_EXECUTABLE}"
    "SDCC_BUILD_DIR=${sdcc_work_dir}"
    "SDCC_TOOLCHAIN_DIR=${toolchain_root}"
    "MANIFEST=${imported_manifest}"
    "CFG_HEADER=${imported_cfg_header}"
    "ZNP_SDCC_PROFILE=${ARG_PROFILE}"
  )
  if(ARG_PORT_INCLUDE_DIR)
    list(APPEND build_env "SDCC_PORT_INC_DIR=${ARG_PORT_INCLUDE_DIR}")
  endif()

  set(prepare_native_stamp "${stamps_dir}/prepare-native-${ARG_PROFILE}.stamp")
  add_custom_command(
    OUTPUT "${prepare_native_stamp}"
    COMMAND "${CMAKE_COMMAND}" -E make_directory "${artifact_dir}"
    COMMAND "${CMAKE_COMMAND}" -E make_directory "${sdcc_work_dir}"
    COMMAND
      "${CMAKE_COMMAND}" -E env
      ${build_env}
      "BUILD_SAMPLELIGHT_MODE=prepare-native"
      bash "${imported_source_root}/Tools/sdcc/build_znp_cc2530_with_sbl.sh" "${artifact_dir}"
    COMMAND "${CMAKE_COMMAND}" -E touch "${prepare_native_stamp}"
    DEPENDS
      "${import_stamp}"
      "${imported_manifest}"
      "${imported_cfg_header}"
      "${imported_compile_plan}"
      "${repo_root}/cmake/ZStackSDCC.cmake"
      "${imported_source_root}/Tools/sdcc/build_samplelight.sh"
    COMMENT "Preparing native SDCC build state"
    VERBATIM
  )

  set(entry_count 0)
  list(LENGTH ZSTACK_NATIVE_OBJECTS entry_count)
  if(entry_count GREATER 0)
    math(EXPR entry_last "${entry_count} - 1")
    foreach(entry_index RANGE 0 ${entry_last})
      list(GET ZSTACK_NATIVE_OBJECTS ${entry_index} object_file)
      list(GET ZSTACK_NATIVE_ENTRY_FILES ${entry_index} entry_file)
      list(GET ZSTACK_NATIVE_COMPILE_SOURCES ${entry_index} compile_source)
      get_filename_component(object_dir "${object_file}" DIRECTORY)
      file(RELATIVE_PATH compile_rel "${imported_source_root}" "${compile_source}")
      add_custom_command(
        OUTPUT "${object_file}"
        COMMAND "${CMAKE_COMMAND}" -E make_directory "${object_dir}"
        COMMAND
          "${CMAKE_COMMAND}" -E env
          ${build_env}
          "BUILD_SAMPLELIGHT_MODE=compile-entry"
          "ENTRY_JSON_FILE=${entry_file}"
          bash "${imported_source_root}/Tools/sdcc/build_znp_cc2530_with_sbl.sh" "${artifact_dir}"
        DEPENDS
          "${prepare_native_stamp}"
          "${entry_file}"
          "${compile_source}"
          "${imported_manifest}"
          "${imported_cfg_header}"
          "${imported_compile_plan}"
          "${imported_source_root}/Tools/sdcc/build_samplelight.sh"
        COMMENT "Compiling ${compile_rel}"
        VERBATIM
      )
    endforeach()
  endif()

  add_custom_command(
    OUTPUT
      "${hex_file}"
      "${ihx_file}"
      "${mem_file}"
    BYPRODUCTS
      "${logical_hex_file}"
    COMMAND "${CMAKE_COMMAND}" -E make_directory "${artifact_dir}"
    COMMAND "${CMAKE_COMMAND}" -E make_directory "${sdcc_work_dir}"
    COMMAND
      "${CMAKE_COMMAND}" -E env
      ${build_env}
      "BUILD_SAMPLELIGHT_MODE=link-only"
      "REUSE_OBJECTS=1"
      bash "${imported_source_root}/Tools/sdcc/build_znp_cc2530_with_sbl.sh" "${artifact_dir}"
    DEPENDS
      "${prepare_native_stamp}"
      ${ZSTACK_NATIVE_OBJECTS}
      "${repo_root}/cmake/ZStackSDCC.cmake"
    COMMENT "Building ${project_name} (${ARG_PROFILE})"
    VERBATIM
  )

  add_custom_target("${ARG_NAME}" ALL DEPENDS "${prepare_native_stamp}" ${ZSTACK_NATIVE_OBJECTS})
  add_custom_target("${ARG_NAME}_import" DEPENDS "${import_stamp}")
  add_custom_target("${ARG_NAME}_prepare" DEPENDS "${prepare_native_stamp}")
  add_custom_target("${ARG_NAME}_hex" DEPENDS "${hex_file}")
  add_custom_target("${ARG_NAME}_ihx" DEPENDS "${ihx_file}")
  add_custom_target("${ARG_NAME}_mem" DEPENDS "${mem_file}")

  set("${ARG_NAME}_ARTIFACT_DIR" "${artifact_dir}" PARENT_SCOPE)
  set("${ARG_NAME}_HEX" "${hex_file}" PARENT_SCOPE)
  set("${ARG_NAME}_IHX" "${ihx_file}" PARENT_SCOPE)
  set("${ARG_NAME}_MEM" "${mem_file}" PARENT_SCOPE)
endfunction()
