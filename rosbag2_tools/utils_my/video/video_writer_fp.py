import os
import re
import subprocess
import threading
from copy import deepcopy
from queue import Empty, Queue

import cv2
import ffmpeg


def get_ffmpeg_video_encoders():
    try:
        # 调用 ffmpeg 获取编码器信息
        result = subprocess.run(
            ["ffmpeg", "-encoders"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        # ' V..... r10k                 AJA Kona 10-bit RGB Codec'

        # 正则表达式匹配编码器的名称和 codec 类型
        encoder_regex = re.compile(r"^\s*(V|A|S)\.+\s+(\w+)\s+(.*)$", re.MULTILINE)
        encoders = []
        # 遍历匹配结果
        for match in encoder_regex.finditer(result.stdout):
            codec_type = match.group(1)  # V: Video, A: Audio, S: Subtitle

            encoder_name = match.group(2)  # 编码器名称
            if codec_type == "V":
                encoders.append(encoder_name)
            # encoder_description = match.group(3)  # 编码器描述
            # encoders.append((codec_type, encoder_name, encoder_description))

        # 打印所有编码器及其 codec 类型
        # for codec_type, encoder_name, encoder_description in encoders:
        # codec_type_desc = {
        #     'V': 'Video',
        #     'A': 'Audio',
        #     'S': 'Subtitle'
        # }.get(codec_type, 'Unknown')

        # print(f"Codec Type: {codec_type_desc}, Encoder: {encoder_name}, Description: {encoder_description}")

        return encoders

    except FileNotFoundError:
        print("ffmpeg 未安装或无法找到")
        return []


class VideoWriter(object):
    def __init__(
        self, file_path, fps, write=True, show=False, pix_fmt="bgr24", new_thread=True
    ):
        self.file_path = str(file_path)
        self.fps = fps
        self._enable_write = write
        self._t_writer = None
        self.show = show
        if show:
            if not isinstance(show, str):
                self.show = "show"

        if not self._enable_write:
            return

        self.quiet = False
        self.loglevel = "quiet"
        encoders = get_ffmpeg_video_encoders()
        l_h264_codec = ["h264_nvenc", "libx264"]
        self.codec_name = None
        for codec in l_h264_codec:
            if codec in encoders:
                self.codec_name = codec
                break
        if self.codec_name is None:
            raise ValueError("No support h264 codec, use libx264")
        self.stop_flag = False
        self.pix_fmt = pix_fmt
        self._new_thread = new_thread
        self.p = None
        if self._new_thread:
            self._t_writer = threading.Thread(
                target=self.run, name="thread_video_writer"
            )
            self.con = threading.Condition()
            self.img_queue = Queue(100)

    def run(self):
        while True:
            if self.stop_flag and self.img_queue.empty():
                break
            try:
                img_write, format = self.img_queue.get(timeout=0.1)
                self.encode_img(img_write, format)
            except Empty as e:
                pass
        # print("thread_video_writer thread exit")
        self._finish_video()

    def write_img_async(self, cv_img, format="bgr24"):
        self.img_queue.put((deepcopy(cv_img), format))

    def write(self, cv_img, format="bgr24"):
        if self._enable_write:
            if self._new_thread:
                if self._t_writer.is_alive() is False:
                    self._t_writer.start()
                self.write_img_async(cv_img, format)
            else:
                self.encode_img(cv_img, format)

        if self.show:
            cv2.namedWindow(self.show, cv2.WINDOW_NORMAL)
            cv2.imshow(self.show, cv_img)
            cv2.waitKey(1)

    def encode_img(self, cv_img, pix_fmt="bgr24"):
        if self.p is None:
            height, width, _ = cv_img.shape
            os.makedirs(os.path.dirname(os.path.abspath(self.file_path)), exist_ok=True)

            args = (
                ffmpeg.input(
                    "pipe:",
                    format="rawvideo",
                    pix_fmt=pix_fmt,
                    s="{}x{}".format(width, height),
                )
                .output(
                    self.file_path,
                    pix_fmt="yuv420p",
                    **{"loglevel": self.loglevel, "c:v": self.codec_name}
                )
                .overwrite_output()
                .compile()
                # .run_async(pipe_stdin=True)
            )
            stdin_stream = subprocess.PIPE
            stdout_stream = None
            stderr_stream = None
            if self.quiet:
                stderr_stream = subprocess.STDOUT
                stdout_stream = subprocess.DEVNULL

            self.p = subprocess.Popen(
                args, stdin=subprocess.PIPE, stdout=stdout_stream, stderr=stderr_stream
            )

        self.p.stdin.write(cv_img.tobytes())

    def _finish_video(self):
        if self.p is not None:
            self.p.stdin.close()
            self.p.wait()

    def release(self):
        if not self._enable_write:
            return

        if self._t_writer is not None:
            self.stop_flag = True
            self._t_writer.join()
        else:
            self._finish_video()

        if self.show:
            try:
                cv2.destroyWindow(self.show)
            except:
                pass

    def __del__(self):
        # print("VideoWriter.__del__")
        self.release()


if __name__ == "__main__":
    import numpy as np

    writer = VideoWriter("test.mp4", 30, write=True, show="show")
    for i in range(100):
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(
            img, str(i), (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 3, (255, 255, 255), 2
        )
        writer.write(img)
    writer.release()
    print("done")
