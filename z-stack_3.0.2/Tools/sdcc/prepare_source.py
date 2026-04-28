#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path


HAL_SLEEP_IMPL_OLD = (
    b"void halSetSleepMode(void)\r\n"
    b"{\r\n"
    b"  PCON = halSleepPconValue;\r\n"
    b"  HAL_DISABLE_INTERRUPTS();\r\n"
    b"}"
)
HAL_SLEEP_IMPL_NEW = (
    b"#if !defined(__SDCC)\n"
    b"void halSetSleepMode(void)\n"
    b"{\n"
    b"  PCON = halSleepPconValue;\n"
    b"  HAL_DISABLE_INTERRUPTS();\n"
    b"}\n"
    b"#endif"
)

HAL_SLEEP_OPTIMIZE_OLD = b"#pragma optimize=none"
HAL_SLEEP_OPTIMIZE_NEW = b"#if !defined(__SDCC)\n#pragma optimize=none\n#endif"

HAL_STARTUP_DECL_OLD = """#if (__CODE_MODEL__ == 2)
__near_func __root char
#else
__root char
#endif
__low_level_init(void);"""
HAL_STARTUP_DECL_NEW = "char __low_level_init(void) __nonbanked;"

HAL_STARTUP_DEF_OLD = """#if (__CODE_MODEL__ == 2)
__near_func __root char
#else
__root char
#endif
__low_level_init(void)"""
HAL_STARTUP_DEF_NEW = "char __low_level_init(void) __nonbanked"

HAL_STARTUP_PREFIX_OLD = """#ifdef __cplusplus
extern "C" {
#endif

#pragma language=extended"""
HAL_STARTUP_PREFIX_NEW = """#ifdef __cplusplus
extern "C" {
#endif

#ifdef __SDCC

unsigned char __sdcc_external_startup( void ) __nonbanked;

unsigned char __sdcc_external_startup( void ) __nonbanked
{
  // Map flash bank #1 into XDATA for access to "ROM mapped as data".
  MEMCTR = (MEMCTR & 0xF8) | 0x01;

  // Returning 0 keeps the standard SDCC data initialization sequence enabled.
  return 0;
}

#else

#pragma language=extended"""

HAL_STARTUP_SUFFIX_OLD = """#pragma language=default

#ifdef __cplusplus"""
HAL_STARTUP_SUFFIX_NEW = """#pragma language=default

#endif

#ifdef __cplusplus"""

OSAL_MATH_SIG_OLD = "__near_func uint32 osalMcuDivide31By16To16( uint32 dividend, uint16 divisor )"
OSAL_MATH_SIG_NEW = "uint32 osalMcuDivide31By16To16( uint32 dividend, uint16 divisor ) __nonbanked"

OSAL_NV_GLOBALS_OLD = """/*********************************************************************
 * GLOBAL VARIABLES
 */

#ifndef OAD_KEEP_NV_PAGES"""
OSAL_NV_GLOBALS_NEW = """/*********************************************************************
 * GLOBAL VARIABLES
 */

#if defined(__SDCC)
#define SDCC_ZIGNV_ADDRESS_SPACE_START ((unsigned long)(HAL_NV_PAGE_BEG) * (unsigned long)(HAL_FLASH_PAGE_SIZE))
#ifndef SDCC_SKIP_FLASH_RESERVATION_SENTINELS
#define SDCC_SKIP_FLASH_RESERVATION_SENTINELS 1
#endif
#endif

#ifndef OAD_KEEP_NV_PAGES"""

OSAL_NV_BUF_OLD = """#pragma location="ZIGNV_ADDRESS_SPACE"
__no_init uint8 _nvBuf[OSAL_NV_PAGES_USED * OSAL_NV_PAGE_SIZE];
#pragma required=_nvBuf"""
OSAL_NV_BUF_NEW = """#if defined(__SDCC)
#if !SDCC_SKIP_FLASH_RESERVATION_SENTINELS
const __code __at (SDCC_ZIGNV_ADDRESS_SPACE_START) uint8 _nvBuf[OSAL_NV_PAGES_USED * OSAL_NV_PAGE_SIZE];
#endif
#else
#pragma location="ZIGNV_ADDRESS_SPACE"
__no_init uint8 _nvBuf[OSAL_NV_PAGES_USED * OSAL_NV_PAGE_SIZE];
#pragma required=_nvBuf
#endif"""

