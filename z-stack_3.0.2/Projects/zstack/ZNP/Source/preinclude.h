#if defined FIRMWARE_SBL
  #define MAKE_CRC_SHDW
#else
  #define FAKE_CRC_SHDW
#endif

// Shared accross all firmwares
#define TC_LINKKEY_JOIN
#define ASSERT_RESET
#define INCLUDE_REVISION_INFORMATION
#define SECURE 1
#define BDB_FINDING_BINDING_CAPABILITY_ENABLED 0
#define ZDSECMGR_TC_DEVICE_MAX 40
#define DISABLE_GREENPOWER_BASIC_PROXY
#define MT_SYS_KEY_MANAGEMENT 1
#define TP2_LEGACY_ZC

// Increase NWK_LINK_STATUS_PERIOD to reduce amount of messages on the network
#define NWK_LINK_STATUS_PERIOD 60

// Save memory
#undef NWK_MAX_BINDING_ENTRIES
#define NWK_MAX_BINDING_ENTRIES 1
#undef APS_MAX_GROUPS
#define APS_MAX_GROUPS 1

// Disabling MULTICAST is required in order for proper group support.
// If MULTICAST is not disabled, the group adress is not included in the APS header
#define MULTICAST_ENABLED FALSE

// Save memory, see swra635.pdf
#define HAL_LCD FALSE
#define HAL_ADC FALSE

/**
 * Reduce BCAST_DELIVERY_TIME and increase MAX_BCAST time.
 * BCAST_DELIVERY_TIME is the length of time a broadcast message is kept in the broadcast table
 * MAX_BCAST is the max number of messages that are in the broadcast table
 * If e.g. BCAST_DELIVERY_TIME = 1 second and MAX_BCAST = 10; 10 broadcast messages per second can be send.
 *
 * Zigbee2mqtt has a fixed delay of 170ms between each command.
 * Therefore a BCAST_DELIVERY_TIME = 20 (= 2 seconds) and MAX_BCAST = 12 allows us to send
 * 2 / 12 = 1 group command per 166ms, which is just below the zigbee2mqtt delay.
 * Therefore the broadcast table will never get full.
 */
#define BCAST_DELIVERY_TIME 20
#undef MAX_BCAST // avoids incompatible redefinition of macro warning
#define MAX_BCAST 12

/**
 * Enable MTO routing, but disable source routing.
 * https://github.com/Koenkk/zigbee2mqtt/issues/1408
 */
#define CONCENTRATOR_ENABLE TRUE
#define CONCENTRATOR_ROUTE_CACHE FALSE
#define CONCENTRATOR_DISCOVERY_TIME 120
#define MAX_RTG_SRC_ENTRIES 1 // Source table is not used, reduce to minimal size
#undef MAX_RTG_ENTRIES
#define MAX_RTG_ENTRIES 40
#define MAX_NEIGHBOR_ENTRIES 8

#if defined(__SDCC)
/* CC2530 radio RAM aliases that are present in IAR headers but missing in the
 * current SDCC cc2530 device header used by this build.
 */
#ifndef XREG
#define XREG(addr) (*((volatile unsigned char __xdata *)(addr)))
#endif
#ifndef SRCRESINDEX
__xdata volatile unsigned char __at(0x6163) SRCRESINDEX;
#endif
#ifndef SRCEXTPENDEN0
__xdata volatile unsigned char __at(0x6164) SRCEXTPENDEN0;
__xdata volatile unsigned char __at(0x6165) SRCEXTPENDEN1;
__xdata volatile unsigned char __at(0x6166) SRCEXTPENDEN2;
#endif
#ifndef SRCSHORTPENDEN0
__xdata volatile unsigned char __at(0x6167) SRCSHORTPENDEN0;
__xdata volatile unsigned char __at(0x6168) SRCSHORTPENDEN1;
__xdata volatile unsigned char __at(0x6169) SRCSHORTPENDEN2;
#endif
#ifndef SRC_ADDR_TABLE
#define SRC_ADDR_TABLE ((volatile unsigned char __xdata *)0x6100)
#endif
#ifndef PAN_ID0
#define PAN_ID0 PANIDL
#define PAN_ID1 PANIDH
#endif
#ifndef SHORT_ADDR0
#define SHORT_ADDR0 SHORTADDRL
#define SHORT_ADDR1 SHORTADDRH
#endif
#ifndef EXT_ADDR0
#define EXT_ADDR0 IEEE_ADDR
#endif
#endif

// CC2531
#if defined FIRMWARE_CC2531
  #define NWK_MAX_DEVICE_LIST 15
  #define CC2531ZNP
  #define MAXMEMHEAP 3203

// CC2530
#elif defined FIRMWARE_CC2530
  #define HAL_UART_DMA_RX_MAX 128
  #define ENABLE_MT_SYS_RESET_SHUTDOWN
  #define ZTOOL_P1
  #define CC2530_MK
  #define NWK_MAX_DEVICE_LIST 10
  #define MAXMEMHEAP 3225

// CC2530 + CC2591
#elif defined FIRMWARE_CC2530_CC2591
  #define ENABLE_MT_SYS_RESET_SHUTDOWN
  #define ZTOOL_P1
  #define HAL_UART_DMA_RX_MAX 128
  #define HAL_PA_LNA
  #define NWK_MAX_DEVICE_LIST 10
  #define MAXMEMHEAP 3223

// CC2530 + CC2592
#elif defined FIRMWARE_CC2530_CC2592
  #define ENABLE_MT_SYS_RESET_SHUTDOWN
  #define ZTOOL_P1
  #define HAL_UART_DMA_RX_MAX 128
  #define HAL_PA_LNA_CC2592
  #define NWK_MAX_DEVICE_LIST 10
  #define MAXMEMHEAP 3223

#endif
