from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    destination = root / "wechat_media_exporter" / "assets" / "app-icon.ico"

    scale = 4
    size = 64 * scale
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    padding = 3 * scale
    radius = 14 * scale
    draw.rounded_rectangle(
        (padding, padding, size - padding, size - padding),
        radius=radius,
        fill="#07894B",
    )

    stroke = 3 * scale
    image_box = (14 * scale, 17 * scale, 50 * scale, 45 * scale)
    draw.rounded_rectangle(
        image_box,
        radius=5 * scale,
        outline="#FFFFFF",
        width=stroke,
    )
    draw.ellipse(
        (22 * scale, 24 * scale, 30 * scale, 32 * scale),
        fill="#FFFFFF",
    )
    draw.line(
        (
            17 * scale,
            41 * scale,
            27 * scale,
            31 * scale,
            34 * scale,
            38 * scale,
            40 * scale,
            32 * scale,
            48 * scale,
            40 * scale,
        ),
        fill="#FFFFFF",
        width=stroke,
        joint="curve",
    )

    icon_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    image.save(destination, format="ICO", sizes=icon_sizes)
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
