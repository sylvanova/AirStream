"""Pure functions for the desktop now-playing button + label strings.

Single source of truth for the format table in the design spec
(docs/superpowers/specs/2026-04-28-now-playing-song-design.md).

State values mirror AudioPlayer.state_changed: "playing", "paused",
"stopped", "error", "buffering".
"""

from typing import Optional, Tuple

EM_DASH = "—"  # "—"


def _is_active(state: str) -> bool:
    """True for states where audio is meant to be coming out of the speakers."""
    return state in ("playing", "buffering")


def _station_name(station: Optional[dict]) -> str:
    if not station:
        return ""
    return station.get("name", "") or ""


def button_strings(
    state: str, station: Optional[dict], song: str
) -> Tuple[str, str]:
    """Return (visible_text, accessible_name) for the play/pause button."""
    name = _station_name(station)
    song = (song or "").strip()

    if state == "error":
        return "Play", "Play"

    if state == "stopped" or not name:
        return "Play", "Play"

    if state == "paused":
        return "Play", f"Play, {name} paused"

    # playing / buffering
    if song:
        return "Pause", f"Pause, now playing {song} on {name}"
    return "Pause", f"Pause, now playing {name}"


def label_string(state: str, station: Optional[dict], song: str) -> str:
    """Return the visible 'Now playing:' label text."""
    name = _station_name(station)
    song = (song or "").strip()

    if state == "error":
        return "Playback error"

    if state == "stopped" or not name:
        return "Not playing"

    if state == "paused":
        return f"{name} {EM_DASH} paused"

    # playing / buffering
    if song:
        return f"Now playing: {song} {EM_DASH} {name}"
    return f"Now playing: {name}"
