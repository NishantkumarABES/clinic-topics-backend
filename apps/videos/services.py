from moviepy.editor import VideoFileClip

def generate_thumbnail_moviepy(video_path, output_image_path, time_in_seconds=1.0):
    try:
        clip = VideoFileClip(video_path)
        duration = clip.duration
        clip.save_frame(output_image_path, t=time_in_seconds) 
        clip.close()
        return duration
    except Exception as e:
        print(f"An error occurred: {e}")


