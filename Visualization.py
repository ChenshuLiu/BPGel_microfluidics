import cv2
import pandas as pd
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
from matplotlib import cm

# Load your DataFrame
df = pd.read_csv("volume_tracking_file.csv")
min_flow = df['flow_rate_mm3_per_sec'].min()
max_flow = df['flow_rate_mm3_per_sec'].max()

def flow_to_color(flow):
    normed = (flow - min_flow) / (max_flow - min_flow)
    color = cm.inferno(normed)
    return tuple(int(255 * c) for c in color[:3])

# Load font
try:
    font_large = ImageFont.truetype("Arial Unicode.ttf", 45)
except:
    font_large = ImageFont.load_default()

# Open video
cap = cv2.VideoCapture("analysis_vid_DIRECTORY")
fps = cap.get(cv2.CAP_PROP_FPS)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

# Output writer with original resolution
out = cv2.VideoWriter("output_vid_file_NAME", cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))

frame_idx = 0

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    time_sec = frame_idx / fps
    df_idx = df[df['time_sec'] == int(time_sec)]

    frame_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
    overlay = Image.new("RGBA", frame_pil.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    if not df_idx.empty:
        volume = df_idx['volume_mm3'].values[0]
        flow = df_idx['flow_rate_mm3_per_sec'].values[0]

        # Panel settings
        panel_w, panel_h = 600, 360
        panel_x, panel_y = 50, height - panel_h - 50  # bottom-left corner
        panel_color = (0, 0, 0, 120)
        draw.rectangle([panel_x, panel_y, panel_x + panel_w, panel_y + panel_h], fill=panel_color)

        # Text
        text_color = "white"
        draw.text((panel_x + 30, panel_y + 20), f"Time: {time_sec:.1f} s", font=font_large, fill=text_color)
        draw.text((panel_x + 30, panel_y + 120), f"Volume: {volume:.1f} mm³", font=font_large, fill=text_color)
        draw.text((panel_x + 30, panel_y + 220), f"Flow Rate: {flow:.2f} mm³/s", font=font_large, fill=text_color)

        # Heatmap bar
        bar_x, bar_y, bar_w, bar_h = panel_x + panel_w - 90, panel_y + 20, 40, 300
        for i in range(bar_h):
            norm_val = i / bar_h
            color = cm.inferno(norm_val)
            color_rgb = tuple(int(255 * c) for c in color[:3])
            draw.line([(bar_x, bar_y + bar_h - i), (bar_x + bar_w, bar_y + bar_h - i)], fill=color_rgb)

        # Marker
        norm_flow = (flow - min_flow) / (max_flow - min_flow)
        marker_y = int(bar_y + bar_h - (norm_flow * bar_h))
        draw.rectangle([bar_x - 4, marker_y - 6, bar_x + bar_w + 4, marker_y + 6], fill="white")

    # Composite with transparency
    frame_annotated = Image.alpha_composite(frame_pil, overlay).convert("RGB")
    out.write(cv2.cvtColor(np.array(frame_annotated), cv2.COLOR_RGB2BGR))
    frame_idx += 1

cap.release()
out.release()
print("✅ Annotated video saved at original resolution.")
