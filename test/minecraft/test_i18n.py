import pytest
from hexdoc.core import ResourceLocation
from hexdoc.minecraft import I18n


@pytest.mark.parametrize(
    ["namespace", "path", "want"],
    [
        ("forge", "ores", "Ores"),
        ("c", "saplings/almond", "Almond Saplings"),
        ("c", "tea_ingredients/gloopy/weak", "Tea Ingredients, Gloopy, Weak"),
    ],
)
def test_fallback_tag_name(namespace: str, path: str, want: str):
    tag = ResourceLocation(namespace, path)

    i18n = I18n(
        lookup={},
        lang="en_us",
        allow_missing=True,
        default_i18n=None,
    )

    got = i18n.fallback_tag_name(tag)

    assert got == want
