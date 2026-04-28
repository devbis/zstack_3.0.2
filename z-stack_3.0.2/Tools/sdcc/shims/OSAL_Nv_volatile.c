/**************************************************************************************************
  Filename:       OSAL_Nv_volatile.c

  Description:    Lean-profile SDCC shim for OSAL NV.

                  This keeps the ZNP build linkable without the flash-backed
                  CC2530 NV implementation. Data lives only in RAM for the
                  current boot and is initialized to erased-flash semantics
                  (0xFF) when no default buffer is provided.
**************************************************************************************************/

#include "comdef.h"
#include "OSAL.h"
#include "OSAL_Nv.h"

typedef struct osal_nv_ram_item_t
{
  struct osal_nv_ram_item_t XDATA *next;
  uint16 id;
  uint16 len;
  uint8 value[1];
} osal_nv_ram_item_t;

static osal_nv_ram_item_t XDATA *nv_items = NULL;

static osal_nv_ram_item_t XDATA *osal_nv_find_item(uint16 id)
{
  osal_nv_ram_item_t XDATA *item = nv_items;

  while (item != NULL)
  {
    if (item->id == id)
    {
      return item;
    }
    item = item->next;
  }

  return NULL;
}

void osal_nv_init(void *p)
{
  (void)p;
}

uint8 osal_nv_item_init(uint16 id, uint16 len, void *buf)
{
  osal_nv_ram_item_t XDATA *item;
  uint16 alloc_len;

  item = osal_nv_find_item(id);
  if (item != NULL)
  {
    return SUCCESS;
  }

  alloc_len = sizeof(osal_nv_ram_item_t) + len;
  item = (osal_nv_ram_item_t XDATA *)osal_mem_alloc(alloc_len);
  if (item == NULL)
  {
    return NV_OPER_FAILED;
  }

  item->next = nv_items;
  item->id = id;
  item->len = len;
  nv_items = item;

  if ((buf != NULL) && (len != 0))
  {
    osal_memcpy(item->value, buf, len);
  }
  else if (len != 0)
  {
    osal_memset(item->value, 0xFF, len);
  }

  return NV_ITEM_UNINIT;
}

uint16 osal_nv_item_len(uint16 id)
{
  osal_nv_ram_item_t XDATA *item = osal_nv_find_item(id);
  return (item == NULL) ? 0 : item->len;
}

uint8 osal_nv_write(uint16 id, uint16 ndx, uint16 len, void *buf)
{
  osal_nv_ram_item_t XDATA *item = osal_nv_find_item(id);

  if (item == NULL)
  {
    return NV_ITEM_UNINIT;
  }

  if (((uint32)ndx + (uint32)len) > item->len)
  {
    return NV_OPER_FAILED;
  }

  if (len != 0)
  {
    osal_memcpy(item->value + ndx, buf, len);
  }

  return SUCCESS;
}

uint8 osal_nv_read(uint16 id, uint16 ndx, uint16 len, void *buf)
{
  osal_nv_ram_item_t XDATA *item = osal_nv_find_item(id);

  if (item == NULL)
  {
    return NV_OPER_FAILED;
  }

  if (((uint32)ndx + (uint32)len) > item->len)
  {
    return NV_OPER_FAILED;
  }

  if (len != 0)
  {
    osal_memcpy(buf, item->value + ndx, len);
  }

  return SUCCESS;
}

uint8 osal_nv_delete(uint16 id, uint16 len)
{
  osal_nv_ram_item_t XDATA *item = nv_items;
  osal_nv_ram_item_t XDATA *prev = NULL;

  while (item != NULL)
  {
    if (item->id == id)
    {
      if (item->len != len)
      {
        return NV_BAD_ITEM_LEN;
      }

      if (prev == NULL)
      {
        nv_items = item->next;
      }
      else
      {
        prev->next = item->next;
      }

      osal_mem_free(item);
      return SUCCESS;
    }

    prev = item;
    item = item->next;
  }

  return NV_ITEM_UNINIT;
}
