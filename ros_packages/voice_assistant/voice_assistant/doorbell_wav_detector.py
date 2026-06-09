import audioop
import json
import wave

import numpy as np
import rclpy
from rclpy.node import Node

from datatypes.msg import VoiceEvent
from voice_assistant.yamnet_doorbell_classifier import YamnetDoorbellClassifier


class DoorbellWavDetector(Node):
    def __init__(self):
        super().__init__("doorbell_wav_detector")

        self.declare_parameter("wav_path", "")
        self.declare_parameter("doorbell_threshold", 0.30)
        self.declare_parameter("speech_max_threshold", 0.25)

        self.wav_path = self.get_parameter("wav_path").value
        self.publisher = self.create_publisher(VoiceEvent, "/voice/events", 10)

        self.classifier = YamnetDoorbellClassifier(
            doorbell_threshold=float(self.get_parameter("doorbell_threshold").value),
            speech_max_threshold=float(self.get_parameter("speech_max_threshold").value),
        )

        self.has_run = False
        self.timer = self.create_timer(1.0, self.detect_once)

        self.get_logger().info("[DoorbellWavDetector] Ready.")

    def detect_once(self):
        if self.has_run:
            return
        self.has_run = True

        if not self.wav_path:
            self.get_logger().error("Parameter wav_path is empty.")
            return

        waveform = self._load_wav_as_16khz_float(self.wav_path)
        result = self.classifier.classify(waveform)

        self.get_logger().info(f"YAMNet result: {result}")

        if not result["detected"]:
            self.get_logger().info("No doorbell detected.")
            return

        event = VoiceEvent()
        event.event_type = "doorbell_detected"
        event.confidence = result["doorbell_score"]
        event.source = "yamnet_wav_detector"
        event.metadata_json = json.dumps({
            **result,
            "wav_path": self.wav_path,
        })

        self.publisher.publish(event)
        self.get_logger().info("Published doorbell_detected event.")

    def _load_wav_as_16khz_float(self, path):
        with wave.open(path, "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()
            frames = wav_file.readframes(wav_file.getnframes())

        if channels > 1:
            frames = audioop.tomono(frames, sample_width, 0.5, 0.5)

        if sample_rate != 16000:
            frames, _ = audioop.ratecv(
                frames,
                sample_width,
                1,
                sample_rate,
                16000,
                None,
            )

        samples = np.frombuffer(frames, dtype=np.int16)
        return samples.astype(np.float32) / 32768.0


def main(args=None):
    rclpy.init(args=args)
    node = DoorbellWavDetector()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()