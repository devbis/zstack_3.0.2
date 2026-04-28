#include "ZComDef.h"
#include "ZDApp.h"
#include "bdb_interface.h"
#include "hal_key.h"
#include "hal_led.h"
#include "zcl_sampleapps_ui.h"

/*
 * SDCC size-focused replacement for the sample UI stack.
 * This keeps the SampleLight app linkable while dropping the LCD/menu layer.
 */

void UI_Init(uint8 app_task_id_value,
             uint16 lcd_auto_update_event_value,
             uint16 key_auto_repeat_event_value,
             uint16 *ui_IdentifyTimeAttribute_value,
             char *app_title_value,
             uiAppUpdateLcd_t uiAppUpdateLcd,
             const uiState_t uiAppStatesMain[])
{
  (void)app_task_id_value;
  (void)lcd_auto_update_event_value;
  (void)key_auto_repeat_event_value;
  (void)ui_IdentifyTimeAttribute_value;
  (void)app_title_value;
  (void)uiAppUpdateLcd;
  (void)uiAppStatesMain;
}

void UI_UpdateComissioningStatus(bdbCommissioningModeMsg_t *bdbCommissioningModeMsg)
{
  (void)bdbCommissioningModeMsg;
}

void UI_UpdateLcd(void)
{
}

void UI_MainStateMachine(uint16 keys)
{
  (void)keys;
}

void UI_ActionBackFromAppMenu(uint16 keys)
{
  (void)keys;
}

void UI_DeviceStateUpdated(devStates_t NwkState)
{
  (void)NwkState;
}