ONBOARD_SIG_OLD = "__near_func void Onboard_soft_reset( void )"
ONBOARD_SIG_NEW = "void Onboard_soft_reset( void ) __nonbanked"

ONBOARD_GLOBALS_OLD = """/*********************************************************************
 * GLOBAL VARIABLES
 */

#if defined MAKE_CRC_SHDW"""
ONBOARD_GLOBALS_NEW = """/*********************************************************************
 * GLOBAL VARIABLES
 */

#if defined(__SDCC)
#define SDCC_FLASH_LAST_PAGE_START  ((HAL_NV_PAGE_END + 1UL) * HAL_FLASH_PAGE_SIZE)
#define SDCC_LOCK_BITS_ADDRESS      (SDCC_FLASH_LAST_PAGE_START + HAL_FLASH_PAGE_SIZE - HAL_FLASH_LOCK_BITS)
#define SDCC_IEEE_ADDRESS           (SDCC_LOCK_BITS_ADDRESS - HAL_FLASH_IEEE_SIZE)
#endif

#if defined MAKE_CRC_SHDW"""

ONBOARD_LOCKBITS_OLD = """#pragma location="LOCK_BITS_ADDRESS_SPACE"
__no_init uint8 _lockBits[16];
#pragma required=_lockBits"""
ONBOARD_LOCKBITS_NEW = """#if defined(__SDCC)
const __code __at (SDCC_LOCK_BITS_ADDRESS) uint8 _lockBits[16];
#else
#pragma location="LOCK_BITS_ADDRESS_SPACE"
__no_init uint8 _lockBits[16];
#pragma required=_lockBits
#endif"""

ONBOARD_NVIEEE_OLD = """#pragma location="IEEE_ADDRESS_SPACE"
__no_init uint8 _nvIEEE[Z_EXTADDR_LEN];
#pragma required=_nvIEEE"""
ONBOARD_NVIEEE_NEW = """#if defined(__SDCC)
const __code __at (SDCC_IEEE_ADDRESS) uint8 _nvIEEE[Z_EXTADDR_LEN];
#else
#pragma location="IEEE_ADDRESS_SPACE"
__no_init uint8 _nvIEEE[Z_EXTADDR_LEN];
#pragma required=_nvIEEE
#endif"""

ONBOARD_RESERVED_OLD = """#pragma location="RESERVED_ADDRESS_SPACE"
__no_init uint8 _reserved[1932];
#pragma required=_reserved"""
ONBOARD_RESERVED_NEW = """#if defined(__SDCC)
const __code __at (SDCC_FLASH_LAST_PAGE_START) uint8 _reserved[1932];
#else
#pragma location="RESERVED_ADDRESS_SPACE"
__no_init uint8 _reserved[1932];
#pragma required=_reserved
#endif"""

ZMAIN_PINFOPAGE_OLD = """#include "ZMAC.h"

/*********************************************************************"""
ZMAIN_PINFOPAGE_NEW = """#include "ZMAC.h"

#ifndef P_INFOPAGE
#define P_INFOPAGE 0x7800
#endif

/*********************************************************************"""

MT_AF_ASSIGN_OLD = "(void)osal_memcpy(&(pMtAfDataReq->dstAddr), &dstAddr, sizeof(afAddrType_t));"
MT_AF_ASSIGN_NEW = "pMtAfDataReq->dstAddr = dstAddr;"

SAPI_EXTADDR_COPY_OLD = "      osal_memcpy(pValue, &aExtendedAddress, Z_EXTADDR_LEN);"
SAPI_EXTADDR_COPY_NEW = "      osal_memcpy(pValue, aExtendedAddress, Z_EXTADDR_LEN);"
SAPI_PARENT_EXTADDR_COPY_OLD = "      osal_memcpy(pValue, &_NIB.nwkCoordExtAddress, Z_EXTADDR_LEN);"
SAPI_PARENT_EXTADDR_COPY_NEW = "      osal_memcpy(pValue, _NIB.nwkCoordExtAddress, Z_EXTADDR_LEN);"
SAPI_EXT_PAN_COPY_OLD = "      osal_memcpy(pValue, &_NIB.extendedPANID, Z_EXTADDR_LEN);"
SAPI_EXT_PAN_COPY_NEW = "      osal_memcpy(pValue, _NIB.extendedPANID, Z_EXTADDR_LEN);"

