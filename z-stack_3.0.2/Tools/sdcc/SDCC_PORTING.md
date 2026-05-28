# SDCC Porting Guide for External IAR Z-Stack Projects

This document describes project-side `.c` / `.h` changes that may be needed
after importing an IAR Z-Stack project for SDCC.

The importer should not hard-code application-specific function names or
application-specific semantics. If a source edit is required and cannot be
derived from a generic rule, leave the project failing with a clear compiler
error and patch the project manually. When an imported tool modifies a real
project `.c` or `.h` file in place, it must save the original file next to it as
`file.ext.bak` before writing the modified file.

Generated service files such as `CMakeLists.txt` and `.sdcc-import/*` may be
overwritten without backups.

## What Can Be Patched Automatically

Only syntax-level or ABI-level patterns are candidates for automatic source
rewrites. A patch is acceptable only when the replacement does not depend on the
meaning of a specific application function.

Safe classes:

- IAR storage/calling keywords that have direct SDCC equivalents or harmless
  compatibility definitions.
- IAR pragmas that can be disabled under `__SDCC`.
- Function pointer typedefs that SDCC explicitly reports as requiring
  `__reentrant`.
- Struct/union zero-initializers that SDCC rejects under the selected ABI, when
  the replacement is a plain zero-fill of the same object.

Unsafe classes:

- Replacing one application helper function with another helper function.
- Adding missing peripheral helper implementations inferred from local naming.
- Changing timer/PWM/register logic based on function names.
- Removing application features to fit flash/RAM.
- Changing callback signatures without also updating declarations, definitions,
  and assignments consistently.

## Error Pattern: Function Pointer Must Be Reentrant

Compiler diagnostic regex:

```regex
Functions called via pointers must be 'reentrant'
```

Typical cause:

SDCC cannot pass that many argument bytes through a non-reentrant function
pointer call under the selected MCS51/IAR ABI.

Detection regex for candidate typedefs:

```regex
typedef\s+([A-Za-z_][A-Za-z0-9_\s\*]+?)\s*\(\s*\*\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)\s*\(([^;]*,[^;]*,[^;]*)\s*\)\s*;
```

Generic replacement shape:

```c
typedef RET (*name)(ARGS) __reentrant;
```

Detection regex for candidate extern function-pointer variables:

```regex
extern\s+([A-Za-z_][A-Za-z0-9_\s\*]+?)\s*\(\s*\*\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)\s*\(([^;]*,[^;]*,[^;]*)\s*\)\s*;
```

Generic replacement shape:

```c
extern RET (*name)(ARGS) __reentrant;
```

Manual check:

Every assigned function implementation must be compatible with the reentrant
pointer type. If SDCC reports a type mismatch after changing the pointer type,
add `__reentrant` to the assigned function declaration and definition as well.

Do not blindly mark every function pointer reentrant. Patch only pointers that
are involved in SDCC diagnostics or that are known public callback ABI points.

## Error Pattern: Aggregate Parameter Larger Than 1 Byte

Compiler diagnostic regex:

```regex
Unimplemented aggregate parameter larger than 1 byte for IAR calling convention
```

Typical cause:

A struct or union is passed by value while compiling with the SDCC IAR ABI.

Candidate function declaration regex:

```regex
(\b(?:static\s+)?[A-Za-z_][A-Za-z0-9_\s\*]+?\s+[A-Za-z_][A-Za-z0-9_]*\s*\([^)]*?)([A-Za-z_][A-Za-z0-9_]*_t)\s+([A-Za-z_][A-Za-z0-9_]*)([^)]*\))
```

Generic manual rewrite:

```c
/* Before */
RET fn(..., SomeStruct_t value, ...);

/* After */
RET fn(..., SomeStruct_t *value, ...);
```

Call-site rewrite shape:

```c
fn(..., &value, ...);
```

Use-site rewrite shape inside the function:

```c
/* Before */
value.field

/* After */
value->field
```

Automatic replacement is not guaranteed safe because the same typedef naming
pattern can represent scalar aliases. Treat this as a guided manual patch.

## Error Pattern: Struct Zero Initializer Rejected

Compiler diagnostic regex:

```regex
error\s+47:\s+indirections to different types assignment|error\s+35:\s+'&'\s+illegal operand,\s+address of literal
```

Candidate source regex:

```regex
\b([A-Za-z_][A-Za-z0-9_]*_t)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{\s*0\s*\}\s*;
```

Generic replacement shape:

```c
TYPE variable;
osal_memset(&variable, 0, sizeof(variable));
```

Prerequisites:

