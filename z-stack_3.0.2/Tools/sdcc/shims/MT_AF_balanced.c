/**************************************************************************************************
  Filename:       MT_AF_balanced.c

  Description:    Balanced-profile SDCC shim for MT AF support.

                  Keeps the common AF MT command path used by ZNP hosts
                  (register/delete/data request plus AF callbacks), but drops
                  the large-message staging and APSF helper paths that make the
                  stock MT_AF.c substantially larger.
**************************************************************************************************/

#include "MT_AF.h"

uint16 _afCallbackSub = 0;

void MT_AfExec(void)
{
}

static void MT_AfRegister(uint8 *pBuf)
{
  uint8 cmdId;
  uint8 retValue = ZMemError;
  endPointDesc_t *epDesc;

  cmdId = pBuf[MT_RPC_POS_CMD1];
  pBuf += MT_RPC_FRAME_HDR_SZ;

  epDesc = (endPointDesc_t *)osal_mem_alloc(sizeof(endPointDesc_t));
  if (epDesc)
  {
    epDesc->task_id = &MT_TaskID;
    retValue = MT_BuildEndpointDesc(pBuf, epDesc);
    if (retValue == ZSuccess)
    {
      retValue = afRegister(epDesc);
    }

    if (retValue != ZSuccess)
    {
      osal_mem_free(epDesc);
    }
  }

  MT_BuildAndSendZToolResponse(((uint8)MT_RPC_CMD_SRSP | (uint8)MT_RPC_SYS_AF), cmdId, 1, &retValue);
}

static void MT_AfDelete(uint8 *pBuf)
{
  uint8 cmdId;
  uint8 retValue;

  cmdId = pBuf[MT_RPC_POS_CMD1];
  pBuf += MT_RPC_FRAME_HDR_SZ;
  retValue = afDelete(*pBuf);

  MT_BuildAndSendZToolResponse(((uint8)MT_RPC_CMD_SRSP | (uint8)MT_RPC_SYS_AF), cmdId, 1, &retValue);
}

static void MT_AfDataRequest(uint8 *pBuf)
{
  #define MT_AF_REQ_MSG_LEN  10
  #define MT_AF_REQ_MSG_EXT  10

  endPointDesc_t *epDesc;
  afAddrType_t dstAddr;
  cId_t cId;
  uint8 transId, txOpts, radius;
  uint8 cmd0, cmd1;
  uint8 retValue = ZFailure;
  uint16 dataLen, tempLen;

  cmd0 = pBuf[MT_RPC_POS_CMD0];
  cmd1 = pBuf[MT_RPC_POS_CMD1];
  pBuf += MT_RPC_FRAME_HDR_SZ;

  if (cmd1 == MT_AF_DATA_REQUEST_EXT)
  {
    dstAddr.addrMode = (afAddrMode_t)*pBuf++;

    if (dstAddr.addrMode == afAddr64Bit)
    {
      (void)osal_memcpy(dstAddr.addr.extAddr, pBuf, Z_EXTADDR_LEN);
    }
    else
    {
      dstAddr.addr.shortAddr = osal_build_uint16(pBuf);
    }
    pBuf += Z_EXTADDR_LEN;

    dstAddr.endPoint = *pBuf++;
    dstAddr.panId = osal_build_uint16(pBuf);
    pBuf += 2;
  }
  else
  {
    dstAddr.addrMode = afAddr16Bit;
    dstAddr.addr.shortAddr = osal_build_uint16(pBuf);
    pBuf += 2;
    dstAddr.endPoint = *pBuf++;
    dstAddr.panId = 0;
  }

  epDesc = afFindEndPointDesc(*pBuf++);
  cId = osal_build_uint16(pBuf);
  pBuf += 2;
  transId = *pBuf++;
  txOpts = *pBuf++;
  radius = *pBuf++;

  if (cmd1 == MT_AF_DATA_REQUEST_EXT)
  {
    dataLen = osal_build_uint16(pBuf);
    tempLen = dataLen + MT_AF_REQ_MSG_LEN + MT_AF_REQ_MSG_EXT;
    pBuf += 2;
  }
  else
  {
    dataLen = *pBuf++;
    tempLen = dataLen + MT_AF_REQ_MSG_LEN;
  }

  if (epDesc == NULL)
  {
    retValue = afStatus_INVALID_PARAMETER;
  }
  else if (tempLen > (uint16)MT_RPC_DATA_MAX)
  {
    /* Balanced profile drops the deferred host-store path for oversized AF frames. */
    retValue = afStatus_INVALID_PARAMETER;
  }
  else
  {
    retValue = AF_DataRequest(&dstAddr, epDesc, cId, dataLen, pBuf, &transId, txOpts, radius);
  }

  if (MT_RPC_CMD_SREQ == (cmd0 & MT_RPC_CMD_TYPE_MASK))
  {
    MT_BuildAndSendZToolResponse(((uint8)MT_RPC_CMD_SRSP | (uint8)MT_RPC_SYS_AF), cmd1, 1, &retValue);
  }
}

