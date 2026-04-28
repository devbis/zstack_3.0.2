#include "hal_led.h"

void HalLedInit(void)
{
}

uint8 HalLedSet(uint8 led, uint8 mode)
{
  (void)led;
  (void)mode;
  return 0;
}

void HalLedBlink(uint8 leds, uint8 cnt, uint8 duty, uint16 time)
{
  (void)leds;
  (void)cnt;
  (void)duty;
  (void)time;
}

void HalLedEnterSleep(void)
{
}

void HalLedExitSleep(void)
{
}

uint8 HalLedGetState(void)
{
  return 0;
}

void HalLedUpdate(void)
{
}
