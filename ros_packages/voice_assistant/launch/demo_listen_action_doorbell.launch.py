from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    wav_path = LaunchConfiguration("wav_path")
    doorbell_threshold = LaunchConfiguration("doorbell_threshold")
    timeout_sec = LaunchConfiguration("timeout_sec")
    repeat = LaunchConfiguration("repeat")

    return LaunchDescription([
        DeclareLaunchArgument("wav_path", default_value=""),
        DeclareLaunchArgument("doorbell_threshold", default_value="0.30"),
        DeclareLaunchArgument("timeout_sec", default_value="30.0"),
        DeclareLaunchArgument("repeat", default_value="true"),

        Node(
            package="voice_assistant",
            executable="listen_action_server",
            name="voice_listen_action_server",
            output="screen",
            parameters=[{
                "wav_path": wav_path,
                "doorbell_threshold": doorbell_threshold,
                "timeout_sec": timeout_sec,
            }],
        ),

        Node(
            package="voice_assistant",
            executable="doorbell_task_manager_demo",
            name="doorbell_task_manager_demo",
            output="screen",
            parameters=[{
                "timeout_sec": timeout_sec,
                "repeat": repeat,
            }],
        ),
    ])