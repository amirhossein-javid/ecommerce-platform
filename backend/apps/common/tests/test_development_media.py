import mimetypes


def test_development_settings_register_webp_media_type():
    content_type, encoding = mimetypes.guess_type("product.webp")

    assert content_type == "image/webp"
    assert encoding is None
