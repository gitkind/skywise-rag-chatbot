"""
Generate visual assets for FlyWise: logo.png and hero.jpg
"""
import math
from PIL import Image, ImageDraw, ImageFont

def create_logo():
    # Crisp high-res logo with transparent background
    width, height = 480, 120
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Stylized winged emblem in Air India red & gold
    # Wing curves / feather motif
    # Left wing swoop
    draw.polygon([(30, 75), (55, 30), (85, 45), (50, 85)], fill="#C8102E")
    # Upper crest swoop (gold)
    draw.polygon([(55, 28), (95, 20), (85, 40), (60, 36)], fill="#B99A5B")
    # Tail / forward thrust arc
    draw.polygon([(48, 85), (92, 45), (105, 52), (58, 92)], fill="#7B1E35")
    # Star accent / focal point
    draw.ellipse([(95, 28), (105, 38)], fill="#B99A5B")

    # FlyWise Typography (rendered using drawn shapes/lines or default fonts)
    # Using ImageDraw text with fallback
    try:
        font_large = ImageFont.truetype("arialbd.ttf", 46)
        font_sub = ImageFont.truetype("arial.ttf", 14)
    except:
        font_large = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    draw.text((120, 26), "Fly", fill="#C8102E", font=font_large)
    draw.text((188, 26), "Wise", fill="#7B1E35", font=font_large)
    draw.text((122, 76), "AIR INDIA CUSTOMER SUPPORT", fill="#B99A5B", font=font_sub)

    img.save("assets/logo.png", "PNG")
    print("Created assets/logo.png")

def create_hero():
    # 1280x480 Hero background banner with luxury burgundy/deep red aviation theme
    w, h = 1280, 500
    img = Image.new("RGB", (w, h), "#18060B")
    draw = ImageDraw.Draw(img)

    # Draw smooth rich radial / angular gradient simulation
    for y in range(h):
        for x in range(0, w, 4):
            # Distance from upper right
            dx = (x - w * 0.8) / w
            dy = (y - h * 0.2) / h
            dist = math.sqrt(dx*dx + dy*dy)
            
            # Blend between deep wine burgundy #3D0C18, AI Red #C8102E, dark night #150508
            r = int(max(20, min(140, 160 * (1 - dist*0.9) + 25)))
            g = int(max(6, min(24, 30 * (1 - dist*0.9) + 8)))
            b = int(max(10, min(40, 55 * (1 - dist*0.9) + 12)))
            draw.rectangle([(x, y), (x+3, y)], fill=(r, g, b))

    # Aviation aesthetic lines / flight paths in shimmering muted gold and translucent red
    # Elegant flight trajectory curves
    points1 = []
    points2 = []
    for x in range(0, w, 10):
        t = x / w
        y1 = int(380 - 180 * math.sin(t * math.pi * 0.9) - 40 * t)
        y2 = int(410 - 200 * math.sin(t * math.pi * 0.85) - 30 * t)
        points1.append((x, y1))
        points2.append((x, y2))

    draw.line(points1, fill="#B99A5B", width=2)
    draw.line(points2, fill="#7B1E35", width=3)

    # Architectural diagonal grid representing modern terminal / wing design
    for i in range(-200, w + 200, 60):
        draw.line([(i, 0), (i + 350, h)], fill=(123, 30, 53), width=1)

    # Stylized airplane silhouette / vector motif soaring upwards
    plane_cx, plane_cy = int(w * 0.78), int(h * 0.42)
    # Fuselage
    draw.polygon([
        (plane_cx + 70, plane_cy - 25),
        (plane_cx - 80, plane_cy + 30),
        (plane_cx - 70, plane_cy + 35),
        (plane_cx + 80, plane_cy - 15)
    ], fill="#FAF7F2")
    # Wings
    draw.polygon([
        (plane_cx + 20, plane_cy - 5),
        (plane_cx - 20, plane_cy - 75),
        (plane_cx - 45, plane_cy - 65),
        (plane_cx - 20, plane_cy + 10)
    ], fill="#C8102E")
    draw.polygon([
        (plane_cx + 5, plane_cy + 10),
        (plane_cx - 30, plane_cy + 65),
        (plane_cx - 50, plane_cy + 60),
        (plane_cx - 25, plane_cy + 22)
    ], fill="#B99A5B")
    # Tail fin
    draw.polygon([
        (plane_cx - 70, plane_cy + 28),
        (plane_cx - 95, plane_cy - 10),
        (plane_cx - 105, plane_cy - 5),
        (plane_cx - 80, plane_cy + 33)
    ], fill="#C8102E")

    img.save("assets/hero.jpg", "JPEG", quality=92)
    print("Created assets/hero.jpg")

if __name__ == "__main__":
    create_logo()
    create_hero()