ZCL_SAMPLELIGHT_DECL_OLD = "void zclSampleLight_UiUpdateLcd(uint8 uiCurrentState, char * line[3]);"
ZCL_SAMPLELIGHT_DECL_NEW = "void zclSampleLight_UiUpdateLcd(uint8 uiCurrentState, char * line[3]) __reentrant;"
ZCL_SAMPLELIGHT_DEF_OLD = "void zclSampleLight_UiUpdateLcd(uint8 UiState, char * line[3])"
ZCL_SAMPLELIGHT_DEF_NEW = "void zclSampleLight_UiUpdateLcd(uint8 UiState, char * line[3]) __reentrant"

ZCL_SAMPLELIGHT_DATA_OLD = """#ifdef ZCL_LEVEL_CTRL
  ,{"""
ZCL_SAMPLELIGHT_DATA_NEW = """#ifdef ZCL_LEVEL_CTRL
  {"""

HAL_MCU_BLOCK_OLD = """/* ---------------------- IAR Compiler ---------------------- */
#if (1)
#include <ioCC2530.h>
#define HAL_COMPILER_IAR
#define HAL_MCU_LITTLE_ENDIAN()   __LITTLE_ENDIAN__
#define _PRAGMA(x) _Pragma(#x)
#define HAL_ISR_FUNC_DECLARATION(f,v)   _PRAGMA(vector=v) __near_func __interrupt void f(void)
#define HAL_ISR_FUNC_PROTOTYPE(f,v)     _PRAGMA(vector=v) __near_func __interrupt void f(void)
#define HAL_ISR_FUNCTION(f,v)           HAL_ISR_FUNC_PROTOTYPE(f,v); HAL_ISR_FUNC_DECLARATION(f,v)

/* ---------------------- Keil Compiler ---------------------- */"""
HAL_MCU_BLOCK_OLD_VENDOR = """/* ---------------------- IAR Compiler ---------------------- */
#ifdef __IAR_SYSTEMS_ICC__
#include <ioCC2530.h>
#define HAL_COMPILER_IAR
#define HAL_MCU_LITTLE_ENDIAN()   __LITTLE_ENDIAN__
#define _PRAGMA(x) _Pragma(#x)
#define HAL_ISR_FUNC_DECLARATION(f,v)   _PRAGMA(vector=v) __near_func __interrupt void f(void)
#define HAL_ISR_FUNC_PROTOTYPE(f,v)     _PRAGMA(vector=v) __near_func __interrupt void f(void)
#define HAL_ISR_FUNCTION(f,v)           HAL_ISR_FUNC_PROTOTYPE(f,v); HAL_ISR_FUNC_DECLARATION(f,v)

/* ---------------------- Keil Compiler ---------------------- */"""
HAL_MCU_BLOCK_NEW = """/* ---------------------- IAR Compiler ---------------------- */
#ifdef __IAR_SYSTEMS_ICC__
#include <ioCC2530.h>
#define HAL_COMPILER_IAR
#define HAL_MCU_LITTLE_ENDIAN()   __LITTLE_ENDIAN__
#define _PRAGMA(x) _Pragma(#x)
#define HAL_ISR_FUNC_DECLARATION(f,v)   _PRAGMA(vector=v) __near_func __interrupt void f(void)
#define HAL_ISR_FUNC_PROTOTYPE(f,v)     _PRAGMA(vector=v) __near_func __interrupt void f(void)
#define HAL_ISR_FUNCTION(f,v)           HAL_ISR_FUNC_PROTOTYPE(f,v); HAL_ISR_FUNC_DECLARATION(f,v)

/* ---------------------- SDCC Compiler ---------------------- */
#elif defined __SDCC
#include <cc2530.h>
#define HAL_COMPILER_SDCC
#define HAL_MCU_LITTLE_ENDIAN()   1
#define HAL_ISR_FUNC_DECLARATION(f,v)   void f(void) __interrupt (v)
#define HAL_ISR_FUNC_PROTOTYPE(f,v)     void f(void) __interrupt (v)
#define HAL_ISR_FUNCTION(f,v)           HAL_ISR_FUNC_PROTOTYPE(f,v); HAL_ISR_FUNC_DECLARATION(f,v)
#ifndef ADCCFG
#define ADCCFG APCFG
#endif
#ifndef T2CSPCFG
#define T2CSPCFG T2EVTCFG
#endif

/* ---------------------- Keil Compiler ---------------------- */"""

