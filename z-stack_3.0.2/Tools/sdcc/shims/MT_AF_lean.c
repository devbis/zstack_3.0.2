/**************************************************************************************************
  Filename:       MT_AF_lean.c

  Description:    Lean-profile SDCC shim for MT AF support.

                  The lean ZNP profile already disables MT AF command handling.
                  This shim also strips the asynchronous AF callback queueing and
                  serialization machinery, leaving only link-compatible no-op
                  entry points for the stack and ZNP event loop.
**************************************************************************************************/

#include "MT_AF.h"

uint16 _afCallbackSub = 0;

void MT_AfExec(void)
{
}

uint8 MT_AfCommandProcessing(uint8 *pBuf)
{
  (void)pBuf;
  return MT_RPC_ERR_COMMAND_ID;
}

void MT_AfIncomingMsg(afIncomingMSGPacket_t *pMsg)
{
  (void)pMsg;
}

void MT_AfDataConfirm(afDataConfirm_t *pMsg)
{
  (void)pMsg;
}

void MT_AfReflectError(afReflectError_t *pMsg)
{
  (void)pMsg;
}
