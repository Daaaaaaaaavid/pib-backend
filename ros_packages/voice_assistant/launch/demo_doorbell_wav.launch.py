from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    wav_path = LaunchConfiguration("wav_path")
    doorbell_threshold = LaunchConfiguration("doorbell_threshold")
    speech_max_threshold = LaunchConfiguration("speech_max_threshold")

    return LaunchDescription([
        DeclareLaunchArgument("wav_path", default_value=""),
        DeclareLaunchArgument("doorbell_threshold", default_value="0.30"),
        DeclareLaunchArgument("speech_max_threshold", default_value="0.25"),

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
            executable="doorbell_wav_detector",
            name="doorbell_wav_detector",
            output="screen",
            parameters=[{
                "wav_path": wav_path,
                "doorbell_threshold": doorbell_threshold,
                "speech_max_threshold": speech_max_threshold,
            }],
        ),
    ])