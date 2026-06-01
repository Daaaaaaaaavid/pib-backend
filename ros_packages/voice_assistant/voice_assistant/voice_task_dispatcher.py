import json
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class VoiceTaskDispatcher(Node):
    def __init__(self):
        super().__init__("voice_task_dispatcher")

        self.subscription = self.create_subscription(
            String,
            "/voice/tasks",
            self.handle_task,
            10,
        )

        self.get_logger().info("[Dispatcher] Ready. Waiting for voice tasks.")

    def handle_task(self, msg: String):
        try:
            task = json.loads(msg.data)
        except json.JSONDecodeError:
            self.get_logger().error("[Dispatcher] Invalid task JSON")
            return

        task_type = task.get("task_type")

        self.get_logger().info(
            f"[Dispatcher] Submitted task to taskmanagement: {task_type}"
        )
        self.get_logger().info(f"[Dispatcher] Full task payload: {task}")


def main(args=None):
    rclpy.init(args=args)
    node = VoiceTaskDispatcher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()