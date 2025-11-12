from ultralytics import YOLO
import cv2
import os
import sys

# --------- SETTINGS ----------
model_path = r"C:\Users\fotop\Desktop\MyCodes\Clean Streams working - Copy\River-pollution-Object-Detection-Model-YOLOV8-main\yolov8n.pt"   # Change to your trained model if needed
video_path = r"C:\Users\fotop\Desktop\MyCodes\Clean Streams working - Copy\flights\nj_20251101_025822.pm4"
print("Opened?", cap.isOpened())
# ✅ OUTPUT FILE MUST INCLUDE A FILENAME (NOT JUST THE FOLDER)
output_path = r"C:\Users\fotop\Desktop\MyCodes\Clean Streams working - Copy\flights\processed_output.mp4"
save_output = True
# ------------------------------
print("Using OpenCV:", cv2.__version__)
print("Video path:", video_path)
print("Exists on disk?", os.path.isfile(video_path))

# Load model
model = YOLO(model_path)

# Load video
cap = cv2.VideoCapture(video_path)
print("Video opened?", cap.isOpened())
print("Frame size:", cap.get(cv2.CAP_PROP_FRAME_WIDTH), cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

if not cap.isOpened():
    print("❌ ERROR: Could not open input video")
    exit()

# Setup video writer if saving enabled
if save_output:
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(
        output_path,
        fourcc,
        30.0,
        (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    )

    if not out.isOpened():
        print("❌ ERROR: Could not open output file:", output_path)
        exit()
    else:
        print("✅ Output file ready:", output_path)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Run YOLO on the frame
    results = model(frame)

    # Draw detections
    annotated = results[0].plot()

    # Show the output in a window
    cv2.imshow("YOLO Video", annotated)

    # Save the result
    if save_output:
        out.write(annotated)

    # Press Q to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
if save_output:
    out.release()
cv2.destroyAllWindows()