#if defined(ZIGBEEPRO)
static void MT_AfDataRequestSrcRtg(uint8 *pBuf)
{
  uint8 cmdId, dataLen = 0;
  uint8 retValue = ZFailure;
  endPointDesc_t *epDesc;
  byte transId;
  afAddrType_t dstAddr;
  cId_t cId;
  byte txOpts, radius, srcEP, relayCnt;
  uint16 *pRelayList;
  uint8 i;

  cmdId = pBuf[MT_RPC_POS_CMD1];
  pBuf += MT_RPC_FRAME_HDR_SZ;

  osal_memset(&dstAddr, 0, sizeof(afAddrType_t));
  dstAddr.addrMode = afAddr16Bit;
  dstAddr.addr.shortAddr = osal_build_uint16(pBuf);
  pBuf += 2;
  dstAddr.endPoint = *pBuf++;

  srcEP = *pBuf++;
  epDesc = afFindEndPointDesc(srcEP);

  cId = osal_build_uint16(pBuf);
  pBuf += 2;
  transId = *pBuf++;
  txOpts = *pBuf++;
  radius = *pBuf++;
  relayCnt = *pBuf++;

  pRelayList = osal_mem_alloc(relayCnt * sizeof(uint16));
  if (pRelayList != NULL)
  {
    for (i = 0; i < relayCnt; i++)
    {
      pRelayList[i] = osal_build_uint16(pBuf);
      pBuf += 2;
    }

    dataLen = *pBuf++;
    if (epDesc == NULL)
    {
      retValue = afStatus_INVALID_PARAMETER;
    }
    else
    {
      retValue = AF_DataRequestSrcRtg(
          &dstAddr, epDesc, cId, dataLen, pBuf, &transId, txOpts, radius, relayCnt, pRelayList);
    }

    osal_mem_free(pRelayList);
  }
  else
  {
    retValue = afStatus_MEM_FAIL;
  }

  MT_BuildAndSendZToolResponse(((uint8)MT_RPC_CMD_SRSP | (uint8)MT_RPC_SYS_AF), cmdId, 1, &retValue);
}
#endif

uint8 MT_AfCommandProcessing(uint8 *pBuf)
{
  uint8 status = MT_RPC_SUCCESS;

  switch (pBuf[MT_RPC_POS_CMD1])
  {
    case MT_AF_REGISTER:
      MT_AfRegister(pBuf);
      break;

    case MT_AF_DELETE:
      MT_AfDelete(pBuf);
      break;

    case MT_AF_DATA_REQUEST:
    case MT_AF_DATA_REQUEST_EXT:
      MT_AfDataRequest(pBuf);
      break;

#if defined(ZIGBEEPRO)
    case MT_AF_DATA_REQUEST_SRCRTG:
      MT_AfDataRequestSrcRtg(pBuf);
      break;
#endif

    default:
      status = MT_RPC_ERR_COMMAND_ID;
      break;
  }

  return status;
}

void MT_AfDataConfirm(afDataConfirm_t *pMsg)
{
  uint8 retArray[3];

  retArray[0] = pMsg->hdr.status;
  retArray[1] = pMsg->endpoint;
  retArray[2] = pMsg->transID;

  MT_BuildAndSendZToolResponse(
      ((uint8)MT_RPC_CMD_AREQ | (uint8)MT_RPC_SYS_AF), MT_AF_DATA_CONFIRM, 3, retArray);
}

