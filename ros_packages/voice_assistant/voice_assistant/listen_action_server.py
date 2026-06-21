# Startet einen ros2 Action Server
# Nimmt ein Goal mit Mode für Speech oder Doorbell + timeout von einem Client entgegen
#     für Doorbell: MODE_DOORBELL=1
#     Speech ist noch nicht implementiert
# Hört bis zum timeout entweder auf .wav file oder oder über pyAudio auf das Mikro
# returned werden detected, confidence, transscript
# transscript ist im Fall einer Doorbell einfach leer

import time
import wave
from dataclasses import dataclass
from typing import Optional

import numpy as np
import rclpy
from datatypes.action import Listen
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.node import Node

from voice_assistant.yamnet_doorbell_classifier import YamnetDoorbellClassifier


@dataclass
class DetectionState:
    detected: bool = False
    confidence: float = 0.0
    top_class: str = ""
    speech_score: float = 0.0


class ListenActionServer(Node):
    def __init__(self) -> None:
        super().__init__("voice_listen_action_server")

        self.declare_parameter("action_name", "/audio/listen")
        self.declare_parameter("doorbell_threshold", 0.30)
        self.declare_parameter("speech_max_threshold", 0.25)
        self.declare_parameter("timeout_sec", 5.0)
        self.declare_parameter("wav_path", "")
        self.declare_parameter("sample_rate", 16000)
        self.declare_parameter("chunk_size", 16000)

        action_name = self.get_parameter("action_name").value

        doorbell_threshold = float(self.get_parameter("doorbell_threshold").value)
        speech_max_threshold = float(self.get_parameter("speech_max_threshold").value)

        self.get_logger().info("[ListenAction] Loading YAMNet model...")

        # lädt bei start das Modell einmal 
        self.classifier = YamnetDoorbellClassifier(
            doorbell_threshold=doorbell_threshold,
            speech_max_threshold=speech_max_threshold,
        )

        self.get_logger().info("[ListenAction] YAMNet model loaded")

        # ros registriert die Action
        self._server = ActionServer(
            self,
            Listen,
            action_name,
            execute_callback=self.execute_callback,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback,
        )

        self.get_logger().info(f"[ListenAction] Ready on {action_name}")

    # checkt ob das Goal angenommen werden darf/kann, aktuell nur doorbell mode
    def goal_callback(self, goal_request: Listen.Goal) -> GoalResponse:
        if goal_request.mode != Listen.Goal.MODE_DOORBELL:
            self.get_logger().warn(
                f"Rejecting listen goal: mode={goal_request.mode} is not implemented yet"
            )
            return GoalResponse.REJECT

        return GoalResponse.ACCEPT

    # erlaubt einem laufenden Auftrag abgebrochen zu werden
    def cancel_callback(self, _goal_handle) -> CancelResponse:
        return CancelResponse.ACCEPT


    # führt den das Goal aus wenn es angenommen wurde
    # entscheidet ob aus wav oder mikro gelesen wird
    # und baut roos result
    # published listening als feedback
    def execute_callback(self, goal_handle) -> Listen.Result:
        default_timeout = float(self.get_parameter("timeout_sec").value)
        timeout_sec = float(goal_handle.request.timeout_sec or default_timeout)
        wav_path = str(self.get_parameter("wav_path").value or "")

        self.get_logger().info(
            f"[ListenAction] Listening for doorbell with YAMNet: "
            f"timeout={timeout_sec:.1f}s"
        )

        self._publish_feedback(goal_handle, "listening")

        started_at = time.monotonic()

        if wav_path:
            state = self._detect_doorbell_from_wav(
                wav_path,
                timeout_sec,
                goal_handle,
                started_at,
            )
        else:
            state = self._detect_doorbell_from_microphone(
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
            f"detected={result.detected} "
            f"confidence={result.confidence:.3f} "
            f"top_class={state.top_class} "
            f"speech_score={state.speech_score:.3f}"
        )

        return result

    # liest ein wav file ein
    def _detect_doorbell_from_wav(
        self,
        wav_path: str,
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

                    waveform = self._pcm_to_float_mono(
                        raw,
                        sample_width,
                        channels,
                    )

                    if waveform.size == 0:
                        continue

                    classification = self.classifier.classify(waveform)

                    doorbell_score = float(classification["doorbell_score"])
                    speech_score = float(classification["speech_score"])
                    top_class = str(classification["top_class"])

                    state.confidence = max(state.confidence, doorbell_score)
                    state.speech_score = speech_score
                    state.top_class = top_class

                    self.get_logger().info(
                        f"[ListenAction] YAMNet: "
                        f"doorbell_score={doorbell_score:.3f} "
                        f"speech_score={speech_score:.3f} "
                        f"top_class={top_class}"
                    )

                    if classification["detected"]:
                        state.detected = True
                        return state

                    time.sleep(frames_per_chunk / max(sample_rate, 1))

        except Exception as exc:
            self.get_logger().error(f"Could not analyse wav_path={wav_path}: {exc}")
            return state

    # ließt audio vom mikro in einer Schleife über pyaudio ein ein 
    def _detect_doorbell_from_microphone(
        self,
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

                waveform = self._pcm_to_float_mono(
                    raw,
                    sample_width=2,
                    channels=1,
                )

                if waveform.size == 0:
                    continue

                classification = self.classifier.classify(waveform)

                doorbell_score = float(classification["doorbell_score"])
                speech_score = float(classification["speech_score"])
                top_class = str(classification["top_class"])

                state.confidence = max(state.confidence, doorbell_score)
                state.speech_score = speech_score
                state.top_class = top_class

                self.get_logger().info(
                    f"[ListenAction] YAMNet: "
                    f"doorbell_score={doorbell_score:.3f} "
                    f"speech_score={speech_score:.3f} "
                    f"top_class={top_class}"
                )

                if classification["detected"]:
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

    # verwandel die Audiodaten in floatdaten damit sie von yamnet verarbeitet werden können
    def _pcm_to_float_mono(
        self,
        raw: bytes,
        sample_width: int,
        channels: int,
    ) -> np.ndarray:
        if sample_width != 2:
            self.get_logger().warn(
                "Only 16-bit PCM audio is supported for YAMNet detection"
            )
            return np.array([], dtype=np.float32)

        samples = np.frombuffer(raw, dtype=np.int16)

        if samples.size == 0:
            return np.array([], dtype=np.float32)

        if channels > 1:
            samples = samples.reshape(-1, channels).mean(axis=1)

        return samples.astype(np.float32) / 32768.0

    # schickt feedback an den client
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