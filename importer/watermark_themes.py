import argparse
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


DEFAULT_TEXT = "Tiên Hiệp Lâu"


def get_image_converter() -> str | None:
    return shutil.which("magick") or shutil.which("convert")


def find_font(candidates: list[str], fallback: str) -> str:
    converter = get_image_converter()
    if converter:
        try:
            result = subprocess.run(
                [converter, "-list", "font"],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            available_fonts = set(re.findall(r"^\s*Font:\s*(.+)$", result.stdout, flags=re.MULTILINE))
            for candidate in candidates:
                if candidate in available_fonts:
                    return candidate
        except Exception:
            pass

    fc_match = shutil.which("fc-match")
    if not fc_match:
        return fallback

    for candidate in candidates:
        try:
            result = subprocess.run(
                [fc_match, "-f", "%{family}", candidate],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            continue

        family = result.stdout.split(",")[0].strip()
        if family:
            return family

    return fallback


def add_watermark(image_path: Path, text: str, *, dry_run: bool = False) -> int:
    converter = get_image_converter()
    if not converter:
        raise RuntimeError("Không tìm thấy ImageMagick 'magick' hoặc 'convert'.")

    font = find_font(
        [
            "Noto-Serif-CJK-SC",
            "Noto-Serif-CJK-TC",
            "Noto Serif CJK SC",
            "Noto Serif CJK TC",
            "Noto Serif",
            "Source Han Serif SC",
            "DejaVu Serif",
        ],
        "DejaVu-Serif",
    )

    if dry_run:
        return image_path.stat().st_size

    with tempfile.NamedTemporaryFile(suffix=".webp", delete=False) as temp:
        temp_path = Path(temp.name)

    command = [
        converter,
        str(image_path),
        "-gravity",
        "southeast",
        "-fill",
        "#f8eedbc2",
        "-stroke",
        "#8f672c66",
        "-strokewidth",
        "1",
        "-draw",
        "roundrectangle 214,444 310,470 6,6",
        "-stroke",
        "none",
        "-font",
        font,
        "-fill",
        "#6f512eaa",
        "-pointsize",
        "12",
        "-annotate",
        "+16+16",
        text,
        "-strip",
        "-quality",
        "54",
        "-define",
        "webp:method=6",
        str(temp_path),
    ]
    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if temp_path.stat().st_size <= 0:
            raise RuntimeError(f"File output rỗng: {image_path}")
        shutil.move(str(temp_path), image_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()

    return image_path.stat().st_size


def iter_theme_paths(paths: list[str]) -> list[Path]:
    theme_paths: list[Path] = []
    for value in paths:
        path = Path(value)
        if path.is_dir():
            theme = path / "theme.webp"
            if theme.exists():
                theme_paths.append(theme)
        elif path.name == "theme.webp" and path.exists():
            theme_paths.append(path)
        else:
            print(f"⚠️  Bỏ qua vì không tìm thấy theme.webp: {value}")
    return theme_paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Thêm watermark nhỏ vào góc bìa theme.webp.")
    parser.add_argument("paths", nargs="+", help="Danh sách folder truyện hoặc file theme.webp.")
    parser.add_argument("--text", default=DEFAULT_TEXT, help="Nội dung watermark.")
    parser.add_argument("--dry-run", action="store_true", help="Chỉ liệt kê, không sửa file.")
    args = parser.parse_args()

    theme_paths = iter_theme_paths(args.paths)
    if not theme_paths:
        print("Không có theme.webp nào để xử lý.")
        return

    sizes = []
    for theme_path in theme_paths:
        size = add_watermark(theme_path, args.text, dry_run=args.dry_run)
        sizes.append(size)
        action = "Sẽ xử lý" if args.dry_run else "Đã xử lý"
        print(f"{action}: {theme_path} ({size:,} bytes)")

    print(f"\nHoàn tất: {len(theme_paths)} theme.webp")
    if sizes:
        print(f"Tổng dung lượng: {sum(sizes):,} bytes")


if __name__ == "__main__":
    main()
