from moviepy.editor import VideoFileClip

src = r"C:\Users\fotop\Desktop\MyCodes\Clean Streams working - Copy\flights\hnujk_20251101_024802.avi"
dst = r"C:\Users\fotop\Desktop\MyCodes\Clean Streams working - Copy\flights\converted.mp4"

clip = VideoFileClip(src)
clip.write_videofile(dst, codec="libx264")
print("✅ Converted to:", dst)
