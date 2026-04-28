	.module cc2530_hal_sleep_set_mode

	.globl _halSleepPconValue
	.globl _halSetSleepMode

PCON	.equ	0x87
EA_BIT	.equ	0xAF

	.area SLEEP_CODE (CODE)
	.bndry 4

_halSetSleepMode:
	mov	PCON,_halSleepPconValue
	clr	EA_BIT
	ret
