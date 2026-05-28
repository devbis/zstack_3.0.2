	.module cc2530_flash_reservations

	.area LOCK_BITS_ADDRESS_SPACE (CODE)
	.blkb 16

	.area IEEE_ADDRESS_SPACE (CODE)
	.blkb 8

	.area RESERVED_ADDRESS_SPACE (CODE)
	.blkb 1932
