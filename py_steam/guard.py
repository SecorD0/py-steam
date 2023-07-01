import base64
import struct
import time
from typing import Optional

from py_steam.crypto import hmac_sha1


def generate_one_time_code(shared_secret: str, timestamp: Optional[int] = None) -> str:
    if not timestamp:
        timestamp = time.time()

    hmac = hmac_sha1(base64.b64decode(shared_secret), struct.pack('>Q', int(timestamp) // 30))
    start = ord(hmac[19:20]) & 0xF
    codeint = struct.unpack('>I', hmac[start:start + 4])[0] & 0x7fffffff

    charset = '23456789BCDFGHJKMNPQRTVWXY'
    code = ''
    for _ in range(5):
        codeint, i = divmod(codeint, len(charset))
        code += charset[i]

    return code
