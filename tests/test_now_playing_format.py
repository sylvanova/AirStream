from services.now_playing_format import button_strings, label_string


def test_no_station():
    btn_visible, btn_a11y = button_strings(state="stopped", station=None, song="")
    assert btn_visible == "Play"
    assert btn_a11y == "Play"
    assert label_string(state="stopped", station=None, song="") == "Not playing"


def test_stopped_with_remembered_station_still_reads_as_idle():
    btn_visible, btn_a11y = button_strings(
        state="stopped", station={"name": "Soma FM"}, song=""
    )
    assert btn_visible == "Play"
    assert btn_a11y == "Play"
    assert (
        label_string(state="stopped", station={"name": "Soma FM"}, song="")
        == "Not playing"
    )


def test_playing_no_song_yet():
    btn_visible, btn_a11y = button_strings(
        state="playing", station={"name": "Soma FM"}, song=""
    )
    assert btn_visible == "Pause"
    assert btn_a11y == "Pause, now playing Soma FM"
    assert (
        label_string(state="playing", station={"name": "Soma FM"}, song="")
        == "Now playing: Soma FM"
    )


def test_buffering_treated_like_playing():
    btn_visible, btn_a11y = button_strings(
        state="buffering", station={"name": "Soma FM"}, song=""
    )
    assert btn_visible == "Pause"
    assert btn_a11y == "Pause, now playing Soma FM"


def test_playing_with_song():
    btn_visible, btn_a11y = button_strings(
        state="playing", station={"name": "Soma FM"}, song="Tycho - A Walk"
    )
    assert btn_visible == "Pause"
    assert btn_a11y == "Pause, now playing Tycho - A Walk on Soma FM"
    assert (
        label_string(state="playing", station={"name": "Soma FM"}, song="Tycho - A Walk")
        == "Now playing: Tycho - A Walk — Soma FM"
    )


def test_paused_drops_song_info():
    btn_visible, btn_a11y = button_strings(
        state="paused", station={"name": "Soma FM"}, song="Tycho - A Walk"
    )
    assert btn_visible == "Play"
    assert btn_a11y == "Play, Soma FM paused"
    assert (
        label_string(state="paused", station={"name": "Soma FM"}, song="Tycho - A Walk")
        == "Soma FM — paused"
    )


def test_error_state():
    btn_visible, btn_a11y = button_strings(
        state="error", station={"name": "Soma FM"}, song=""
    )
    assert btn_visible == "Play"
    assert btn_a11y == "Play"
    assert (
        label_string(state="error", station={"name": "Soma FM"}, song="")
        == "Playback error"
    )
