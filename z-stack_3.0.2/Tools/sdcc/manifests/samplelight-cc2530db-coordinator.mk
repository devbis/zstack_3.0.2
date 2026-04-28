# Auto-generated from SampleLight.ewp CoordinatorEB

SAMPLELIGHT_CFG := CoordinatorEB

SAMPLELIGHT_PROJECT := /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Projects/zstack/HomeAutomation/SampleLight/CC2530DB/SampleLight.ewp

SAMPLELIGHT_DEFINES := \
  -DBDB_REPORTING\
  -DSECURE=1\
  -DTC_LINKKEY_JOIN\
  -DNV_INIT\
  -DNV_RESTORE\
  -DxZTOOL_P1\
  -DxMT_TASK\
  -DxMT_APP_FUNC\
  -DxMT_SYS_FUNC\
  -DxMT_ZDO_FUNC\
  -DxMT_ZDO_MGMT\
  -DxMT_APP_CNF_FUNC\
  -DLCD_SUPPORTED=DEBUG\
  -DMULTICAST_ENABLED=FALSE\
  -DZCL_READ\
  -DZCL_DISCOVER\
  -DZCL_WRITE\
  -DZCL_BASIC\
  -DZCL_IDENTIFY\
  -DZCL_ON_OFF\
  -DZCL_SCENES\
  -DZCL_GROUPS\
  -DZCL_LEVEL_CTRL

SAMPLELIGHT_INCLUDES := \
  -I$PROJ_DIR$\
  -I/Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Projects/zstack/HomeAutomation/SampleLight/Source\
  -I/Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Projects/zstack/HomeAutomation/Source\
  -I/Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Projects/zstack/ZMain/TI2530DB\
  -I/Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/hal/include\
  -I/Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/hal/target/CC2530EB\
  -I/Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mac/include\
  -I/Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mac/high_level\
  -I/Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mac/low_level/srf04\
  -I/Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mac/low_level/srf04/single_chip\
  -I/Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mt\
  -I/Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/osal/include\
  -I/Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/services/saddr\
  -I/Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/services/sdata\
  -I/Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/stack/af\
  -I/Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/stack/bdb\
  -I/Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/stack/gp\
  -I/Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/stack/nwk\
  -I/Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/stack/sapi\
  -I/Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/stack/sec\
  -I/Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/stack/sys\
  -I/Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/stack/zcl\
  -I/Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/stack/zdo\
  -I/Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/zmac\
  -I/Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/zmac/f8w

SAMPLELIGHT_SOURCES := \
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Projects/zstack/HomeAutomation/SampleLight/Source/OSAL_SampleLight.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Projects/zstack/HomeAutomation/Source/zcl_sampleapps_ui.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Projects/zstack/HomeAutomation/SampleLight/Source/zcl_samplelight.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Projects/zstack/HomeAutomation/SampleLight/Source/zcl_samplelight_data.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/stack/bdb/bdb.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/stack/bdb/bdb_FindingAndBinding.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/stack/bdb/bdb_Reporting.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/stack/bdb/bdb_tlCommissioning.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/stack/bdb/bdb_touchlink.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/stack/bdb/bdb_touchlink_initiator.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/stack/bdb/bdb_touchlink_target.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/stack/GP/gp_common.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/stack/GP/gp_proxyTbl.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/hal/common/hal_assert.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/hal/common/hal_drivers.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/hal/target/CC2530EB/hal_adc.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/hal/target/CC2530EB/hal_dma.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/hal/target/CC2530EB/hal_flash.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/hal/target/CC2530EB/hal_key.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/hal/target/CC2530EB/hal_lcd.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/hal/target/CC2530EB/hal_led.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/hal/target/CC2530EB/hal_sleep.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/hal/target/CC2530EB/hal_startup.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/hal/target/CC2530EB/hal_timer.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/hal/target/CC2530EB/hal_uart.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mac/high_level/mac_cfg.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mac/high_level/mac_pib.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mac/low_level/srf04/mac_autopend.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mac/low_level/srf04/mac_backoff_timer.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mac/low_level/srf04/mac_low_level.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mac/low_level/srf04/mac_radio.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mac/low_level/srf04/mac_rx.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mac/low_level/srf04/mac_rx_onoff.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mac/low_level/srf04/mac_sleep.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mac/low_level/srf04/mac_tx.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mac/low_level/srf04/single_chip/mac_csp_tx.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mac/low_level/srf04/single_chip/mac_mcu.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mac/low_level/srf04/single_chip/mac_mem.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mac/low_level/srf04/single_chip/mac_radio_defs.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mac/low_level/srf04/single_chip/mac_rffrontend.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mt/DebugTrace.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mt/MT.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mt/MT_AF.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mt/MT_APP.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mt/MT_APP_CONFIG.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mt/MT_DEBUG.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mt/MT_GP.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mt/MT_NWK.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mt/MT_SAPI.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mt/MT_SYS.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mt/MT_TASK.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mt/MT_UART.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mt/MT_UTIL.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mt/MT_VERSION.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/mt/MT_ZDO.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/stack/nwk/BindingTable.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/stack/nwk/nwk_globals.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/stack/nwk/stub_aps.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/stack/sys/ZDiags.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/stack/sys/ZGlobals.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/osal/common/OSAL.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/osal/common/OSAL_Clock.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/osal/mcu/cc2530/OSAL_Math.s51\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/osal/common/OSAL_Memory.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/osal/mcu/cc2530/OSAL_Nv.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/osal/common/OSAL_PwrMgr.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/osal/common/OSAL_Timers.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/stack/af/AF.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/stack/zcl/zcl.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/stack/zcl/zcl_diagnostic.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/stack/zcl/zcl_general.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/stack/zcl/zcl_green_power.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Projects/zstack/HomeAutomation/Source/zcl_ha.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/services/saddr/saddr.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/stack/zdo/ZDApp.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/stack/zdo/ZDConfig.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/stack/zdo/ZDNwkMgr.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/stack/zdo/ZDObject.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/stack/zdo/ZDProfile.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/stack/zdo/ZDSecMgr.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/zmac/f8w/zmac.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Components/zmac/f8w/zmac_cb.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Projects/zstack/ZMain/TI2530DB/chipcon_cstartup.s51\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Projects/zstack/ZMain/TI2530DB/OnBoard.c\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Projects/zstack/ZMain/TI2530DB/ZMain.c

SAMPLELIGHT_CFG_FILES := \
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Projects/zstack/Tools/CC2530DB/f8wCoord.cfg\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Projects/zstack/Tools/CC2530DB/f8wConfig.cfg\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Projects/zstack/Tools/CC2530DB/f8wZCL.cfg

SAMPLELIGHT_IAR_LIBS := \
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Projects/zstack/Libraries/TI2530DB/bin/Router-Pro.lib\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Projects/zstack/Libraries/TI2530DB/bin/Security.lib\
  /Users/ivan.belokobylskiy/projects/ti/sdcc-dev/Z-Stack_3.0.2/Projects/zstack/Libraries/TIMAC/bin/TIMAC-CC2530.lib
