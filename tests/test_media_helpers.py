from app.services.media import _ass_color, dimensions


def test_ass_color_converts_rgb_to_ass_bgr():
    assert _ass_color("#FF0000") == "&H000000FF"
    assert _ass_color("#123456") == "&H00563412"


def test_dimensions():
    assert dimensions("9:16") == (1080, 1920)
    assert dimensions("16:9") == (1920, 1080)
    assert dimensions("1:1") == (1080, 1080)
