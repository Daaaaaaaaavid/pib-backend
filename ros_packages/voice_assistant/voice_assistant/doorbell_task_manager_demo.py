import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from datatypes.action import Listen


class DoorbellTaskManagerDemo(Node):
    def __init__(self):
        super().__init__("doorbell_task_manager_demo")

        GREEN = "\033[92m"
        RED = "\033[91m"
        RESET = "\033[0m"

        self.declare_parameter("action_name", "/audio/listen")
        self.declare_parameter("timeout_sec", 30.0)
        self.declare_parameter("repeat", True)

        action_name = self.get_parameter("action_name").value
        self.timeout_sec = float(self.get_parameter("timeout_sec").value)
        self.repeat = bool(self.get_parameter("repeat").value)

        self.client = ActionClient(self, Listen, action_name)
        self.timer = self.create_timer(1.0, self.start_once)
        self.running = False

        self.get_logger().info("[TaskManagerDemo] Waiting for listen action server...")

    def start_once(self):
        if self.running:
            return

        if not self.client.wait_for_server(timeout_sec=0.1):
            return

        self.running = True
        self.timer.cancel()

        goal = Listen.Goal()
        goal.mode = Listen.Goal.MODE_DOORBELL
        goal.timeout_sec = self.timeout_sec

        self.get_logger().info("[TaskManagerDemo] Listening for doorbell...")

        future = self.client.send_goal_async(
            goal,
            feedback_callback=self.feedback_callback,
        )
        future.add_done_callback(self.goal_response_callback)

    def feedback_callback(self, feedback_msg):
        self.get_logger().info(
            f"[TaskManagerDemo] listen state: {feedback_msg.feedback.state}"
        )

    def goal_response_callback(self, future):
        goal_handle = future.result()

        if not goal_handle.accepted:
            self.get_logger().error("[TaskManagerDemo] Listen goal rejected")
            rclpy.shutdown()
            return

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.result_callback)

    def result_callback(self, future):
        result = future.result().result

        if result.detected:
            self.get_logger().info(
                f"\033[1;92m"
                f"✓ DOORBELL DETECTED (confidence={result.confidence:.3f})"
                f"\033[0m"
            )
        else:
            self.get_logger().info(
                f"\033[1;91m"
                f"✗ NO DOORBELL DETECTED (confidence={result.confidence:.3f})"
                f"\033[0m"
            )

        if self.repeat:
            self.running = False
            self.timer = self.create_timer(1.0, self.start_once)
        else:
            rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = DoorbellTaskManagerDemo()

    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()