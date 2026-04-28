if(NOT DEFINED SOURCE_SDK_DIR OR NOT DEFINED STAGED_SDK_DIR OR NOT DEFINED PATCH_FILE OR NOT DEFINED STAMP_FILE)
  message(FATAL_ERROR "StageZStackSDK.cmake requires SOURCE_SDK_DIR, STAGED_SDK_DIR, PATCH_FILE, and STAMP_FILE")
endif()

if(NOT EXISTS "${SOURCE_SDK_DIR}")
  message(FATAL_ERROR "Source SDK directory does not exist: ${SOURCE_SDK_DIR}")
endif()
if(NOT EXISTS "${PATCH_FILE}")
  message(FATAL_ERROR "Vendor patch does not exist: ${PATCH_FILE}")
endif()

get_filename_component(_stage_parent "${STAGED_SDK_DIR}" DIRECTORY)
file(REMOVE_RECURSE "${STAGED_SDK_DIR}")
file(MAKE_DIRECTORY "${_stage_parent}")

execute_process(
  COMMAND "${CMAKE_COMMAND}" -E copy_directory "${SOURCE_SDK_DIR}" "${STAGED_SDK_DIR}"
  RESULT_VARIABLE copy_rv
)
if(NOT copy_rv EQUAL 0)
  message(FATAL_ERROR "Failed to stage SDK copy into ${STAGED_SDK_DIR}")
endif()

execute_process(
  COMMAND patch -d "${STAGED_SDK_DIR}" --forward -p1 -i "${PATCH_FILE}"
  RESULT_VARIABLE patch_rv
  OUTPUT_VARIABLE patch_stdout
  ERROR_VARIABLE patch_stderr
)
if(NOT patch_rv EQUAL 0)
  message(FATAL_ERROR "Failed to apply ${PATCH_FILE} in ${STAGED_SDK_DIR}\n${patch_stdout}${patch_stderr}")
endif()

get_filename_component(_stamp_parent "${STAMP_FILE}" DIRECTORY)
file(MAKE_DIRECTORY "${_stamp_parent}")
file(WRITE "${STAMP_FILE}" "staged\n")
