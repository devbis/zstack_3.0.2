#include "hal_types.h"

__near_func uint32 osalMcuDivide31By16To16( uint32 dividend, uint16 divisor )
{
  uint16 quotient = (uint16)( dividend / divisor );
  uint16 remainder = (uint16)( dividend % divisor );

  return ( ( (uint32)quotient << 16 ) | remainder );
}
