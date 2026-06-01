import json
import wave
import audioop

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class DoorbellWavDetector(Node):
    def __init__(self):
        super().__init__("doorbell_wav_detector")

        self.declare_parameter("wav_path", "")
        self.declare_parameter("threshold", 1000)

        self.wav_path = self.get_parameter("wav_path").value
        self.threshold = self.get_parameter("threshold").value

        self.publisher = self.create_publisher(String, "/voice/events", 10)

        self.timer = self.create_timer(1.0, self.analyze_wav_once)
        self.has_run = False

        self.get_logger().info("[WavDetector] Ready.")

    def analyze_wav_once(self):
        if self.has_run:
            return

        self.has_run = True

        if not self.wav_path:
            self.get_logger().error("[WavDetector] No wav_path parameter given.")
            return

        try:
            with wave.open(self.wav_path, "rb") as wav_file:
                sample_width = wav_file.getsampwidth()
                frames = wav_file.readframes(wav_file.getnframes())
                rms = audioop.rms(frames, sample_width)

        except Exception as e:
            self.get_logger().error(f"[WavDetector] Failed to read WAV: {e}")
            return

        self.get_logger().info(f"[WavDetector] WAV RMS volume: {rms}")

        if rms >= self.threshold:
            event = {
                "event_type": "doorbell_detected",
                "confidence": 0.90,
                "source": "wav_threshold_detector",
                "rms": rms,
                "threshold": self.threshold,
                "wav_path": self.wav_path,
            }

            self.publisher.publish(String(data=json.dumps(event)))
            self.get_logger().info(f"[WavDetector] Published event: {event}")
        else:
            self.get_logger().info("[WavDetector] No doorbell detected.")


def main(args=None):
    rclpy.init(args=args)
    node = DoorbellWavDetector()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()