import os
import sys
import gc
import asyncio
import json

def clear_memory():
    gc.collect()
    print("✅ 메모리 정리 완료")

def restart_program():
    os.execv(sys.executable, ['python'] + sys.argv)

async def delete_after_delay(ctx, msg=None, delay=10):
    await asyncio.sleep(delay)
    try:
        if msg:
            await msg.delete()
        if ctx and hasattr(ctx, 'message'):
            await ctx.message.delete()
    except Exception:
        pass 

async def delete_user_command(ctx):
    await asyncio.sleep(1)
    try:
        if ctx and hasattr(ctx, 'message'):
            await ctx.message.delete()
    except Exception:
        pass