"""从命令行入口验证透明素材检查，使用合成文件，不调用生图服务。"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image


class AlphaCheckTest(unittest.TestCase):
    def test_file_formats_and_alpha(self):
        rgb = Image.new("RGB", (2, 2), "white")
        rgb.putpixel((0, 0), (128, 128, 128))
        rgba = Image.new("RGBA", (2, 2), (0, 0, 0, 255))
        valid = rgba.copy()
        valid.putpixel((0, 0), (0, 0, 0, 0))
        partial = rgba.copy()
        partial.putpixel((0, 0), (0, 0, 0, 128))
        palette = Image.new("P", (2, 2), 1)
        palette.putpalette([0, 0, 0, 255, 255, 255] + [0] * 762)
        palette.putpixel((0, 0), 0)
        palette.info["transparency"] = 0
        cases = [("checker-rgb", rgb, False), ("opaque-rgba", rgba, False),
                 ("transparent-rgba", valid, True), ("partial-alpha", partial, True),
                 ("palette-transparency", palette, True),
                 ("empty", Image.new("RGBA", (2, 2), (0, 0, 0, 0)), False)]
        script = Path(__file__).resolve().parents[1] / "scripts/check_asset_alpha.py"
        with tempfile.TemporaryDirectory() as directory:
            for name, im, expected in cases:
                with self.subTest(name=name):
                    path = Path(directory) / (name + ".png")
                    im.save(path)
                    result = subprocess.run([sys.executable, str(script), str(path),
                                             "--require-transparency"], capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0 if expected else 2, result.stderr)
                    self.assertEqual(json.loads(result.stdout)["transparency_check_passed"], expected)


if __name__ == "__main__":
    unittest.main()
