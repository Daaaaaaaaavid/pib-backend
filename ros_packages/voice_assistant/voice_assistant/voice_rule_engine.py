import json
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class VoiceRuleEngine(Node):
    def __init__(self):
        super().__init__("voice_rule_engine")

        self.subscription = self.create_subscription(
            String,
            "/voice/events",
            self.handle_event,
            10,
        )

        self.publisher = self.create_publisher(String, "/voice/tasks", 10)

        self.get_logger().info("[RuleEngine] Ready. Waiting for voice events.")

    def handle_event(self, msg: String):
        try:
            event = json.loads(msg.data)
        except json.JSONDecodeError:
            self.get_logger().error("[RuleEngine] Invalid event JSON")
            return

        event_type = event.get("event_type")

        if event_type == "doorbell_detected":
            task = {
                "task_type": "handle_doorbell",
                "priority": "high",
                "source_event": event,
            }

            self.publisher.publish(String(data=json.dumps(task)))
            self.get_logger().info(f"[RuleEngine] Generated task: {task}")
        else:
            self.get_logger().warn(f"[RuleEngine] No rule for event_type: {event_type}")


def main(args=None):
    rclpy.init(args=args)
    node = VoiceRuleEngine()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()