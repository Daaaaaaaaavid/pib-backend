import csv
import numpy as np
import tensorflow_hub as hub
import tensorflow as tf


class YamnetDoorbellClassifier:
    def __init__(self, doorbell_threshold=0.30, speech_max_threshold=0.25):
        self.model = hub.load("https://tfhub.dev/google/yamnet/1")
        self.doorbell_threshold = doorbell_threshold
        self.speech_max_threshold = speech_max_threshold

        class_map_path = self.model.class_map_path().numpy().decode("utf-8")
        self.class_names = self._load_class_names(class_map_path)

        self.doorbell_indices = self._find_indices(["Doorbell", "Ding-dong"])
        self.speech_indices = self._find_indices(["Speech", "Conversation", "Human voice"])

    def classify(self, waveform_16khz_float: np.ndarray) -> dict:
        scores, _, _ = self.model(waveform_16khz_float.astype(np.float32))
        mean_scores = scores.numpy().mean(axis=0)

        doorbell_score = self._max_score(mean_scores, self.doorbell_indices)
        speech_score = self._max_score(mean_scores, self.speech_indices)
        top_index = int(np.argmax(mean_scores))

        return {
            "detected": doorbell_score >= self.doorbell_threshold
            and speech_score <= self.speech_max_threshold,
            "doorbell_score": float(doorbell_score),
            "speech_score": float(speech_score),
            "top_class": self.class_names[top_index],
            "top_score": float(mean_scores[top_index]),
        }

    def _load_class_names(self, path):
        with tf.io.gfile.GFile(path) as csvfile:
            return [row["display_name"] for row in csv.DictReader(csvfile)]

    def _find_indices(self, names):
        return [
            i for i, class_name in enumerate(self.class_names)
            if any(name.lower() in class_name.lower() for name in names)
        ]

    def _max_score(self, scores, indices):
        return float(np.max(scores[indices])) if indices else 0.0