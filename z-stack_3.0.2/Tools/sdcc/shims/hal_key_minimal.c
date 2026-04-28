#include "hal_key.h"

bool Hal_KeyIntEnable = FALSE;

void HalKeyInit(void)
{
}

void HalKeyConfig(bool interruptEnable, const halKeyCBack_t cback)
{
  Hal_KeyIntEnable = interruptEnable;
  (void)cback;
}

uint8 HalKeyRead(void)
{
  return 0;
}

void HalKeyEnterSleep(void)
{
}

uint8 HalKeyExitSleep(void)
{
  return 0;
}

void HalKeyPoll(void)
{
}

bool HalKeyPressed(void)
{
  return FALSE;
}

uint8 hal_key_keys(void)
{
  return 0;
}

uint8 hal_key_int_keys(void)
{
  return 0;
}
