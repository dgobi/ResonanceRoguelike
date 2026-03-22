1. Requirements

Python installed

Pillow library installed

Install Pillow:

pip install Pillow

Verify Python works:

py --version
2. Prepare your files

Place in the same folder:

sprite_ref.py

your spritesheet (e.g. tiles.png)

3. Open PowerShell in that folder

In File Explorer:

Navigate to the folder

Click the address bar

Type:

powershell

Press Enter

4. Run the script
Basic (default tile size = 12×12)
py .\sprite_ref.py tiles.png
With tile size
py .\sprite_ref.py tiles.png 16 16

First number = tile width

Second number = tile height

5. Output

The script will generate PNG files in the same folder:

tiles_ref_0000_0499.png
tiles_ref_0500_0999.png

Each image shows:

Enlarged tiles

Index number under each tile

6. Using the indices

Find a tile in the reference image (e.g. index 137)

Single-row spritesheet:
"tile_name": { "sheet": "tiles", "col": 137, "row": 0 }
Multi-row spritesheet:
"tile_name": { "sheet": "tiles", "col": 9, "row": 2 }
7. Common issues
Script opens in VS Code instead of running

You are not invoking Python. Use:

py .\sprite_ref.py tiles.png
“File not found”

Check file exists:

dir
No output images

Ensure tile size is correct

Ensure PNG is valid

Check console for errors

8. Optional: Use full path

If needed:

py "C:\path\to\sprite_ref.py" "C:\path\to\tiles.png" 16 16
9. Help command
py .\sprite_ref.py --help