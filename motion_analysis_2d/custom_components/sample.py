from pathlib import Path

import cv2

tracker_type = "CSRT"

# Get the video file and read it
video = cv2.VideoCapture(str(Path(r"C:\Users\wlyeoh\Downloads\Media1.mp4")))
ret, frame = video.read()

tracker = cv2.TrackerCSRT_create()

frame_height, frame_width = frame.shape[:2]
# Resize the video for a more convinient view
# frame = cv2.resize(frame, [frame_width // 2, frame_height // 2])

if not ret:
    print("cannot read the video")
# Select the bounding box in the first frame
# bbox = cv2.selectROI(frame, False)
# print(bbox)
print(frame.shape)
ret = tracker.init(frame, (235, 223, 344, 5))
# Start tracking
while True:
    ret, frame = video.read()
    # frame = cv2.resize(frame, [frame_width // 2, frame_height // 2])
    if not ret:
        print("something went wrong")
        break
    timer = cv2.getTickCount()
    ret, bbox = tracker.update(frame)
    fps = cv2.getTickFrequency() / (cv2.getTickCount() - timer)
    if ret:
        p1 = (int(bbox[0]), int(bbox[1]))
        p2 = (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))
        cv2.rectangle(frame, p1, p2, (255, 0, 0), 2, 1)
    else:
        cv2.putText(
            frame,
            "Tracking failure detected",
            (100, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (0, 0, 255),
            2,
        )
    cv2.putText(
        frame,
        tracker_type + " Tracker",
        (100, 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        (50, 170, 50),
        2,
    )
    cv2.putText(
        frame,
        "FPS : " + str(int(fps)),
        (100, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        (50, 170, 50),
        2,
    )
    cv2.imshow("Tracking", frame)
    k = cv2.waitKey(1) & 0xFF
    if k == 27:
        break

video.release()
cv2.destroyAllWindows()
