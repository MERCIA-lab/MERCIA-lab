#!/usr/bin/env python3
"""
generate_animated_avatar.py
---------------------------
Synthesizes a high-fidelity, looping animated character avatar GIF from a portrait photo
or character artwork.

Features:
- Micro-floating and idle breathing motion with smooth sinusoidal interpolation.
- Cybernetic / smart-glasses specular light glint sweeping across lenses.
- Breathing ambient tech aura (cyan/blue gradient ring).
- Circular or squircle frame clipping with smooth anti-aliased alpha borders.
- Adaptive color quantization & palette optimization for fast GitHub load times.
- Pure Python using Pillow, NumPy, and standard libraries.
"""

import os
import sys
import math
import argparse
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageOps
import numpy as np

DEFAULT_INPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "character-white.jpg")
DEFAULT_OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "animated-character-white.gif")
FALLBACK_PHOTO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "avatar-source.png")


def stylize_raw_photo(img: Image.Image) -> Image.Image:
    """
    Transforms a real-world photo into a stylized digital cartoon/portrait
    using edge enhancement, color quantization, and bilateral-style smoothing.
    """
    img_rgb = img.convert("RGB")
    
    # Smooth skin and reduce noise while keeping major contours
    smoothed = img_rgb.filter(ImageFilter.SMOOTH_MORE).filter(ImageFilter.SMOOTH_MORE)
    
    # Enhance color saturation and contrast for animated look
    enhancer_col = ImageEnhance.Color(smoothed)
    vibrant = enhancer_col.enhance(1.25)
    
    enhancer_con = ImageEnhance.Contrast(vibrant)
    contrast = enhancer_con.enhance(1.15)
    
    # Extract edges for subtle cartoon inking
    gray = contrast.convert("L")
    edges = gray.filter(ImageFilter.FIND_EDGES)
    edges = ImageOps.invert(edges)
    edges = edges.point(lambda p: 255 if p > 200 else (180 if p > 140 else 80))
    
    # Blend edges gently with vibrant image
    edges_rgb = Image.merge("RGB", (edges, edges, edges))
    stylized = Image.blend(contrast, edges_rgb, alpha=0.15)
    return stylized


def create_circular_mask(size: tuple[int, int]) -> Image.Image:
    """Creates a high-resolution anti-aliased circular alpha mask."""
    w, h = size
    # 4x supersampling for ultra smooth anti-aliasing
    scale = 4
    mask_large = Image.new("L", (w * scale, h * scale), 0)
    draw = ImageDraw.Draw(mask_large)
    
    pad = 4 * scale
    draw.ellipse([pad, pad, w * scale - pad, h * scale - pad], fill=255)
    return mask_large.resize((w, h), Image.Resampling.LANCZOS)