HAL_TYPES_BLOCK_OLD = """/* ----------- IAR Compiler ----------- */
#ifdef __IAR_SYSTEMS_ICC__
#define  CODE   __code
#define  XDATA  __xdata
#define ASM_NOP    asm("NOP")

/* ----------- KEIL Compiler ----------- */"""
HAL_TYPES_BLOCK_NEW = """/* ----------- IAR Compiler ----------- */
#ifdef __IAR_SYSTEMS_ICC__
#define  CODE   __code
#define  XDATA  __xdata
#define ASM_NOP    asm("NOP")

/* ----------- SDCC Compiler ----------- */
#elif defined __SDCC
#define  CODE   __code
#define  XDATA  __xdata
#define ASM_NOP __asm NOP __endasm
#define __root
#define __no_init
#define __segment_begin(x) 0
#define __segment_end(x) 0

/* ----------- KEIL Compiler ----------- */"""

HAL_TYPES_BLOCK_OLD_WITH_HELPERS = """/* ----------- IAR Compiler ----------- */
#ifdef __IAR_SYSTEMS_ICC__
#define  CODE   __code
#define  XDATA  __xdata
#define HAL_ASM(instr) asm(#instr)
#define HAL_LJMP(addr) HAL_ASM(LJMP addr)
#define ASM_NOP    asm("NOP")

/* ----------- KEIL Compiler ----------- */"""
HAL_TYPES_BLOCK_NEW_WITH_HELPERS = """/* ----------- IAR Compiler ----------- */
#ifdef __IAR_SYSTEMS_ICC__
#define  CODE   __code
#define  XDATA  __xdata
#define HAL_ASM(instr) asm(#instr)
#define HAL_LJMP(addr) HAL_ASM(LJMP addr)
#define ASM_NOP    asm("NOP")

/* ----------- SDCC Compiler ----------- */
#elif defined __SDCC
#define  CODE   __code
#define  XDATA  __xdata
#define HAL_ASM(instr) __asm instr __endasm
#define HAL_LJMP(addr) HAL_ASM(ljmp addr)
#define ASM_NOP __asm NOP __endasm
#define __root
#define __no_init
#define __segment_begin(x) 0
#define __segment_end(x) 0

/* ----------- KEIL Compiler ----------- */"""

ZCL_SAMPLEAPPS_UI_OLD = "typedef void (* uiAppUpdateLcd_t)(uint8 uiCurrentState, char * line[3]);"
ZCL_SAMPLEAPPS_UI_NEW = "typedef void (* uiAppUpdateLcd_t)(uint8 uiCurrentState, char * line[3]) __reentrant;"

ONBOARD_H_OLD = "  extern __near_func void Onboard_soft_reset( void );"
ONBOARD_H_NEW = """  #ifdef __SDCC
  extern void Onboard_soft_reset( void ) __nonbanked;
  #else
  extern __near_func void Onboard_soft_reset( void );
  #endif"""
