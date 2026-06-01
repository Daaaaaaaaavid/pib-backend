import json
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class DemoDoorbellDetector(Node):
    def __init__(self):
        super().__init__("demo_doorbell_detector")
        self.publisher = self.create_publisher(String, "/voice/events", 10)
        self.timer = self.create_timer(3.0, self.publish_doorbell_event)
        self.published = False

    def publish_doorbell_event(self):
        if self.published:
            return

        event = {
            "event_type": "doorbell_detected",
            "confidence": 0.95,
            "source": "demo_sound_classifier",
        }

        self.publisher.publish(String(data=json.dumps(event)))
        self.get_logger().info(f"[DemoDetector] Published event: {event}")
        self.published = True


def main(args=None):
    rclpy.init(args=args)
    node = DemoDoorbellDetector()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()