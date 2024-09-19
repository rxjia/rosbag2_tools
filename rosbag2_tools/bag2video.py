import os

from cv_bridge import CvBridge  # Create a typestore and get the string class.
from rosbags.rosbag2 import Reader
from rosbags.typesys import Stores, get_typestore
from tqdm import tqdm

from rosbag2_tools.utils_my.video.video_writer_fp import VideoWriter

typestore = get_typestore(Stores.LATEST)


def is_bag(bag_path):
    """
    Determine if an input file or directory name is a legit rosbag.

    Allow either the rosbag directory or the metadata file to be used
    to represent the rosbag.
    """
    metadata_filename = "metadata.yaml"

    if os.path.isfile(bag_path):
        (dirname, filename) = os.path.split(bag_path)
        if filename == metadata_filename:
            return dirname

    if os.path.isdir(bag_path) and os.path.isfile(
        os.path.join(bag_path, metadata_filename)
    ):
        return bag_path

    print(f"'{bag_path}' is not a valid rosbag")


def decode_video(bag_name, fps=30.0, skip_exist=True, out_dir=None):
    with Reader(bag_name) as reader:
        # Topic and msgtype information is available on .connections list.
        print("read bag file:", bag_name)
        print("All topics:")
        for connection in reader.connections:
            print(connection.topic, connection.msgtype)
        print("-" * 20)
        
        if connection.msgtype == "sensor_msgs/msg/Image":
            print("Image message")

        img_connections = [
            x for x in reader.connections if x.msgtype == "sensor_msgs/msg/Image"
        ]
        
        if out_dir is None:
            out_dir = bag_name
        else:
            out_dir = os.path.join(out_dir, os.path.basename(bag_name))

        # filter out rgb8/bgr8 image topics
        color_connections = []
        for connection in img_connections:
            for conn, timestamp, rawdata in reader.messages(connections=[connection]):
                msg = typestore.deserialize_cdr(rawdata, connection.msgtype)
                if msg.encoding in ["rgb8", "bgr8", "mono8"]:
                    color_connections.append(connection)
                break
        color_topics = [x.topic for x in color_connections]
        # connections = [x for x in reader.connections if x.msgtype == 'sensor_msgs/msg/Image']
        print(f"Color topics: {color_topics}")

        for i, connection in enumerate(color_connections):
            print(f"Processing topic [{i}]: {connection.topic}")
            video_file_name = connection.topic
            if video_file_name[0] == "/":
                video_file_name = video_file_name[1:]
            video_file_name = video_file_name.replace("/", "_")

            cv_bridge = CvBridge()
            # if file exists, skip
            if skip_exist and os.path.exists(
                f"{os.path.join(out_dir, video_file_name)}.mp4"
            ):
                print(f"File {video_file_name}.mp4 exists, skip !")
                continue
            video_writer = VideoWriter(
                f"{os.path.join(out_dir, video_file_name)}.mp4", fps
            )
            for conn, timestamp, rawdata in tqdm(
                reader.messages(connections=[connection])
            ):
                msg = typestore.deserialize_cdr(rawdata, conn.msgtype)
                img = cv_bridge.imgmsg_to_cv2(msg, desired_encoding="rgb8")
                video_writer.write(img, "rgb24")
            video_writer.release()


def main():
    import argparse

    from rosbag2_tools.utils_my.util_dbg import inDebug
    from rosbag2_tools.utils_my.util_file import detect_walk_file

    parser = argparse.ArgumentParser()

    is_in_debug = inDebug()

    parser.add_argument(
        "--bag_name",
        type=str,
        required=not is_in_debug,
        help="Root folder of bags or bag name(directory)",
    )
    parser.add_argument("--fps", type=float, default=30.0, help="Frame per second")
    parser.add_argument(
        "--out_dir",
        type=str,
        default=None,
        help="Output directory. Default is the same directory as the raw bag dir.",
    )
    parser.add_argument(
        "--skip_exist", action="store_true", default=False, help="Skip existing files"
    )
    args = parser.parse_args()

    if inDebug():
        args.bag_name = (
            args.bag_name or "/workspaces/ros2bags/rosbag2_2024_09_05-16_04_14"
        )
        args.skip_exist = False
    print(f"args: {args}")

    l_files = detect_walk_file(args.bag_name, rematch=r".*metadata.yaml$")
    bag_files = []
    for bag in l_files:
        bag_folder = is_bag(bag)
        if bag_folder:
            bag_files.append(bag_folder)

    if len(bag_files) == 0:
        print("No bag files found.")
        return

    for bag_name in tqdm(bag_files):
        print(f"Processing bag file: {bag_name}")
        try:
            decode_video(bag_name, fps=args.fps, skip_exist=args.skip_exist,out_dir=args.out_dir)
        except Exception as e:
            print(e)


if __name__ == "__main__":
    main()