ONBOARD_INCLUDES_OLD = """#include "hal_sleep.h"
#include "osal.h"
"""
ONBOARD_INCLUDES_NEW = """#include "hal_sleep.h"
#include "osal.h"

#ifndef P_INFOPAGE
#define P_INFOPAGE 0x7800
#endif"""
ONBOARD_STACK_BLOCK_OLD = """#ifdef __IAR_SYSTEMS_ICC__
// Internal (MCU) Stack addresses
#define CSTACK_BEG ((uint8 const *)(_Pragma("segment=\\"XSTACK\\"") __segment_begin("XSTACK")))
#define CSTACK_END ((uint8 const *)(_Pragma("segment=\\"XSTACK\\"") __segment_end("XSTACK"))-1)
// Stack Initialization Value
#define STACK_INIT_VALUE  0xCD
#else
#error Check compiler compatibility.
#endif"""
ONBOARD_STACK_BLOCK_NEW = """#ifdef __IAR_SYSTEMS_ICC__
// Internal (MCU) Stack addresses
#define CSTACK_BEG ((uint8 const *)(_Pragma("segment=\\"XSTACK\\"") __segment_begin("XSTACK")))
#define CSTACK_END ((uint8 const *)(_Pragma("segment=\\"XSTACK\\"") __segment_end("XSTACK"))-1)
// Stack Initialization Value
#define STACK_INIT_VALUE  0xCD
#elif defined __SDCC
#define CSTACK_BEG ((uint8 const *)(0x0000))
#define CSTACK_END ((uint8 const *)(0x0000))
#define STACK_INIT_VALUE  0xCD
#else
#error Check compiler compatibility.
#endif"""
HAL_BOARD_CFG_INCLUDES_OLD = """#include "hal_mcu.h"
#include "hal_defs.h"
#include "hal_types.h"
"""
HAL_BOARD_CFG_INCLUDES_NEW = """#include "hal_mcu.h"
#include "hal_defs.h"
#include "hal_types.h"

#ifndef P_INFOPAGE
#define P_INFOPAGE 0x7800
#endif"""


def _replace_once(data: bytes, old: bytes, new: bytes, label: str) -> bytes:
    count = data.count(old)
    if count != 1:
        raise SystemExit(f"Expected exactly one {label} block, found {count}")
    return data.replace(old, new, 1)


def prepare_cc2530_hal_sleep(src: Path, dst: Path) -> None:
    data = src.read_bytes()
    data = _replace_once(data, HAL_SLEEP_IMPL_OLD, HAL_SLEEP_IMPL_NEW, "hal_sleep implementation")
    data = _replace_once(data, HAL_SLEEP_OPTIMIZE_OLD, HAL_SLEEP_OPTIMIZE_NEW, "hal_sleep optimize pragma")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(data)


def _replace_text_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Expected exactly one {label} block, found {count}")
    return text.replace(old, new, 1)


def _replace_text_all(text: str, old: str, new: str, label: str, *, expected_at_least: int = 1) -> str:
    count = text.count(old)
    if count < expected_at_least:
        raise SystemExit(f"Expected at least {expected_at_least} {label} block(s), found {count}")
    return text.replace(old, new)


def _read_text(src: Path) -> str:
    data = src.read_bytes().replace(b"\r\n", b"\n")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp1252")


def _prepare_text(src: Path, dst: Path, replacements: list[tuple[str, str, str]]) -> None:
    text = _read_text(src)
    for old, new, label in replacements:
        text = _replace_text_once(text, old, new, label)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text, encoding="utf-8")


def prepare_cc2530_hal_startup(src: Path, dst: Path) -> None:
    _prepare_text(
        src,
        dst,
        [
            (HAL_STARTUP_PREFIX_OLD, HAL_STARTUP_PREFIX_NEW, "hal_startup sdcc prefix"),
            (HAL_STARTUP_SUFFIX_OLD, HAL_STARTUP_SUFFIX_NEW, "hal_startup sdcc suffix"),
        ],
    )


