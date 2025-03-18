from pathlib import Path
from intel_simd_knowledge_toy.data_tools.network.download_url import download_url

def fix_unicode_errors_in_intel_manual(line_text: str) -> str:
    if any(ord(c) > 127 for c in line_text):
        line_text = line_text.replace("\uf0df", "\u2190")
        line_text = line_text.replace("\uf020", "\u0020")
        line_text = line_text.replace("\uf0e0", "\U0001f86a")
        line_text = line_text.replace("\uf0e1", "\u27e8")
        line_text = line_text.replace("\uf0f1", "\u27e9")
        line_text = line_text.replace("\u0160", "\u2265")
        line_text = line_text.replace("\u0399", "\x49")
    return line_text


if __name__ == "__main__":
    cwd = Path.cwd()
    text_path = cwd / "intel_simd_knowledge_toy/data/downloads/325383-sdm-vol-2abcd-dec-24.txt"
    text_cleaned_path = text_path.with_stem(text_path.stem + "_cleaned")
    with open(text_path, "rt") as f:
        text = f.read()
    text = fix_unicode_errors_in_intel_manual(text)
    with open(text_cleaned_path, "wt") as f:
        f.write(text)
