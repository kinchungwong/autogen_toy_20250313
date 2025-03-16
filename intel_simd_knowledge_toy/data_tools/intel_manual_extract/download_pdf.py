from pathlib import Path
from intel_simd_knowledge_toy.data_tools.network.download_url import download_url

if __name__ == "__main__":
    _URL = r'''https://community.intel.com/legacyfs/online/drupal_files/managed/a4/60/325383-sdm-vol-2abcd.pdf'''
    _OVERWRITE = False
    cwd = Path.cwd()
    target_dir = cwd / "intel_simd_knowledge_toy" / "data" / "downloads"
    target_file = target_dir / "325383-sdm-vol-2abcd-dec-24.pdf"
    if not _OVERWRITE and target_file.is_file():
        print(f"The target file already exists at {target_file}")
        exit()
    download_url(_URL, target_file)
