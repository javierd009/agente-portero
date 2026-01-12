# Voice Audio Cutouts - Diagnosis and Fix

> **Nota**: Para la guia completa de integracion, ver `docs/OPENAI_REALTIME_FREEPBX_INTEGRATION.md`

## Problem

- Calls connect, but audio becomes choppy or stops; the agent stops responding.
- Logs show the playback buffer runs out: `queue=0`, `silence=...`, and
  `Playback paused after ... (buffer empty)` while input audio continues.

## Root Cause

- Audio from Asterisk continues, but OpenAI output is not delivered
  continuously.
- Background noise keeps server VAD open (no end-of-speech), so the
  model does not close the turn and stop to respond.
- Jitter in OpenAI output can cause buffer underruns and silence
  insertion.

## Fix Applied in Code

- Noise gate replaces low-level noise with silence (helps VAD end turns).
- VAD parameters are configurable for tuning.
- Playback prebuffer is configurable to smooth jitter.
- Output queue size is configurable to avoid dropped audio on long responses.

Files updated:

- `services/voice-service/config.py`
- `services/voice-service/call_session.py`
- `services/voice-service/.env.example`
- `services/voice-service/README.md`

## Recommended Configuration (FreePBX Local)

- Run voice-service on the same FreePBX host.
- Use `network_mode: host` OR map `9089:8089` if not using host network.
- Dialplan must point AudioSocket to the host port used by the service.

Example `docker-compose.yml` (host network):

```yaml
version: '3.8'
services:
  voice-service:
    build: .
    container_name: voice-service
    network_mode: host
    environment:
      - OPENAI_API_KEY=sk-...
      - DEBUG=false
      - NOISE_GATE_THRESHOLD=200
      - PLAYBACK_PREBUFFER_FRAMES=10
      - OUTPUT_AUDIO_QUEUE_MAXSIZE=1000
      - VAD_THRESHOLD=0.6
      - VAD_SILENCE_DURATION_MS=800
```

Dialplan (AudioSocket):

```ini
exten => 1010,1,Answer()
 same => n,AudioSocket(${UUID},127.0.0.1:8089)
```

If you need port 9089:

- Set `AUDIO_BRIDGE_PORT=9089`
- Update dialplan to `127.0.0.1:9089`

Health check:

- `http://127.0.0.1:8091/health`

## Validation Checklist

- AudioSocket connects: `AudioSocket connection from channel ...`
- First audio chunks: `Audio chunk #1: 320 bytes`
- OpenAI output present: `From OpenAI: ... bytes`
- Playback stable: queue grows, silence count does not climb

## Tuning Notes

- If the agent stops responding, raise `NOISE_GATE_THRESHOLD` or
  `VAD_THRESHOLD`.
- If speech is delayed, lower `PLAYBACK_PREBUFFER_FRAMES` or
  `VAD_SILENCE_DURATION_MS`.
