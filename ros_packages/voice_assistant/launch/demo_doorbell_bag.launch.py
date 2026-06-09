from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    bag_path = LaunchConfiguration("bag_path")
    audio_topic = LaunchConfiguration("audio_topic")
    threshold = LaunchConfiguration("threshold")

    return LaunchDescription([
        DeclareLaunchArgument("bag_path", default_value=""),
        DeclareLaunchArgument("audio_topic", default_value="/audio_stream"),
        DeclareLaunchArgument("threshold", default_value="1000"),

        Node(
            package="voice_assistant",
            executable="voice_task_dispatcher",
            name="voice_task_dispatcher",
            output="screen",
        ),

        Node(
            package="voice_assistant",
            executable="voice_rule_engine",
            name="voice_rule_engine",
            output="screen",
        ),

        Node(
            package="voice_assistant",
            executable="doorbell_audio_stream_detector",
            name="doorbell_audio_stream_detector",
            output="screen",
            parameters=[{
                "audio_topic": audio_topic,
                "threshold": threshold,
            }],
        ),

        ExecuteProcess(
            cmd=["ros2", "bag", "play", bag_path],
            output="screen",
        ),
    ])