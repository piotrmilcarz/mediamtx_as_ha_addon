# MediaMTX Home Assistant Add-on

[MediaMTX](https://github.com/bluenviron/mediamtx) is a free, zero-dependency,
ready-to-use real-time media server and media proxy. It can publish, read, proxy,
record and play back video/audio streams.

## Supported protocols

| Protocol | Default port | Direction |
|----------|-------------|-----------|
| RTSP | 8554 TCP + UDP | publish & read |
| RTMP | 1935 TCP | publish & read |
| HLS | 8888 TCP | read only |
| WebRTC | 8889 TCP (signalling) + 8189 UDP (ICE) | publish & read |
| SRT | 8890 UDP | publish & read |
| Control API | 9997 TCP | optional |

## Configuration options

All options are available in the **Configuration** tab of the add-on.

### Protocols

Toggle each protocol on or off. Disabled protocols will not listen on their ports even if ports are mapped in the **Network** tab.

### Ports

Use the **Network** tab in the add-on page to remap any container port to a different host port. For example, to expose RTSP on host port 8555 instead of 8554, set the `RTSP (TCP)` host port to `8555`.

### Authentication

When **Enable authentication** is on, clients must supply credentials:

- **Publisher username/password** — required to push a stream (e.g. from a camera or OBS).
- **Reader username/password** — required to pull/watch a stream. Leave blank to reuse the publisher credentials for readers.

### Recording

Enable **Record streams** to save all streams to disk. Files are written to the path template configured in **Recording path template**. The default saves to `/media/recordings/` which maps to the Home Assistant `/media` volume.

Set **Auto-delete recordings after** to a duration (e.g. `7d`, `24h`) to automatically purge old segments. `0s` keeps recordings forever.

### Stream paths

The **Stream paths** list lets you define named paths with individual settings:

| Field | Description |
|-------|-------------|
| `name` | Path identifier, e.g. `camera1`. Regular expressions supported with `~` prefix. |
| `source` | Pull stream from a URL, e.g. `rtsp://192.168.1.10/stream`. Leave empty to let a publisher push. |
| `source_on_demand` | Only connect to the source when a viewer requests it. |
| `record` | Override the global recording toggle for this path. |

Leave the list empty to accept publishers on any path name (default behaviour).

### Custom configuration (advanced)

The **Custom configuration** field accepts raw YAML that is appended to the generated config file. Use it to set any MediaMTX option not exposed by the UI (e.g. ICE/STUN servers, multicast ranges, per-path hooks). Values here override any previously generated setting.

Example — add a STUN server for WebRTC behind NAT:

```yaml
webrtcICEServers2:
  - url: stun:stun.l.google.com:19302
```

Example — configure a specific camera path with on-demand pulling:

```yaml
paths:
  garden_cam:
    source: rtsp://admin:pass@192.168.1.20/h264/ch1/main/av_stream
    source_on_d_emand: true
    record: true
```

> **Note:** if you define `paths:` in the custom configuration field, remove all entries from the **Stream paths** list above to avoid duplicate keys.

## Usage examples

### Receive a stream from OBS / FFmpeg

In OBS or FFmpeg, publish to:
```
rtmp://<ha-ip>:1935/live
```
Then watch it at:
```
rtsp://<ha-ip>:8554/live
http://<ha-ip>:8888/live
```

### Pull from an IP camera (RTSP re-stream)

Add a path entry:
- **name**: `cam1`
- **source**: `rtsp://admin:password@192.168.1.50:554/stream1`
- **source on demand**: `off`

The camera stream is then available on all enabled protocols, e.g.:
```
rtsp://<ha-ip>:8554/cam1
http://<ha-ip>:8888/cam1
```

## Support & documentation

- MediaMTX documentation: <https://github.com/bluenviron/mediamtx>
- Full configuration reference: <https://github.com/bluenviron/mediamtx/blob/main/mediamtx.yml>
