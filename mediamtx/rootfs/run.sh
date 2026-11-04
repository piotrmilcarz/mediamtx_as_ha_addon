#!/usr/bin/env bash
set -euo pipefail

readonly OPTIONS="${OPTIONS:-/data/options.json}"
readonly CONFIG="${CONFIG:-/data/mediamtx.yml}"

log() { printf '[mediamtx] %s\n' "$*"; }

log "Generating MediaMTX configuration..."

WORKDIR=$(mktemp -d)
trap 'rm -rf "${WORKDIR}"' EXIT

jq '
  def present: with_entries(select(.value != null and .value != ""));
  def camelcase:
    split("_") | .[0] + (.[1:] | map(ascii_upcase[0:1] + .[1:]) | join(""));
  def permissions($actions): $actions | map({action: ., path: ""});

  {
      logLevel: .log_level,
      logDestinations: ["stdout"],
      rtsp: .rtsp,
      rtspAddress: ":8554",
      rtspTransports: ((.rtsp_transports // "" | gsub("^\\s+|\\s+$"; ""))
        | if . == "" then "udp,multicast,tcp" else . end
        | split(",") | map(gsub("^\\s+|\\s+$"; ""))),
      rtmp: .rtmp,
      rtmpAddress: ":1935",
      hls: .hls,
      hlsAddress: ":8888",
      hlsAlwaysRemux: .hls_always_remux,
      webrtc: .webrtc,
      webrtcAddress: ":8889",
      webrtcLocalUDPAddress: ":8189",
      srt: .srt,
      srtAddress: ":8890",
      api: .api,
      apiAddress: ":9997",
      authMethod: "internal",
      authInternalUsers: (
        if .auth_enabled then [
          {user: .publish_user, pass: .publish_pass, ips: [], permissions: permissions(["publish"])},
          {
            user: (if .read_user == "" then .publish_user else .read_user end),
            pass: (if .read_user == "" then .publish_pass else .read_pass end),
            ips: [], permissions: permissions(["read", "playback"])
          }
        ] else [
          {user: "any", pass: "", ips: [], permissions: permissions(["publish", "read", "playback"])}
        ] end
        + [{user: "any", pass: "", ips: ["127.0.0.1", "::1"], permissions: permissions(["api", "metrics", "pprof"])}]
      ),
      pathDefaults: ({
        record: .record,
        recordPath: .record_path,
        recordFormat: .record_format,
        recordDeleteAfter: .record_delete_after
      } | present),
      paths: (
        if (.paths // [] | length) == 0 then {all_others: {}}
        else .paths | map({key: .name, value: (
          del(.name) | present | with_entries(.key |= camelcase)
        )}) | from_entries end
      )
    }
  | with_entries(select(.value != null))
' "${OPTIONS}" > "${WORKDIR}/generated.json"

jq -r '.custom_config // ""' "${OPTIONS}" > "${WORKDIR}/custom.yml"
if ! yq -e '[.. | select(tag == "!!map") | keys | group_by(.) | .[] | select(length > 1)] | length == 0' "${WORKDIR}/custom.yml" > /dev/null; then
    log "Custom configuration must be valid YAML without duplicate keys." >&2
    exit 1
fi
yq -o=json '.' "${WORKDIR}/custom.yml" | jq -s '
  if length > 1 then error("Custom configuration must contain a single YAML document")
  elif length == 0 or .[0] == null then {}
  elif (.[0] | type) == "object" then .[0]
  else error("Custom configuration must be a YAML mapping") end
' > "${WORKDIR}/custom.json"
jq -s '.[0] * .[1]' "${WORKDIR}/generated.json" "${WORKDIR}/custom.json" > "${WORKDIR}/merged.json"
mv "${WORKDIR}/merged.json" "${CONFIG}"

rm -rf "${WORKDIR}"
trap - EXIT

log "Configuration written to ${CONFIG}"
log "Starting MediaMTX..."

exec "${MEDIAMTX_BINARY:-/mediamtx}" "${CONFIG}"