void MT_AfReflectError(afReflectError_t *pMsg)
{
  uint8 retArray[6];

  retArray[0] = pMsg->hdr.status;
  retArray[1] = pMsg->endpoint;
  retArray[2] = pMsg->transID;
  retArray[3] = pMsg->dstAddrMode;
  retArray[4] = LO_UINT16(pMsg->dstAddr);
  retArray[5] = HI_UINT16(pMsg->dstAddr);

  MT_BuildAndSendZToolResponse(
      ((uint8)MT_RPC_CMD_AREQ | (uint8)MT_RPC_SYS_AF), MT_AF_REFLECT_ERROR, 6, retArray);
}

void MT_AfIncomingMsg(afIncomingMSGPacket_t *pMsg)
{
  #define MT_AF_INC_MSG_LEN  20
  #define MT_AF_INC_MSG_EXT  10

  uint16 dataLen = pMsg->cmd.DataLength;
  uint16 respLen = MT_AF_INC_MSG_LEN + dataLen;
  uint8 cmd = MT_AF_INCOMING_MSG;
  uint8 *pRsp, *pTmp;

  if (pMsg->srcAddr.addrMode == afAddr64Bit)
  {
    cmd = MT_AF_INCOMING_MSG_EXT;
  }

  if (cmd == MT_AF_INCOMING_MSG_EXT)
  {
    respLen += MT_AF_INC_MSG_EXT;
  }

  if (respLen > (uint16)MT_RPC_DATA_MAX)
  {
    return;
  }

  pRsp = osal_mem_alloc(respLen);
  if (pRsp == NULL)
  {
    return;
  }
  pTmp = pRsp;

  *pTmp++ = LO_UINT16(pMsg->groupId);
  *pTmp++ = HI_UINT16(pMsg->groupId);
  *pTmp++ = LO_UINT16(pMsg->clusterId);
  *pTmp++ = HI_UINT16(pMsg->clusterId);

  if (cmd == MT_AF_INCOMING_MSG_EXT)
  {
    *pTmp++ = pMsg->srcAddr.addrMode;
    if (pMsg->srcAddr.addrMode == afAddr64Bit)
    {
      (void)osal_memcpy(pTmp, pMsg->srcAddr.addr.extAddr, Z_EXTADDR_LEN);
    }
    else
    {
      pTmp[0] = LO_UINT16(pMsg->srcAddr.addr.shortAddr);
      pTmp[1] = HI_UINT16(pMsg->srcAddr.addr.shortAddr);
    }
    pTmp += Z_EXTADDR_LEN;
    *pTmp++ = pMsg->srcAddr.endPoint;
    *pTmp++ = 0;
    *pTmp++ = 0;
    *pTmp++ = 0;
    *pTmp++ = LO_UINT16(dataLen);
    *pTmp++ = HI_UINT16(dataLen);
  }
  else
  {
    *pTmp++ = LO_UINT16(pMsg->srcAddr.addr.shortAddr);
    *pTmp++ = HI_UINT16(pMsg->srcAddr.addr.shortAddr);
    *pTmp++ = pMsg->srcAddr.endPoint;
    *pTmp++ = pMsg->endPoint;
    *pTmp++ = pMsg->wasBroadcast;
    *pTmp++ = pMsg->LinkQuality;
    *pTmp++ = pMsg->SecurityUse;
    osal_buffer_uint32(pTmp, pMsg->timestamp);
    pTmp += 4;
    *pTmp++ = pMsg->cmd.TransSeqNumber;
    *pTmp++ = dataLen;
  }

  if (cmd == MT_AF_INCOMING_MSG_EXT)
  {
    *pTmp++ = pMsg->endPoint;
    *pTmp++ = pMsg->wasBroadcast;
    *pTmp++ = pMsg->LinkQuality;
    *pTmp++ = pMsg->SecurityUse;
    osal_buffer_uint32(pTmp, pMsg->timestamp);
    pTmp += 4;
  }

  (void)osal_memcpy(pTmp, pMsg->cmd.Data, dataLen);
  pTmp += dataLen;
  *pTmp++ = LO_UINT16(pMsg->macSrcAddr);
  *pTmp = HI_UINT16(pMsg->macSrcAddr);

  MT_BuildAndSendZToolResponse(((uint8)MT_RPC_CMD_AREQ | (uint8)MT_RPC_SYS_AF), cmd, respLen, pRsp);
  (void)osal_mem_free(pRsp);
}
