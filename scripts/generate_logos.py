#!/usr/bin/env python3
"""Generate PortAct logo PNGs and favicon from the source logo image."""

import os
from PIL import Image, ImageDraw

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(SCRIPT_DIR, "..", "logo", "portact_logo.png")
OUT_DIR = os.path.join(SCRIPT_DIR, "..", "frontend", "public")

SIZES = [16, 32, 48, 64, 128, 192, 512]
FAVICON_BG = (21, 101, 192)  # #1565C0 — matches theme dark primary


def make_favicon(src, size):
    """Create a favicon with a rounded-rect blue background for visibility."""
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    # Draw rounded rectangle background
    bg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(bg)
    radius = max(2, size // 5)
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=(*FAVICON_BG, 255))
    canvas.paste(bg, mask=bg)

    # Shrink logo slightly so it has padding inside the background
    pad = max(1, size // 8)
    logo_size = size - pad * 2
    logo = src.resize((logo_size, logo_size), Image.LANCZOS)
    canvas.paste(logo, (pad, pad), mask=logo)

    return canvas.convert("RGBA")


def main():
    src = Image.open(SOURCE).convert("RGBA")
    print(f"Source: {src.size[0]}x{src.size[1]} {src.mode}")

    for size in SIZES:
        out = src.resize((size, size), Image.LANCZOS)
        path = os.path.join(OUT_DIR, f"logo-{size}.png")
        out.save(path, "PNG")
        print(f"  logo-{size}.png")

    # logo.png (512x512 — main app logo)
    src.resize((512, 512), Image.LANCZOS).save(os.path.join(OUT_DIR, "logo.png"), "PNG")
    print("  logo.png (512)")

    # apple-touch-icon (180x180) — with background for iOS
    make_favicon(src, 180).save(os.path.join(OUT_DIR, "apple-touch-icon.png"), "PNG")
    print("  apple-touch-icon.png (180)")

    # favicon.ico — with background for browser tab visibility
    ico_imgs = [make_favicon(src, s) for s in (16, 32, 48)]
    ico_imgs[0].save(
        os.path.join(OUT_DIR, "favicon.ico"),
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48)],
        append_images=ico_imgs[1:],
    )
    print("  favicon.ico (16/32/48)")

    print("Done!")


if __name__ == "__main__":
    main()
