#!/usr/bin/env python3
from __future__ import annotations
import io, struct, sys
from pathlib import Path
import httpx
from dotenv import load_dotenv
ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / '.env')
load_dotenv(ROOT / 'backend' / '.env', override=False)
def _wav():
    sr, sec = 16000, 0.6
    n = int(sr * sec)
    sc = n * 2
    b = io.BytesIO()
    b.write(b'RIFF' + struct.pack('<I', 36 + sc) + b'WAVEfmt ' + struct.pack('<IHHIIHH', 16, 1, 1, sr, sr * 2, 2, 16) + b'data' + struct.pack('<I', sc) + b'\x00\x00' * n)
    return b.getvalue()
def main():
    import os
    k = (os.getenv('ELEVENLABS_API_KEY') or '').strip()
    vid = (os.getenv('ELEVENLABS_VOICE_ID') or '21m00Tcm4TlvDq8ikWAM').strip()
    mid = (os.getenv('ELEVENLABS_STT_MODEL') or 'scribe_v2').strip() or 'scribe_v2'
    if not k: print('Set ELEVENLABS_API_KEY in inflect/.env'); return 1
    h = {'xi-api-key': k}; fail = False
    print('1) user …', end=' ')
    r = httpx.get('https://api.elevenlabs.io/v1/user', headers=h, timeout=30)
    print('OK' if r.status_code==200 else f'FAIL {r.status_code}'); fail |= r.status_code!=200
    print('2) tts …', end=' ')
    r = httpx.post(f'https://api.elevenlabs.io/v1/text-to-speech/{vid}', headers={**h,'Accept':'audio/mpeg','Content-Type':'application/json'}, json={'text':'Test.','model_id':'eleven_multilingual_v2'}, timeout=60)
    print('OK' if r.status_code==200 and len(r.content)>100 else f'FAIL {r.status_code}'); fail |= not (r.status_code==200 and len(r.content)>100)
    print('3) sdk …', end=' ')
    try:
        from elevenlabs.client import ElevenLabs
        ElevenLabs(api_key=k).voices.search()
        print('OK')
    except ImportError: print('SKIP')
    except Exception as e: print(f'FAIL {e}'); fail = True
    print('4) stt …', end=' ')
    r = httpx.post('https://api.elevenlabs.io/v1/speech-to-text', headers=h, files={'file':('t.wav', io.BytesIO(_wav()), 'audio/wav')}, data={'model_id': mid}, timeout=120)
    print('OK' if r.status_code==200 else f'HTTP {r.status_code}'); fail |= r.status_code in (401,403) or r.status_code>=500
    return 1 if fail else 0
if __name__=='__main__': sys.exit(main())