def prepare_cc2530_osal_math(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(_read_text(src), encoding="utf-8")


def prepare_cc2530_osal_nv(src: Path, dst: Path) -> None:
    _prepare_text(
        src,
        dst,
        [
            (OSAL_NV_GLOBALS_OLD, OSAL_NV_GLOBALS_NEW, "OSAL_Nv globals prefix"),
            (OSAL_NV_BUF_OLD, OSAL_NV_BUF_NEW, "OSAL_Nv _nvBuf placement"),
        ],
    )


def prepare_cc2530_onboard(src: Path, dst: Path) -> None:
    _prepare_text(
        src,
        dst,
        [
            (ONBOARD_GLOBALS_OLD, ONBOARD_GLOBALS_NEW, "OnBoard globals prefix"),
            (ONBOARD_LOCKBITS_OLD, ONBOARD_LOCKBITS_NEW, "OnBoard lockbits"),
            (ONBOARD_NVIEEE_OLD, ONBOARD_NVIEEE_NEW, "OnBoard nv ieee"),
            (ONBOARD_RESERVED_OLD, ONBOARD_RESERVED_NEW, "OnBoard reserved page"),
        ],
    )


def prepare_cc2530_zmain(src: Path, dst: Path) -> None:
    _prepare_text(
        src,
        dst,
        [
            (ZMAIN_PINFOPAGE_OLD, ZMAIN_PINFOPAGE_NEW, "ZMain P_INFOPAGE define"),
        ],
    )


def prepare_cc2530_hal_lcd(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(src.read_bytes())


def prepare_cc2530_mt_af(src: Path, dst: Path) -> None:
    _prepare_text(
        src,
        dst,
        [
            (MT_AF_ASSIGN_OLD, MT_AF_ASSIGN_NEW, "MT_AF dstAddr assignment"),
        ],
    )


def prepare_cc2530_sapi(src: Path, dst: Path) -> None:
    _prepare_text(
        src,
        dst,
        [
            (SAPI_EXTADDR_COPY_OLD, SAPI_EXTADDR_COPY_NEW, "SAPI extended address copy"),
            (SAPI_PARENT_EXTADDR_COPY_OLD, SAPI_PARENT_EXTADDR_COPY_NEW, "SAPI parent extended address copy"),
            (SAPI_EXT_PAN_COPY_OLD, SAPI_EXT_PAN_COPY_NEW, "SAPI extended PAN copy"),
        ],
    )


def prepare_cc2530_zcl_samplelight(src: Path, dst: Path) -> None:
    _prepare_text(
        src,
        dst,
        [
            (ZCL_SAMPLELIGHT_DECL_OLD, ZCL_SAMPLELIGHT_DECL_NEW, "zcl_samplelight lcd decl"),
            (ZCL_SAMPLELIGHT_DEF_OLD, ZCL_SAMPLELIGHT_DEF_NEW, "zcl_samplelight lcd def"),
        ],
    )


def prepare_cc2530_zcl_samplelight_data(src: Path, dst: Path) -> None:
    _prepare_text(
        src,
        dst,
        [
            (ZCL_SAMPLELIGHT_DATA_OLD, ZCL_SAMPLELIGHT_DATA_NEW, "zcl_samplelight_data level ctrl entry"),
        ],
    )


def prepare_cc2530_hal_mcu_header(src: Path, dst: Path) -> None:
    text = _read_text(src)
    if HAL_MCU_BLOCK_NEW in text:
        pass
    elif HAL_MCU_BLOCK_OLD in text:
        text = _replace_text_once(text, HAL_MCU_BLOCK_OLD, HAL_MCU_BLOCK_NEW, "hal_mcu sdcc compiler block")
    else:
        text = _replace_text_once(
            text,
            HAL_MCU_BLOCK_OLD_VENDOR,
            HAL_MCU_BLOCK_NEW,
            "hal_mcu sdcc compiler block",
        )
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text, encoding="utf-8")


def prepare_cc2530_hal_types_header(src: Path, dst: Path) -> None:
    text = _read_text(src)
    if "/* ----------- SDCC Compiler ----------- */" in text and "#define  CODE   __code" in text:
        pass
    elif HAL_TYPES_BLOCK_OLD_WITH_HELPERS in text:
        text = _replace_text_once(
            text,
            HAL_TYPES_BLOCK_OLD_WITH_HELPERS,
            HAL_TYPES_BLOCK_NEW_WITH_HELPERS,
            "hal_types sdcc compiler block with helpers",
        )
    else:
        text = _replace_text_once(text, HAL_TYPES_BLOCK_OLD, HAL_TYPES_BLOCK_NEW, "hal_types sdcc compiler block")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text, encoding="utf-8")


def prepare_cc2530_hal_board_cfg_header(src: Path, dst: Path) -> None:
    text = _read_text(src)
    if HAL_BOARD_CFG_INCLUDES_NEW not in text:
        text = _replace_text_once(
            text,
            HAL_BOARD_CFG_INCLUDES_OLD,
            HAL_BOARD_CFG_INCLUDES_NEW,
            "hal_board_cfg P_INFOPAGE define",
        )
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text, encoding="utf-8")


