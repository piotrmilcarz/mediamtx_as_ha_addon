# MediaMTX Home Assistant Add-on

[MediaMTX](https://github.com/bluenviron/mediamtx) is a free, zero-dependency,
ready-to-use real-time media server and media proxy. It can publish, read, proxy,
record and play back video/audio streams.

## Supported protocols

| Protocol    | Default port                           | Direction      |
| ----------- | -------------------------------------- | -------------- |
| RTSP        | 8554 TCP + UDP                         | publish & read |
| RTMP        | 1935 TCP                               | publish & read |
| HLS         | 8888 TCP                               | read only      |
| WebRTC      | 8889 TCP (signalling) + 8189 UDP (ICE) | publish & read |
| SRT         | 8890 UDP                               | publish & read |
| Control API | 9997 TCP                               | optional       |

## Configuration options

Configure the add-on in its **Configuration** tab. Use snake_case for add-on options and camelCase inside `custom_config`, which accepts native MediaMTX configuration.

### Where settings belong

| Location                         | Settings                                                                                                               | Behavior                                                       |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| Top level                        | `log_level`, protocol toggles, `rtsp_transports`, authentication options                                               | Apply to the server, not individual cameras.                   |
| Top level                        | `record`, `record_path`, `record_format`, `record_delete_after`                                                        | Shared recording defaults. A camera can override them.         |
| Each entry in `paths`            | `name`, `source`, optional per-camera settings                                                                         | Identify the camera and override shared defaults where needed. |
| `custom_config` → `pathDefaults` | Native MediaMTX path settings such as `sourceOnDemand`, `rtspTransport`, `recordPartDuration`, `recordSegmentDuration` | Share settings not exposed as top-level add-on options.        |

`record_part_duration`, `record_segment_duration`, `source_on_demand`, and `rtsp_transport` are supported under each camera in `paths`, but not as top-level add-on options. To share them, use their camelCase names under `pathDefaults` in custom YAML. Unsupported top-level fields may be removed when Home Assistant saves the configuration.

Camera-specific settings override shared defaults. Custom YAML merges over the generated configuration last; a custom `paths` entry overrides the same camera's UI settings. Avoid defining the same setting in multiple places unless that override is intentional.

The [add-on schema](config.yaml) lists every supported UI option and its type. The [upstream configuration reference](https://github.com/bluenviron/mediamtx/blob/main/mediamtx.yml) describes native MediaMTX options. See the [shared-defaults example](#continuous-recording-with-shared-defaults) below.

### Protocols

Toggle each protocol on or off. Disabled protocols will not listen on their ports even if ports are mapped in the **Network** tab.

### Ports

Use the **Network** tab in the add-on page to remap any container port to an unused host port. For example, set the `RTSP (TCP)` host port to `8556` to expose the container's RTSP listener on host port `8556`. Check for conflicts with existing services such as go2rtc.

Host-port mappings make listeners reachable outside the container, normally from the LAN. Recording from a remote source to SMB needs no published RTSP port. Clear unused mappings; this does not prevent outgoing connections to sources or storage, nor does it isolate the add-on from the internal container network.

### Authentication

When **Enable authentication** is on, clients must supply credentials:

- **Publisher username/password** — required to push a stream (e.g. from a camera or OBS).
- **Reader username/password** — required to pull/watch a stream. Leave blank to reuse the publisher credentials for readers.

These credentials protect clients connecting to MediaMTX, not its connection to a camera or go2rtc. If a source requires authentication, include its credentials in the `source` URL and percent-encode special characters in each credential. Source authentication does not protect MediaMTX's own output; enable reader authentication if you expose it to other clients.

### Recording

Top-level `record` is a shared default, not a master switch. With `record: true`, cameras record unless they explicitly set `record: false`. With `record: false`, a camera can still opt in with `record: true`. Stop the add-on to halt all recording regardless of overrides.

For continuous recording from a URL source, use `source_on_demand: false` per camera or `sourceOnDemand: false` in shared defaults. Setting it to `true` connects only when a reader requests the stream; recording alone does not activate an on-demand source.

Files are written to `record_path`. The add-on maps Home Assistant's `/media` volume with write access. Its default `/media/recordings/` uses Home Assistant's local storage. Include `%path` in shared templates to separate cameras and `%z` to distinguish timezone offsets during daylight saving time changes, for example `%Y-%m-%d/%Y-%m-%d_%H-%M-%S.%f%z`. The date directory groups recordings by day. A filename such as `2026-11-03_15-30-00.123456-0700.mp4` keeps the timezone offset attached to the timestamp. MediaMTX adds the extension automatically. New installations use `/media/recordings/%path/%Y-%m-%d/%Y-%m-%d_%H-%M-%S.%f%z`. Existing installations keep their saved `record_path`; update it manually to adopt this layout. Changing the template affects new recordings and does not move existing files.

Recording folders and filenames use your Home Assistant timezone, including daylight saving changes. `%z` adds the UTC offset, such as `-0800` or `+0100`; `Z` means UTC. Existing files keep their names.

#### Recording durations and retention

| Per-camera add-on option  | Native MediaMTX name    | Meaning                                                                                                                                         |
| ------------------------- | ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `record_part_duration`    | `recordPartDuration`    | Duration of internal fMP4 parts within each file, not separate files. For MPEG-TS, the disk-flush interval. `1s` is a practical starting point. |
| `record_segment_duration` | `recordSegmentDuration` | Minimum duration of each recording file. Keyframe boundaries can make files longer. `5m` gives manageable clips without many tiny files.        |
| `record_delete_after`     | `recordDeleteAfter`     | Age-based segment deletion. For example, `7d` keeps roughly seven days; `0s` disables deletion. It is not a disk-space limit.                   |

Smaller parts reduce buffered video at risk if recording crashes, but do not guarantee durable writes on the NAS. Neither duration setting changes video quality or enables transcoding. A nonzero retention duration must be at least the segment duration. Check overrides if MediaMTX reports that `recordDeleteAfter` is lower than `recordSegmentDuration`.

#### SMB storage on Home Assistant OS

Configure network storage under **Settings → System → Storage** with **Usage: Media**. This exposes the named mount at `/media/<storage-name>`. **Usage: Share** instead mounts it under `/share/<storage-name>`, which this add-on does not map. The directory path on the NAS is separate from these Home Assistant paths. See [Home Assistant's network storage documentation](https://www.home-assistant.io/common-tasks/os/#network-storage).

Use the verified Media mount in the recording template, for example `/media/<storage-name>/recordings/%path/%Y-%m-%d/%Y-%m-%d_%H-%M-%S.%f%z`. A directory existing or appearing in Home Assistant's Media browser does not prove it is network-backed. Verify the mount and confirm test files exist on the NAS itself before leaving recording enabled.

This add-on does not check whether network storage is mounted or stop recording when a mount disappears. Missing mounts can cause failed recordings or local writes. Do not enable unattended recording if local fallback writes could exhaust Home Assistant's disk.

### Stream paths

The **Stream paths** list lets you define named paths with individual settings:

| Field              | Description                                                                                                      |
| ------------------ | ---------------------------------------------------------------------------------------------------------------- |
| `name`             | Path identifier, e.g. `camera1`. Regular expressions supported with `~` prefix.                                  |
| `source`           | Pull stream from a URL, e.g. `rtsp://192.168.1.10/stream`. Leave empty to let a publisher push.                  |
| `source_on_demand` | Connect only when a reader requests the stream. Use `false` for continuous recording.                            |
| `rtsp_transport`   | Transport for pulling an RTSP source. Use `tcp` to request TCP; this differs from server-side `rtsp_transports`. |
| `record`           | Override the shared recording default for this path.                                                             |

All per-path options declared in the add-on schema are supported, including recording settings, RTSP settings, limits, and command hooks. Omitted or empty optional fields inherit the effective shared `pathDefaults`, then MediaMTX's built-in defaults for settings not supplied there. Explicit `false` and `0` values are preserved. The UI uses snake_case option names; custom YAML uses MediaMTX's camelCase names.

Leave the list empty to accept publishers on any path name (default behaviour).

### Custom configuration (advanced)

The **Custom configuration** field accepts a single YAML mapping that is recursively merged over the generated settings. Use it to set any MediaMTX option not exposed by the UI, such as ICE/STUN servers or multicast ranges. Custom values take precedence. Empty or null documents add no overrides. Nested mappings merge, while arrays and scalar values replace the generated values. Invalid YAML, duplicate keys, and multiple YAML documents prevent startup.

The add-on writes the merged configuration as JSON, which MediaMTX accepts as YAML, to `/data/mediamtx.yml`. It regenerates this file on each start. Make persistent changes in the add-on Configuration tab.

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
    sourceOnDemand: true
    record: false
```

Custom `paths` entries merge with entries from **Stream paths** by path name. If the UI list is empty, the generated `all_others: {}` fallback remains unless explicitly overridden. To avoid that fallback, add at least one named entry in the UI list.

## Usage examples

### Continuous recording with shared defaults

This is a partial add-on configuration to merge into your existing settings. Replace the storage name and source URLs before enabling recording. Verify the Media mount first and size retention for the NAS's available space.

```yaml
record: true
record_path: "/media/<storage-name>/recordings/%path/%Y-%m-%d/%Y-%m-%d_%H-%M-%S.%f%z"
record_format: fmp4
record_delete_after: 7d
paths:
  - name: camera1
    source: "rtsp://<username>:<password>@<source-host>:8554/camera1"
  - name: camera2
    source: "rtsp://<username>:<password>@<source-host>:8554/camera2"
custom_config: |
  moq: false
  pathDefaults:
    sourceOnDemand: false
    rtspTransport: tcp
    recordPartDuration: 1s
    recordSegmentDuration: 5m
```

Both cameras inherit recording, storage, retention, transport, and duration settings. Add a per-camera override only when needed, such as `record: false` or `record_delete_after: 3d`. Remove old per-camera values such as `record_segment_duration: 10s` or `source_on_demand: true` if you want the shared defaults to apply.

The example disables MoQ, which is enabled by default in MediaMTX v1.21.3. Top-level `rtsp_transports` controls readers and publishers connecting to MediaMTX; `rtspTransport` under `pathDefaults` controls MediaMTX pulling its sources. Disabling server listeners or clearing host-port mappings does not prevent source pulls or recording.

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

## Local verification

Requires Python 3, Bash, jq, and Mike Farah's yq v4. No cameras or NAS are needed.

```sh
python3 -m unittest discover -s tests -v
bash -n mediamtx/rootfs/run.sh
shellcheck mediamtx/rootfs/run.sh
docker build -t mediamtx-addon:local mediamtx
TEST_ADDON_IMAGE=mediamtx-addon:local python3 -m unittest discover -s tests -v
```

Run these commands from the repository root. The optional Docker checks use no network and publish no ports.

## Support & documentation

- MediaMTX documentation: <https://github.com/bluenviron/mediamtx>
- Full configuration reference, current upstream: <https://github.com/bluenviron/mediamtx/blob/main/mediamtx.yml>
- Version-specific reference used to verify these examples, MediaMTX v1.21.3: <https://github.com/bluenviron/mediamtx/blob/v1.21.3/mediamtx.yml>

The Dockerfile uses the floating upstream `:1` image tag. Check the MediaMTX version in startup logs and use the matching upstream reference if behavior differs.
