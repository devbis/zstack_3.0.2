#include "ZComDef.h"
#include "zcl_ha.h"

static char hex_digit(uint8 value)
{
  value &= 0x0F;
  return (value < 10) ? (char)('0' + value) : (char)('A' + (value - 10));
}

bool zclHA_isbit(uint8 *pArray, uint8 bitIndex)
{
  uint8 bit = (uint8)(1U << (bitIndex & 0x7));
  return (pArray[bitIndex >> 3] & bit) ? TRUE : FALSE;
}

void zclHA_setbit(uint8 *pArray, uint8 bitIndex)
{
  uint8 bit = (uint8)(1U << (bitIndex & 0x7));
  pArray[bitIndex >> 3] |= bit;
}

void zclHA_clearbit(uint8 *pArray, uint8 bitIndex)
{
  uint8 bit = (uint8)(1U << (bitIndex & 0x7));
  pArray[bitIndex >> 3] &= (uint8)~bit;
}

void zclHA_uint16toa(uint16 u, char *string)
{
  string[0] = hex_digit((uint8)(u >> 12));
  string[1] = hex_digit((uint8)(u >> 8));
  string[2] = hex_digit((uint8)(u >> 4));
  string[3] = hex_digit((uint8)u);
  string[4] = '\0';
}

void zclHA_uint8toa(uint8 b, char *string)
{
  string[0] = string[1] = string[2] = '0';
  string[2] = (char)('0' + (b % 10));
  b = (uint8)(b / 10);
  if (b) {
    string[1] = (char)('0' + (b % 10));
    b = (uint8)(b / 10);
  }
  if (b) {
    string[0] = (char)('0' + (b % 10));
  }
}

void zclHA_LcdStatusLine1(uint8 kind)
{
  (void)kind;
}
