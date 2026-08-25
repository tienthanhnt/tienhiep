import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 240
HEIGHT = 360


def font(path: str, size: int):
    return ImageFont.truetype(path, size)


def wrap_by_width(draw: ImageDraw.ImageDraw, text: str, font_obj, max_width: int, max_lines: int = 3) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""

    for word in words:
        candidate = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), candidate, font=font_obj)
        if not current or bbox[2] - bbox[0] <= max_width:
            current = candidate
            continue
        lines.append(current)
        current = word

    if current:
        lines.append(current)

    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(".") + "..."

    return lines


def apply_overlay(src: Path, dest: Path, title: str, author: str, quality: int = 34):
    image = Image.open(src).convert("RGB")
    scale = max(WIDTH / image.width, HEIGHT / image.height)
    image = image.resize((int(image.width * scale), int(image.height * scale)), Image.Resampling.LANCZOS)
    left = (image.width - WIDTH) // 2
    top = (image.height - HEIGHT) // 2
    image = image.crop((left, top, left + WIDTH, top + HEIGHT)).convert("RGBA")

    gradient = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw_gradient = ImageDraw.Draw(gradient)
    for y in range(0, 120):
        alpha = int(132 * (1 - y / 120))
        draw_gradient.line((0, y, WIDTH, y), fill=(246, 238, 220, alpha))
    image = Image.alpha_composite(image, gradient)

    draw = ImageDraw.Draw(image)
    title_font = font("/usr/share/fonts/truetype/noto/NotoSerif-Bold.ttf", 20)
    author_font = font("/usr/share/fonts/truetype/noto/NotoSerif-Regular.ttf", 10)
    watermark_font = font("/usr/share/fonts/truetype/noto/NotoSerif-Regular.ttf", 9)

    y = 18
    for line in wrap_by_width(draw, title, title_font, WIDTH - 28):
        bbox = draw.textbbox((0, 0), line, font=title_font)
        x = (WIDTH - (bbox[2] - bbox[0])) // 2
        draw.text((x + 1, y + 1), line, font=title_font, fill=(246, 239, 224, 210))
        draw.text((x, y), line, font=title_font, fill=(35, 28, 22, 245))
        y += 24

    if author:
        bbox = draw.textbbox((0, 0), author, font=author_font)
        draw.text(((WIDTH - (bbox[2] - bbox[0])) // 2, y + 3), author, font=author_font, fill=(81, 65, 50, 230))

    watermark = "Tiên Hiệp Lâu"
    bbox = draw.textbbox((0, 0), watermark, font=watermark_font)
    draw.text((WIDTH - bbox[2] - 8, HEIGHT - bbox[3] - 7), watermark, font=watermark_font, fill=(72, 59, 45, 155))

    dest.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(dest, "WEBP", quality=quality, method=6)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("src", type=Path)
    parser.add_argument("dest", type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--author", default="")
    parser.add_argument("--quality", type=int, default=34)
    args = parser.parse_args()
    apply_overlay(args.src, args.dest, args.title, args.author, args.quality)
    print(f"{args.dest} {args.dest.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