def prepare_cc2530_zcl_sampleapps_ui_header(src: Path, dst: Path) -> None:
    _prepare_text(
        src,
        dst,
        [
            (ZCL_SAMPLEAPPS_UI_OLD, ZCL_SAMPLEAPPS_UI_NEW, "zcl_sampleapps_ui reentrant callback"),
        ],
    )


def prepare_cc2530_onboard_header(src: Path, dst: Path) -> None:
    text = _read_text(src)
    if ONBOARD_INCLUDES_NEW not in text:
        text = _replace_text_once(text, ONBOARD_INCLUDES_OLD, ONBOARD_INCLUDES_NEW, "OnBoard P_INFOPAGE define")
    if "#elif defined __SDCC" not in text:
        text = _replace_text_once(text, ONBOARD_STACK_BLOCK_OLD, ONBOARD_STACK_BLOCK_NEW, "OnBoard stack block")
    if ONBOARD_H_NEW not in text:
        text = _replace_text_once(text, ONBOARD_H_OLD, ONBOARD_H_NEW, "OnBoard soft reset decl")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text, encoding="utf-8")


def prepare_copy(src: Path, dst: Path) -> None:
    data = src.read_bytes().replace(b"\r\n", b"\n")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(data)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare patched SDCC-specific source variants.")
    parser.add_argument(
        "--mode",
        required=True,
        choices=(
            "cc2530-hal-sleep",
            "cc2530-hal-startup",
            "cc2530-osal-math",
            "cc2530-osal-nv",
            "cc2530-onboard",
            "cc2530-zmain",
            "cc2530-hal-lcd",
            "cc2530-mt-af",
            "cc2530-sapi",
            "cc2530-zcl-samplelight",
            "cc2530-zcl-samplelight-data",
            "cc2530-hal-mcu-h",
            "cc2530-hal-types-h",
            "cc2530-hal-board-cfg-h",
            "cc2530-zcl-sampleapps-ui-h",
            "cc2530-onboard-h",
            "copy",
        ),
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    if args.mode == "cc2530-hal-sleep":
        prepare_cc2530_hal_sleep(args.input, args.output)
    elif args.mode == "cc2530-hal-startup":
        prepare_cc2530_hal_startup(args.input, args.output)
    elif args.mode == "cc2530-osal-math":
        prepare_cc2530_osal_math(args.input, args.output)
    elif args.mode == "cc2530-osal-nv":
        prepare_cc2530_osal_nv(args.input, args.output)
    elif args.mode == "cc2530-onboard":
        prepare_cc2530_onboard(args.input, args.output)
    elif args.mode == "cc2530-zmain":
        prepare_cc2530_zmain(args.input, args.output)
    elif args.mode == "cc2530-hal-lcd":
        prepare_cc2530_hal_lcd(args.input, args.output)
    elif args.mode == "cc2530-mt-af":
        prepare_cc2530_mt_af(args.input, args.output)
    elif args.mode == "cc2530-sapi":
        prepare_cc2530_sapi(args.input, args.output)
    elif args.mode == "cc2530-zcl-samplelight":
        prepare_cc2530_zcl_samplelight(args.input, args.output)
    elif args.mode == "cc2530-zcl-samplelight-data":
        prepare_cc2530_zcl_samplelight_data(args.input, args.output)
    elif args.mode == "cc2530-hal-mcu-h":
        prepare_cc2530_hal_mcu_header(args.input, args.output)
    elif args.mode == "cc2530-hal-types-h":
        prepare_cc2530_hal_types_header(args.input, args.output)
    elif args.mode == "cc2530-hal-board-cfg-h":
        prepare_cc2530_hal_board_cfg_header(args.input, args.output)
    elif args.mode == "cc2530-zcl-sampleapps-ui-h":
        prepare_cc2530_zcl_sampleapps_ui_header(args.input, args.output)
    elif args.mode == "cc2530-onboard-h":
        prepare_cc2530_onboard_header(args.input, args.output)
    elif args.mode == "copy":
        prepare_copy(args.input, args.output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
