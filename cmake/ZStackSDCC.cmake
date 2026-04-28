include(CMakeParseArguments)

function(zstack_add_znp_cc2530_with_sbl_target)
  set(options)
  set(oneValueArgs NAME PROFILE SOURCE_ROOT TOOLCHAIN_ROOT TOOLCHAIN_URL PORT_INCLUDE_DIR WORK_ROOT OUTPUT_BASE_DIR PYTHON_EXECUTABLE)
  cmake_parse_arguments(ARG "${options}" "${oneValueArgs}" "" ${ARGN})

  foreach(required_arg NAME PROFILE SOURCE_ROOT TOOLCHAIN_URL WORK_ROOT OUTPUT_BASE_DIR PYTHON_EXECUTABLE)
    if(NOT ARG_${required_arg})
      message(FATAL_ERROR "zstack_add_znp_cc2530_with_sbl_target missing required argument: ${required_arg}")
    endif()
  endforeach()

  set(repo_root "${ARG_SOURCE_ROOT}")
  set(sdk_source_dir "${repo_root}/z-stack_3.0.2")
  set(patch_file "${repo_root}/firmware_CC2531_CC2530.patch")
  set(sdcc_tools_dir "${sdk_source_dir}/Tools/sdcc")
  set(prepare_script "${sdcc_tools_dir}/prepare_znp_cc2530_with_sbl.py")
  set(extract_script "${sdcc_tools_dir}/extract_iar_project.py")
  set(znp_project_file "${sdk_source_dir}/Projects/zstack/ZNP/CC253x/CC2530.ewp")
  set(znp_cfg_file "${sdk_source_dir}/Projects/zstack/ZNP/Source/znp.cfg")
  set(znp_preinclude_file "${sdk_source_dir}/Projects/zstack/ZNP/Source/preinclude.h")

  if(NOT EXISTS "${sdk_source_dir}")
    message(FATAL_ERROR "Missing vendored SDK tree: ${sdk_source_dir}")
  endif()
  if(NOT EXISTS "${patch_file}")
    message(FATAL_ERROR "Missing vendor patch: ${patch_file}")
  endif()
  if(NOT EXISTS "${prepare_script}")
    message(FATAL_ERROR "Missing SDCC preparation script: ${prepare_script}")
  endif()

  set_property(
    DIRECTORY
    APPEND
    PROPERTY CMAKE_CONFIGURE_DEPENDS
    "${prepare_script}"
    "${extract_script}"
    "${znp_project_file}"
    "${znp_cfg_file}"
    "${znp_preinclude_file}"
  )

  set(configure_output_dir "${CMAKE_CURRENT_BINARY_DIR}/generated/${ARG_PROFILE}")
  set(configure_manifest "${configure_output_dir}/znp-cc2530-with-sbl.manifest.json")
  set(configure_cfg_header "${configure_output_dir}/znp-cc2530-with-sbl-sdcc-cfg.h")
  set(configure_stage_dir "${configure_output_dir}/workspace/z-stack_3.0.2")
  set(configure_stage_stamp "${configure_output_dir}/configure-stage.stamp")
  set(configure_prepare_script "${configure_stage_dir}/Tools/sdcc/prepare_znp_cc2530_with_sbl.py")
  file(MAKE_DIRECTORY "${configure_output_dir}")

  execute_process(
    COMMAND
      "${CMAKE_COMMAND}"
      -DSOURCE_SDK_DIR=${sdk_source_dir}
      -DSTAGED_SDK_DIR=${configure_stage_dir}
      -DPATCH_FILE=${patch_file}
      -DSTAMP_FILE=${configure_stage_stamp}
      -P "${repo_root}/cmake/StageZStackSDK.cmake"
    RESULT_VARIABLE configure_stage_rv
    OUTPUT_VARIABLE configure_stage_stdout
    ERROR_VARIABLE configure_stage_stderr
  )
  if(NOT configure_stage_rv EQUAL 0)
    message(
      FATAL_ERROR
      "Failed to prepare staged SDK for configure-time manifest generation.\n${configure_stage_stdout}${configure_stage_stderr}"
    )
  endif()

  execute_process(
    COMMAND
      "${ARG_PYTHON_EXECUTABLE}" "${configure_prepare_script}"
      --profile "${ARG_PROFILE}"
      --output-manifest "${configure_manifest}"
      --output-header "${configure_cfg_header}"
    WORKING_DIRECTORY "${configure_stage_dir}"
    RESULT_VARIABLE prepare_rv
    OUTPUT_VARIABLE prepare_stdout
    ERROR_VARIABLE prepare_stderr
  )
  if(NOT prepare_rv EQUAL 0)
    message(
      FATAL_ERROR
      "Failed to generate ZNP manifest for profile '${ARG_PROFILE}'.\n${prepare_stdout}${prepare_stderr}"
    )
  endif()

  file(GLOB_RECURSE sdk_stage_inputs CONFIGURE_DEPENDS "${sdk_source_dir}/*")

  set(work_root "${ARG_WORK_ROOT}")
  set(stamps_dir "${work_root}/stamps")
  set(stage_workspace_dir "${work_root}/workspace")
  set(staged_sdk_dir "${stage_workspace_dir}/z-stack_3.0.2")
  set(stage_stamp "${stamps_dir}/stage-sdk-${ARG_PROFILE}.stamp")

  add_custom_command(
    OUTPUT "${stage_stamp}"
    COMMAND
      "${CMAKE_COMMAND}"
      -DSOURCE_SDK_DIR=${sdk_source_dir}
      -DSTAGED_SDK_DIR=${staged_sdk_dir}
      -DPATCH_FILE=${patch_file}
      -DSTAMP_FILE=${stage_stamp}
      -P "${repo_root}/cmake/StageZStackSDK.cmake"
    DEPENDS
      ${sdk_stage_inputs}
      "${patch_file}"
      "${repo_root}/cmake/StageZStackSDK.cmake"
    COMMENT "Staging patched Z-Stack SDK tree"
    VERBATIM
  )

  set(toolchain_download_root "${work_root}/toolchain-download")
  set(toolchain_tarball "${toolchain_download_root}/sdcc-toolchain.tar.xz")
  set(toolchain_extract_root "${toolchain_download_root}/raw")
  set(toolchain_overlay_root "${work_root}/sdcc-toolchain")
  set(toolchain_stamp "${stamps_dir}/toolchain-${ARG_PROFILE}.stamp")

  set(toolchain_deps
    "${repo_root}/cmake/BootstrapSDCCToolchain.cmake"
    "${repo_root}/cmake/sdcpp.in"
  )
  if(ARG_TOOLCHAIN_ROOT)
    list(APPEND toolchain_deps "${ARG_TOOLCHAIN_ROOT}/bin/sdcc")
  endif()

  add_custom_command(
    OUTPUT "${toolchain_stamp}"
    COMMAND
      "${CMAKE_COMMAND}"
      -DINPUT_TOOLCHAIN_ROOT=${ARG_TOOLCHAIN_ROOT}
      -DDOWNLOAD_URL=${ARG_TOOLCHAIN_URL}
      -DDOWNLOAD_TARBALL=${toolchain_tarball}
      -DDOWNLOAD_ROOT=${toolchain_extract_root}
      -DOVERLAY_ROOT=${toolchain_overlay_root}
      -DSDCPP_TEMPLATE=${repo_root}/cmake/sdcpp.in
      -DSTAMP_FILE=${toolchain_stamp}
      -P "${repo_root}/cmake/BootstrapSDCCToolchain.cmake"
    DEPENDS ${toolchain_deps}
    COMMENT "Preparing SDCC toolchain overlay"
    VERBATIM
  )

  set(artifact_dir "${ARG_OUTPUT_BASE_DIR}/${ARG_PROFILE}")
  set(sdcc_work_dir "${work_root}/sdcc-work")
  set(project_name "CC2530ZNP-with-SBL")
  set(hex_file "${artifact_dir}/${project_name}.hex")
  set(ihx_file "${artifact_dir}/${project_name}.ihx")
  set(mem_file "${artifact_dir}/${project_name}.mem")
  set(logical_hex_file "${artifact_dir}/${project_name}.logical.hex")
  set(build_env
    "PYTHON_BIN=${ARG_PYTHON_EXECUTABLE}"
    "SDCC_BUILD_DIR=${sdcc_work_dir}"
    "SDCC_TOOLCHAIN_DIR=${toolchain_overlay_root}"
    "MANIFEST=${configure_manifest}"
    "CFG_HEADER=${configure_cfg_header}"
    "ZNP_SDCC_PROFILE=${ARG_PROFILE}"
  )
  if(ARG_PORT_INCLUDE_DIR)
    list(APPEND build_env "SDCC_PORT_INC_DIR=${ARG_PORT_INCLUDE_DIR}")
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
      bash "${staged_sdk_dir}/Tools/sdcc/build_znp_cc2530_with_sbl.sh" "${artifact_dir}"
    DEPENDS
      "${stage_stamp}"
      "${toolchain_stamp}"
      "${configure_manifest}"
      "${configure_cfg_header}"
      "${repo_root}/cmake/ZStackSDCC.cmake"
    COMMENT "Building ${project_name} (${ARG_PROFILE})"
    VERBATIM
  )

  add_custom_target("${ARG_NAME}" ALL DEPENDS "${hex_file}" "${ihx_file}" "${mem_file}")

  set("${ARG_NAME}_ARTIFACT_DIR" "${artifact_dir}" PARENT_SCOPE)
  set("${ARG_NAME}_HEX" "${hex_file}" PARENT_SCOPE)
  set("${ARG_NAME}_IHX" "${ihx_file}" PARENT_SCOPE)
  set("${ARG_NAME}_MEM" "${mem_file}" PARENT_SCOPE)
endfunction()
