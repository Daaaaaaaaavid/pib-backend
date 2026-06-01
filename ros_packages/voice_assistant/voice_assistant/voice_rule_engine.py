import json
import rclpy
from rclpy.node import Node
from datatypes.msg import VoiceEvent, VoiceTask

class VoiceRuleEngine(Node):
    def __init__(self):
        super().__init__("voice_rule_engine")

        self.subscription = self.create_subscription(
            VoiceEvent,
            "/voice/events",
            self.handle_event,
            10,
        )

        self.publisher = self.create_publisher(VoiceTask, "/voice/tasks", 10)

        self.get_logger().info("[RuleEngine] Ready. Waiting for voice events.")

    def handle_event(self, event: VoiceEvent):
        event_type = event.event_type

        if event_type == "doorbell_detected":
            task = VoiceTask()
            task.task_type = "handle_doorbell"
            task.priority = "high"
            task.source_event_type = event.event_type
            task.metadata_json = event.metadata_json

            self.publisher.publish(task)
            self.get_logger().info(f"[RuleEngine] Generated task: {task}")
        else:
            self.get_logger().warn(f"[RuleEngine] No rule for event_type: {event_type}")


def main(args=None):
    rclpy.init(args=args)
    node = VoiceRuleEngine()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()