import cv2
import numpy as np
import csv

# Global variables for drawing and masks
drawing = False
ix, iy = -1, -1
current_segment = 0
segment_masks = [None] * 4  # Four segments
color_sample_mask = None
roi_defined = False
roi = (0, 0, 0, 0)
brush_size = 10


def select_roi(event, x, y, flags, param):
    global drawing, ix, iy, roi_defined, roi
    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        ix, iy = x, y
    elif event == cv2.EVENT_MOUSEMOVE and drawing:
        frame_copy = param.copy()
        cv2.rectangle(frame_copy, (ix, iy), (x, y), (0, 255, 0), 2)
        cv2.imshow("Select ROI", frame_copy)
    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        roi = (min(ix, x), min(iy, y), abs(x - ix), abs(y - iy))
        roi_defined = True


def draw_mask(event, x, y, flags, param):
    global drawing, color_sample_mask, brush_size
    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        cv2.circle(color_sample_mask, (x, y), brush_size, 1, -1)
    elif event == cv2.EVENT_MOUSEMOVE and drawing:
        cv2.circle(color_sample_mask, (x, y), brush_size, 1, -1)
    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        cv2.circle(color_sample_mask, (x, y), brush_size, 1, -1)


def extract_hsv_range(frame, mask, tolerance=15):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    pixels = hsv[mask.astype(bool)]
    h, s, v = np.median(pixels, axis=0)
    lower = np.array([max(h - tolerance, 0), 50, 50], dtype=np.uint8)
    upper = np.array([min(h + tolerance, 179), 255, 255], dtype=np.uint8)
    return lower, upper


def define_segment_masks(frame):
    masks = []
    global brush_size

    for i in range(4):
        print(f"Paint mask for segment {i+1} (press Enter when done, +/- to change brush size)...")
        mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        clone = frame.copy()
        window_name = f"Paint Segment {i+1}"

        def paint_callback(event, x, y, flags, param):
            nonlocal mask
            if event == cv2.EVENT_LBUTTONDOWN or (event == cv2.EVENT_MOUSEMOVE and flags == cv2.EVENT_FLAG_LBUTTON):
                cv2.circle(mask, (x, y), brush_size, 1, -1)
            elif event == cv2.EVENT_RBUTTONDOWN or (event == cv2.EVENT_MOUSEMOVE and flags == cv2.EVENT_FLAG_RBUTTON):
                cv2.circle(mask, (x, y), brush_size, 0, -1)

        cv2.namedWindow(window_name)
        cv2.setMouseCallback(window_name, paint_callback)

        while True:
            display = clone.copy()
            display[mask > 0] = (0, 0, 255)  # Red overlay
            cv2.putText(display, f"Brush size: {brush_size}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.imshow(window_name, display)
            key = cv2.waitKey(1) & 0xFF
            if key == 13:  # Enter
                break
            elif key == ord('+') or key == ord('='):
                brush_size += 1
            elif key == ord('-') and brush_size > 1:
                brush_size -= 1

        cv2.destroyWindow(window_name)
        masks.append(mask)
    return masks


def calculate_volume(fluid_mask, segment_masks, segment_heights, known_segment_areas):
    total_volume = 0.0
    for i, segment_mask in enumerate(segment_masks):
        segment_area_pixels = np.sum(segment_mask)
        filled_pixels = np.sum(segment_mask & fluid_mask)
        if segment_area_pixels == 0:
            continue
        pixel_area = known_segment_areas[i] / segment_area_pixels
        segment_volume = filled_pixels * pixel_area * segment_heights[i]
        total_volume += segment_volume
    return total_volume


def get_color_sample_mask(frame):
    global color_sample_mask, brush_size
    color_sample_mask = np.zeros(frame.shape[:2], dtype=np.uint8)
    clone = frame.copy()
    print("Draw region to sample fluid color (press 'n' when done, +/- to change brush size)...")
    cv2.namedWindow("Sample Color")
    cv2.setMouseCallback("Sample Color", draw_mask, clone)

    while True:
        overlay = clone.copy()
        overlay[color_sample_mask > 0] = [0, 0, 255]
        cv2.putText(overlay, f"Brush size: {brush_size}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.imshow("Sample Color", overlay)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('n'):
            break
        elif key == ord('+') or key == ord('='):
            brush_size += 1
        elif key == ord('-') and brush_size > 1:
            brush_size -= 1

    cv2.destroyWindow("Sample Color")
    return color_sample_mask


def process_video_color_tracking(video_path, segment_heights, known_segment_areas, frame_interval_sec=1, output_csv="color_volumes.csv"):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    interval = int(fps * frame_interval_sec)
    frame_idx = 0
    results = []

    ret, frame = cap.read()
    if not ret:
        print("Failed to read video.")
        return

    # Get fluid color sample
    sample_mask = get_color_sample_mask(frame)
    lower_hsv, upper_hsv = extract_hsv_range(frame, sample_mask)

    # Get ROI for tracking
    global roi_defined, roi
    roi_defined = False
    print("Draw a rectangular region where detection will happen (press Enter when done)")
    cv2.imshow("Select ROI", frame)
    cv2.setMouseCallback("Select ROI", select_roi, frame.copy())
    while not roi_defined:
        cv2.waitKey(1)
    cv2.destroyWindow("Select ROI")
    rx, ry, rw, rh = roi
    detection_mask = np.zeros(frame.shape[:2], dtype=np.uint8)
    detection_mask[ry:ry+rh, rx:rx+rw] = 1

    # Define chamber segments (4)
    segment_masks = define_segment_masks(frame)

    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % interval == 0:
            # Calculate current time in seconds
            current_time_sec = frame_idx / fps

            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, lower_hsv, upper_hsv)
            mask = mask & (detection_mask * 255)

            fluid_mask = (mask > 0).astype(np.uint8)
            volume = calculate_volume(fluid_mask, segment_masks, segment_heights, known_segment_areas)
            print(f"Time {current_time_sec:.2f} s: Volume = {volume:.2f} mm³")
            results.append({
                "time_sec": current_time_sec,
                "volume_mm3": volume
            })

        frame_idx += 1

    cap.release()

    # Save CSV with time instead of frame number
    with open(output_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["time_sec", "volume_mm3"])
        writer.writeheader()
        writer.writerows(results)

    print(f"\nVolume results saved to: {output_csv}")


# Example usage:
segment_heights = [0.15, 0.25, 0.25, 0.25]          # mm
known_segment_areas = [170.0, 13.0, 9.8, 67.4]      # mm²

process_video_color_tracking(
    video_path="/Users/liuchenshu/Documents/Research/NUS/Jiaqi Zhang/jiaqi_vid_best.mov",
    segment_heights=segment_heights,
    known_segment_areas=known_segment_areas,
    frame_interval_sec=0.1,
    output_csv="tracked_volumes_20250815.csv"
)
