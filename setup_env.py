import os
import urllib.request

# Define paths
output_dirs = [
    'output/videos',
    'output/thumbnails',
    'assets/images',
    'assets/audio',
    'templates/fonts',
]

# Create directories
for d in output_dirs:
    os.makedirs(d, exist_ok=True)
    print(f"Directory ready: {d}")

# Download font
# Using a more direct and reliable URL for Montserrat-Bold
font_url = 'https://raw.githubusercontent.com/google/fonts/main/ofl/montserrat/Montserrat%5Bwght%5D.ttf'
# Fallback to a known working raw URL if needed
backup_font_url = 'https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Bold.ttf'

font_path = 'templates/fonts/Montserrat-Bold.ttf'

def download_file(url, path):
    print(f"Attempting to download from: {url}")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response, open(path, 'wb') as out_file:
        data = response.read()
        out_file.write(data)
    return True

if not os.path.exists(font_path) or os.path.getsize(font_path) < 10000:
    print("Downloading Montserrat font...")
    success = False
    for url in [font_url, backup_font_url]:
        try:
            if download_file(url, font_path):
                # Verify it's actually a font and not an error page
                if os.path.getsize(font_path) > 10000:
                    print(f"Font downloaded successfully from {url}")
                    success = True
                    break
                else:
                    print(f"Download from {url} resulted in a small file, likely invalid.")
        except Exception as e:
            print(f"Error downloading from {url}: {e}")

    if not success:
        print("CRITICAL: Failed to download a valid font file.")
        # Create a dummy file only as a last resort to prevent crashes, but it will affect rendering
        if not os.path.exists(font_path):
            with open(font_path, "wb") as f:
                f.write(b"")
else:
    print("Font already exists and is valid.")