def render_avatar_frame(
    base_img: Image.Image,
    frame_idx: int,
    total_frames: int,
    canvas_size: int = 400,
    ring_color_a: tuple[int, int, int] = (56, 189, 248),   # Sky blue
    ring_color_b: tuple[int, int, int] = (129, 140, 248),  # Indigo
) -> Image.Image:
    """
    Renders a single frame of the looping avatar animation.
    """
    t = frame_idx / float(total_frames)  # 0.0 to 1.0
    phase = 2.0 * math.pi * t
    
    # 1. Idle breathing & floating calculation
    float_y = int(round(math.sin(phase) * 5.0))
    scale_factor = 1.0 + (math.sin(phase) * 0.015)
    
    # Prepare canvas with GitHub dark theme background (#0d1117)
    canvas = Image.new("RGBA", (canvas_size, canvas_size), (13, 17, 23, 255))
    draw = ImageDraw.Draw(canvas)
    
    # 2. Draw ambient outer tech pulse ring
    pulse = (math.sin(phase) + 1.0) / 2.0  # 0.0 to 1.0
    ring_radius = int((canvas_size / 2) - 10 + (pulse * 3.0))
    center = canvas_size // 2
    
    # Gradient interpolation for the tech ring
    r = int(ring_color_a[0] * (1 - pulse) + ring_color_b[0] * pulse)
    g = int(ring_color_a[1] * (1 - pulse) + ring_color_b[1] * pulse)
    b = int(ring_color_a[2] * (1 - pulse) + ring_color_b[2] * pulse)
    
    # Draw soft outer glow
    for offset in range(3, 0, -1):
        glow_alpha = int(25 * (4 - offset) * (0.6 + 0.4 * pulse))
        draw.ellipse(
            [center - ring_radius - offset, center - ring_radius - offset,
             center + ring_radius + offset, center + ring_radius + offset],
            outline=(r, g, b, glow_alpha),
            width=2
        )
    
    # Draw crisp primary border ring
    draw.ellipse(
        [center - ring_radius, center - ring_radius,
         center + ring_radius, center + ring_radius],
        outline=(r, g, b, 240),
        width=3
    )
    
    # 3. Scale and position character inside the circular portal
    inner_dim = int((ring_radius - 3) * 2)
    cur_w = int(round(inner_dim * scale_factor))
    cur_h = int(round(inner_dim * scale_factor))
    
    char_resized = base_img.resize((cur_w, cur_h), Image.Resampling.LANCZOS)
    
    # Crop to inner_dim
    crop_x = (cur_w - inner_dim) // 2
    crop_y = (cur_h - inner_dim) // 2 + float_y
    # Clamp crop bounds
    crop_y = max(0, min(crop_y, cur_h - inner_dim))
    char_cropped = char_resized.crop((crop_x, crop_y, crop_x + inner_dim, crop_y + inner_dim))
    
    # 4. Smart Glasses Glint / Specular Light Sweep
    # Glint sweeps diagonally across the glasses region during 20% to 55% of the loop
    glint_start = 0.20
    glint_end = 0.55
    if glint_start <= t <= glint_end:
        glint_progress = (t - glint_start) / (glint_end - glint_start)  # 0.0 -> 1.0
        glint_layer = Image.new("RGBA", char_cropped.size, (0, 0, 0, 0))
        glint_draw = ImageDraw.Draw(glint_layer)
        
        # Diagonal beam across eye/glasses band (Y approx 30% to 45%)
        sweep_x = int(inner_dim * glint_progress * 1.3 - (inner_dim * 0.15))
        glasses_y = int(inner_dim * 0.35)
        band_height = int(inner_dim * 0.14)
        beam_width = 18
        
        # Polygon angled slash
        p1 = (sweep_x - beam_width, glasses_y - band_height // 2)
        p2 = (sweep_x + beam_width, glasses_y - band_height // 2)
        p3 = (sweep_x + beam_width - 15, glasses_y + band_height // 2)
        p4 = (sweep_x - beam_width - 15, glasses_y + band_height // 2)
        
        # Soft white glint with translucent core
        glint_draw.polygon([p1, p2, p3, p4], fill=(255, 255, 255, 110))
        # Center hot glint
        core_w = 6
        c1 = (sweep_x - core_w, glasses_y - band_height // 2)
        c2 = (sweep_x + core_w, glasses_y - band_height // 2)
        c3 = (sweep_x + core_w - 15, glasses_y + band_height // 2)
        c4 = (sweep_x - core_w - 15, glasses_y + band_height // 2)
        glint_draw.polygon([c1, c2, c3, c4], fill=(255, 255, 255, 190))
        
        # Blur the glint slightly for realistic sheen
        glint_blurred = glint_layer.filter(ImageFilter.GaussianBlur(radius=2))
        char_cropped = Image.alpha_composite(char_cropped.convert("RGBA"), glint_blurred)
    
    # 5. Composite cropped character through circular mask onto canvas
    inner_mask = create_circular_mask((inner_dim, inner_dim))
    portal_pos = (center - inner_dim // 2, center - inner_dim // 2)
    canvas.paste(char_cropped, portal_pos, inner_mask)
    
    # 6. Orbiting tech data particle
    particle_angle = phase * 1.0
    orbit_r = ring_radius + 1
    px = int(center + orbit_r * math.cos(particle_angle))
    py = int(center + orbit_r * math.sin(particle_angle))
    particle_size = 3
    draw.ellipse(
        [px - particle_size, py - particle_size, px + particle_size, py + particle_size],
        fill=(255, 255, 255, 240)
    )
    
    return canvas


def generate_animated_avatar(
    input_path: str,
    output_path: str,
    frames_count: int = 24,
    fps: int = 15,
    size: int = 400,
    stylize: bool = False,
) -> str:
    """
    Processes the source image and generates the animated looping GIF.
    """
    if not os.path.exists(input_path):
        if os.path.exists(FALLBACK_PHOTO):
            print(f"[!] Target {input_path} not found. Using fallback photo {FALLBACK_PHOTO}")
            input_path = FALLBACK_PHOTO
            stylize = True
        else:
            raise FileNotFoundError(f"Input file not found: {input_path}")
    
    print(f"[*] Loading source image: {input_path}")
    raw_img = Image.open(input_path).convert("RGBA")
    
    # Crop to square aspect ratio (centered on upper-torso / face)
    w, h = raw_img.size
    crop_size = min(w, h)
    left = (w - crop_size) // 2
    top = int((h - crop_size) * 0.15)  # slight bias towards head/face
    right = left + crop_size
    bottom = top + crop_size
    # Clamp bounds
    if bottom > h:
        bottom = h
        top = h - crop_size
    
    cropped_square = raw_img.crop((left, top, right, bottom))
    
    if stylize:
        print("[*] Applying cartoon stylization filters to raw photo...")
        base_img = stylize_raw_photo(cropped_square)
    else:
        base_img = cropped_square
        
    print(f"[*] Rendering {frames_count} frames at {fps} fps ({size}x{size} px)...")
    frames = []
    duration_ms = int(1000 / fps)
    
    for i in range(frames_count):
        frame = render_avatar_frame(base_img, i, frames_count, canvas_size=size)
        # Convert to RGB with GitHub-friendly dark background (#0d1117)
        frame_rgb = Image.new("RGB", frame.size, (13, 17, 23))
        frame_rgb.paste(frame, mask=frame.split()[3])
        # Adaptive palette quantization with Floyd-Steinberg dithering for smooth gradients
        frame_p = frame_rgb.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG)
        frames.append(frame_p)
        print(f"    Frame {i+1}/{frames_count} done", end="\r")
    
    print("\n[*] Assembling and optimizing looping GIF...")
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0,
        optimize=True,
    )
    
    file_size_kb = os.path.getsize(output_path) / 1024.0
    print(f"[✓] Successfully generated: {output_path} ({file_size_kb:.1f} KB)")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate animated developer character avatar GIF")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Path to input character image or photo")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Path to output GIF")
    parser.add_argument("--frames", type=int, default=24, help="Number of frames in animation loop")
    parser.add_argument("--fps", type=int, default=15, help="Playback frames per second")
    parser.add_argument("--size", type=int, default=400, help="Width & height in pixels")
    parser.add_argument("--stylize", action="store_true", help="Apply cartoon stylization to raw photos")
    
    args = parser.parse_args()
    generate_animated_avatar(
        input_path=args.input,
        output_path=args.output,
        frames_count=args.frames,
        fps=args.fps,
        size=args.size,
        stylize=args.stylize,
    )


if __name__ == "__main__":
    main()

