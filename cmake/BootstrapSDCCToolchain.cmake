if(
  NOT DEFINED DOWNLOAD_URL OR
  NOT DEFINED DOWNLOAD_TARBALL OR
  NOT DEFINED DOWNLOAD_ROOT OR
  NOT DEFINED OVERLAY_ROOT OR
  NOT DEFINED SDCPP_TEMPLATE OR
  NOT DEFINED STAMP_FILE
)
  message(
    FATAL_ERROR
    "BootstrapSDCCToolchain.cmake requires DOWNLOAD_URL, DOWNLOAD_TARBALL, DOWNLOAD_ROOT, OVERLAY_ROOT, SDCPP_TEMPLATE, and STAMP_FILE"
  )
endif()

function(_resolve_toolchain_root base_dir out_var)
  if(EXISTS "${base_dir}/bin/sdcc")
    set(${out_var} "${base_dir}" PARENT_SCOPE)
    return()
  endif()

  file(GLOB _children LIST_DIRECTORIES true "${base_dir}/*")
  foreach(_child IN LISTS _children)
    if(EXISTS "${_child}/bin/sdcc")
      set(${out_var} "${_child}" PARENT_SCOPE)
      return()
    endif()
  endforeach()

  set(${out_var} "" PARENT_SCOPE)
endfunction()

set(_real_toolchain_root "")
if(DEFINED INPUT_TOOLCHAIN_ROOT AND NOT INPUT_TOOLCHAIN_ROOT STREQUAL "")
  _resolve_toolchain_root("${INPUT_TOOLCHAIN_ROOT}" _real_toolchain_root)
  if(_real_toolchain_root STREQUAL "")
    message(FATAL_ERROR "SDCC_TOOLCHAIN_ROOT does not contain bin/sdcc: ${INPUT_TOOLCHAIN_ROOT}")
  endif()
else()
  _resolve_toolchain_root("${DOWNLOAD_ROOT}" _real_toolchain_root)
  if(_real_toolchain_root STREQUAL "")
    get_filename_component(_tarball_parent "${DOWNLOAD_TARBALL}" DIRECTORY)
    file(MAKE_DIRECTORY "${_tarball_parent}")
    file(MAKE_DIRECTORY "${DOWNLOAD_ROOT}")

    if(NOT EXISTS "${DOWNLOAD_TARBALL}")
      file(DOWNLOAD "${DOWNLOAD_URL}" "${DOWNLOAD_TARBALL}" SHOW_PROGRESS STATUS _download_status)
      list(GET _download_status 0 _download_code)
      list(GET _download_status 1 _download_message)
      if(NOT _download_code EQUAL 0)
        message(FATAL_ERROR "Failed to download SDCC toolchain: ${_download_message}")
      endif()
    endif()

    file(REMOVE_RECURSE "${DOWNLOAD_ROOT}")
    file(MAKE_DIRECTORY "${DOWNLOAD_ROOT}")
    execute_process(
      COMMAND "${CMAKE_COMMAND}" -E tar xf "${DOWNLOAD_TARBALL}"
      WORKING_DIRECTORY "${DOWNLOAD_ROOT}"
      RESULT_VARIABLE _extract_rv
    )
    if(NOT _extract_rv EQUAL 0)
      message(FATAL_ERROR "Failed to extract SDCC toolchain archive: ${DOWNLOAD_TARBALL}")
    endif()

    _resolve_toolchain_root("${DOWNLOAD_ROOT}" _real_toolchain_root)
    if(_real_toolchain_root STREQUAL "")
      message(FATAL_ERROR "Unable to locate extracted SDCC toolchain root under ${DOWNLOAD_ROOT}")
    endif()
  endif()
endif()

file(REMOVE_RECURSE "${OVERLAY_ROOT}")
file(MAKE_DIRECTORY "${OVERLAY_ROOT}")

file(GLOB _top_level_entries RELATIVE "${_real_toolchain_root}" "${_real_toolchain_root}/*")
foreach(_entry IN LISTS _top_level_entries)
  if(_entry STREQUAL "bin")
    continue()
  endif()
  file(CREATE_LINK "${_real_toolchain_root}/${_entry}" "${OVERLAY_ROOT}/${_entry}" SYMBOLIC)
endforeach()

file(MAKE_DIRECTORY "${OVERLAY_ROOT}/bin")
file(GLOB _bin_entries RELATIVE "${_real_toolchain_root}/bin" "${_real_toolchain_root}/bin/*")
foreach(_entry IN LISTS _bin_entries)
  if(_entry STREQUAL "sdcpp" OR _entry STREQUAL "sdcpp.exe")
    continue()
  endif()
  file(CREATE_LINK "${_real_toolchain_root}/bin/${_entry}" "${OVERLAY_ROOT}/bin/${_entry}" SYMBOLIC)
endforeach()

configure_file("${SDCPP_TEMPLATE}" "${OVERLAY_ROOT}/bin/sdcpp" @ONLY NEWLINE_STYLE UNIX)
file(
  CHMOD "${OVERLAY_ROOT}/bin/sdcpp"
  PERMISSIONS
    OWNER_READ OWNER_WRITE OWNER_EXECUTE
    GROUP_READ GROUP_EXECUTE
    WORLD_READ WORLD_EXECUTE
)

get_filename_component(_stamp_parent "${STAMP_FILE}" DIRECTORY)
file(MAKE_DIRECTORY "${_stamp_parent}")
file(WRITE "${STAMP_FILE}" "${_real_toolchain_root}\n")
