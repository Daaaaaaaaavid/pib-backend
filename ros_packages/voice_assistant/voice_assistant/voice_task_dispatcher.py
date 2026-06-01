import json
import rclpy
from rclpy.node import Node
from datatypes.msg import VoiceTask


class VoiceTaskDispatcher(Node):
    def __init__(self):
        super().__init__("voice_task_dispatcher")

        self.subscription = self.create_subscription(
            VoiceTask,
            "/voice/tasks",
            self.handle_task,
            10,
        )

        self.get_logger().info("[Dispatcher] Ready. Waiting for voice tasks.")

    def handle_task(self, task: VoiceTask):
        self.get_logger().info(
            f"[Dispatcher] Submitted task to taskmanagement: {task.task_type}"
        )
        self.get_logger().info(
            f"[Dispatcher] priority={task.priority}, source_event={task.source_event_type}, metadata={task.metadata_json}"
        )


def main(args=None):
    rclpy.init(args=args)
    node = VoiceTaskDispatcher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()