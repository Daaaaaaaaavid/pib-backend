import math
import time
import wave
from dataclasses import dataclass
from typing import Optional

import numpy as np
import rclpy
from datatypes.action import Listen
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.node import Node


@dataclass
class DetectionState:
    detected: bool = False
    confidence: float = 0.0


class ListenActionServer(Node):
    def __init__(self) -> None:
        super().__init__("voice_listen_action_server")

        self.declare_parameter("action_name", "/audio/listen")
        self.declare_parameter("doorbell_threshold", 0.30)
        self.declare_parameter("timeout_sec", 5.0)
        self.declare_parameter("wav_path", "")
        self.declare_parameter("sample_rate", 16000)
        self.declare_parameter("chunk_size", 2048)

        action_name = self.get_parameter("action_name").value

        self._server = ActionServer(
            self,
            Listen,
            action_name,
            execute_callback=self.execute_callback,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback,
        )

        self.get_logger().info(f"[ListenAction] Ready on {action_name}")

    def goal_callback(self, goal_request: Listen.Goal) -> GoalResponse:
        if goal_request.mode != Listen.Goal.MODE_DOORBELL:
            self.get_logger().warn(
                f"Rejecting listen goal: mode={goal_request.mode} is not implemented yet"
            )
            return GoalResponse.REJECT

        return GoalResponse.ACCEPT

    def cancel_callback(self, _goal_handle) -> CancelResponse:
        return CancelResponse.ACCEPT

    def execute_callback(self, goal_handle) -> Listen.Result:
        threshold = float(self.get_parameter("doorbell_threshold").value)
        default_timeout = float(self.get_parameter("timeout_sec").value)
        timeout_sec = float(goal_handle.request.timeout_sec or default_timeout)
        wav_path = str(self.get_parameter("wav_path").value or "")

        self.get_logger().info(
            f"[ListenAction] Listening for doorbell: "
            f"timeout={timeout_sec:.1f}s threshold={threshold:.2f}"
        )

        self._publish_feedback(goal_handle, "listening")

        started_at = time.monotonic()

        if wav_path:
            state = self._detect_doorbell_from_wav(
                wav_path,
                threshold,
                timeout_sec,
                goal_handle,
                started_at,
            )
        else:
            state = self._detect_doorbell_from_microphone(
                threshold,
                timeout_sec,
                goal_handle,
                started_at,
            )

        result = Listen.Result()
        result.detected = state.detected
        result.confidence = float(state.confidence)
        result.transcript = ""

        if goal_handle.is_cancel_requested:
            self._publish_feedback(goal_handle, "cancelled")
            goal_handle.canceled()
            return result

        if state.detected:
            self._publish_feedback(goal_handle, "doorbell_detected")
        else:
            self._publish_feedback(goal_handle, "timeout")

        goal_handle.succeed()

        self.get_logger().info(
            f"[ListenAction] Finished: "
            f"detected={result.detected} confidence={result.confidence:.3f}"
        )

        return result

    def _detect_doorbell_from_wav(
        self,
        wav_path: str,
        threshold: float,
        timeout_sec: float,
        goal_handle,
        started_at: float,
    ) -> DetectionState:
        state = DetectionState()

        try:
            with wave.open(wav_path, "rb") as wav:
                sample_rate = wav.getframerate()
                channels = wav.getnchannels()
                sample_width = wav.getsampwidth()
                frames_per_chunk = int(self.get_parameter("chunk_size").value)

                while True:
                    if goal_handle.is_cancel_requested:
                        return state

                    if time.monotonic() - started_at >= timeout_sec:
                        return state

                    raw = wav.readframes(frames_per_chunk)

                    if not raw:
                        return state

                    confidence = self._confidence_from_pcm(
                        raw,
                        sample_width,
                        channels,
                    )

                    state.confidence = max(state.confidence, confidence)

                    if confidence >= threshold:
                        state.detected = True
                        return state

                    time.sleep(frames_per_chunk / max(sample_rate, 1))

        except Exception as exc:
            self.get_logger().error(f"Could not analyse wav_path={wav_path}: {exc}")
            return state

    def _detect_doorbell_from_microphone(
        self,
        threshold: float,
        timeout_sec: float,
        goal_handle,
        started_at: float,
    ) -> DetectionState:
        state = DetectionState()

        try:
            import pyaudio
        except ImportError:
            self.get_logger().error("pyaudio is required for microphone listening")
            return state

        sample_rate = int(self.get_parameter("sample_rate").value)
        chunk_size = int(self.get_parameter("chunk_size").value)

        audio = pyaudio.PyAudio()
        stream: Optional[object] = None

        try:
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=sample_rate,
                input=True,
                frames_per_buffer=chunk_size,
            )

            while True:
                if goal_handle.is_cancel_requested:
                    return state

                if time.monotonic() - started_at >= timeout_sec:
                    return state

                raw = stream.read(chunk_size, exception_on_overflow=False)

                confidence = self._confidence_from_pcm(
                    raw,
                    sample_width=2,
                    channels=1,
                )

                state.confidence = max(state.confidence, confidence)

                if confidence >= threshold:
                    state.detected = True
                    return state

        except Exception as exc:
            self.get_logger().error(f"Microphone listen failed: {exc}")
            return state

        finally:
            if stream is not None:
                stream.stop_stream()
                stream.close()

            audio.terminate()

    def _confidence_from_pcm(
        self,
        raw: bytes,
        sample_width: int,
        channels: int,
    ) -> float:
        if sample_width != 2:
            self.get_logger().warn(
                "Only 16-bit PCM WAV is calibrated for doorbell detection"
            )
            return 0.0

        samples = np.frombuffer(raw, dtype=np.int16)

        if samples.size == 0:
            return 0.0

        if channels > 1:
            samples = samples.reshape(-1, channels).mean(axis=1)

        normalized = samples.astype(np.float32) / 32768.0

        rms = math.sqrt(float(np.mean(np.square(normalized))))
        peak = float(np.max(np.abs(normalized)))

        confidence = 0.65 * rms + 0.35 * peak

        return max(0.0, min(1.0, confidence))

    def _publish_feedback(self, goal_handle, state: str) -> None:
        feedback = Listen.Feedback()
        feedback.state = state
        goal_handle.publish_feedback(feedback)


def main(args=None) -> None:
    rclpy.init(args=args)

    node = ListenActionServer()

    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()