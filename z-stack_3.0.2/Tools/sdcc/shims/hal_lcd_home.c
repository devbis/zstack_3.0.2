#include "hal_lcd.h"

void HalLcdInit(void)
{
}

void HalLcdWriteString(char *str, uint8 option)
{
  (void)str;
  (void)option;
}

void HalLcdWriteValue(uint32 value, const uint8 radix, uint8 option)
{
  (void)value;
  (void)radix;
  (void)option;
}

void HalLcdWriteScreen(char *line1, char *line2)
{
  (void)line1;
  (void)line2;
}

void HalLcdWriteStringValue(char *title, uint16 value, uint8 format, uint8 line)
{
  (void)title;
  (void)value;
  (void)format;
  (void)line;
}

void HalLcdWriteStringValueValue(
  char *title,
  uint16 value1,
  uint8 format1,
  uint16 value2,
  uint8 format2,
  uint8 line
)
{
  (void)title;
  (void)value1;
  (void)format1;
  (void)value2;
  (void)format2;
  (void)line;
}

void HalLcdDisplayPercentBar(char *title, uint8 value)
{
  (void)title;
  (void)value;
}

void HalLcd_HW_Clear(void)
{
}