- `osal_memset` is visible in the current translation unit.
- The initializer is exactly zero initialization.
- The object is an automatic local object, not static storage.

If `osal_memset` is not available, use the project's existing zero-fill helper
or add the required include. Do not use this rewrite for non-zero aggregate
initializers.

## Error Pattern: Too Many Parameters

Compiler diagnostic regex:

```regex
error\s+101:\s+too many parameters
```

Typical causes:

- A function is called before the correct prototype is visible.
- A local helper declaration has fewer parameters than the call site.
- A project contains a typo and calls a similarly named helper with the wrong
  signature.
- A macro from IAR configuration expanded differently under SDCC.

Useful detection regex:

```regex
\b([A-Za-z_][A-Za-z0-9_]*)\s*\((?:[^()]|\([^()]*\))*?,(?:[^()]|\([^()]*\))*?,(?:[^()]|\([^()]*\))*?\)
```

No generic replacement is safe.

Required manual process:

1. Find the visible prototype for the reported function.
2. Find the intended implementation or macro in the IAR project.
3. If the prototype is missing, add the correct prototype.
4. If the function is missing, port or implement it manually.
5. If the call is semantically wrong, change the call manually.

Do not infer fixes from function names such as timer/channel/helper naming.

## Error Pattern: Undefined CC2530 Register Alias

Compiler diagnostic regex:

```regex
Undefined identifier\s+'(P_INFOPAGE|X_[A-Za-z0-9_]+|XX_[A-Za-z0-9_]+|SRC[A-Za-z0-9_]+|PAN_ID[01]|SHORT_ADDR[01]|EXT_ADDR0)'
```

Preferred fix:

Add the alias to the generated SDCC configuration header or SDK header overlay,
not to application source files.

Replacement examples:

```c
#ifndef XREG
#define XREG(addr) (*((volatile unsigned char __xdata *)(addr)))
#endif
```

```c
#ifndef P_INFOPAGE
#define P_INFOPAGE 0x7800
#endif
```

This class is SDK/platform compatibility, not an external project patch.

## Error Pattern: IAR Pragmas Or Keywords

Detection regex:

```regex
#pragma\s+(location|required|segment|vector|language|optimize)\b|__near_func\b|__root\b|__no_init\b|__interrupt\b
```

Preferred fix:

Use SDK overlays or generated compatibility headers. For project files, only
apply direct mechanical rewrites when the construct has no semantic placement
effect.

Examples:

```c
#if !defined(__SDCC)
#pragma optimize=none
#endif
```

```c
#if defined(__SDCC)
#define __root
#define __no_init
#endif
```

Do not mechanically replace `#pragma location` for real flash/RAM placement in
application code. Placement must be expressed with an SDCC `__at` declaration or
linker layout decision and reviewed manually.

## Error Pattern: Inline Assembly

Detection regex:

```regex
\basm\s*\(|__asm\b|#pragma\s+asm\b
```

No universal replacement is safe.

Manual rewrite shape for simple single-instruction cases:

```c
/* IAR-like */
asm("NOP");

/* SDCC */
__asm
  nop
__endasm;
```

Multi-instruction blocks, labels, jumps, register clobbers, and interrupt
entries must be ported manually and verified in generated assembly.

## Error Pattern: Pointer Arithmetic ICE Around Fake Segment Symbols

Compiler diagnostic regex:

```regex
FATAL Compiler Internal Error.*opPutgot offset > aop->size
```

Common trigger:

Code performs pointer arithmetic using compatibility definitions for IAR segment
boundaries, for example `__segment_begin()` / `__segment_end()` replacements.

No generic project replacement is safe.

Recommended manual approach:

- Keep the IAR implementation under `#if !defined(__SDCC)`.
- Add an SDCC implementation that uses real linker symbols if available.
- If the function is diagnostic-only, return a conservative stub value under
  `__SDCC` and document the loss of diagnostic precision.

## Backup Policy For In-Place Project Patches

Before modifying a real project file:

1. Check if `file.ext.bak` already exists.
2. If not, copy `file.ext` to `file.ext.bak`.
3. Apply the patch to `file.ext`.
4. Never overwrite the backup.

Regex-driven tooling must report every changed file and every rule applied.

## Recommended Importer Behavior

The importer should:

- Generate service files unconditionally.
- Never silently edit external `.c` / `.h` files.
- Provide an optional `--apply-porting-patches` mode only for rules documented
  here.
- Save `.bak` before the first edit to any external `.c` / `.h`.
- Stop at the first unsupported compiler diagnostic and point to this document.

