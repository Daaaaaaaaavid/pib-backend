import os
from glob import glob

from setuptools import find_packages, setup

package_name = "voice_assistant"

setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/voice_assistant"]),
        ("share/voice_assistant", ["package.xml"]),
        (
            os.path.join("share", "voice_assistant", "launch"),
            glob("launch/*.py"),
        ),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="pib",
    maintainer_email="pib@todo.todo",
    description="TODO: Package description",
    license="TODO: License declaration",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "assistant = voice_assistant.assistant:main",
            "chat = voice_assistant.chat:main",
            "audio_recorder = voice_assistant.audio_recorder:main",
            "audio_player = voice_assistant.audio_player:main",
            "token_service = voice_assistant.token_service:main",
            "demo_doorbell_detector = voice_assistant.demo_doorbell_detector:main",
            "voice_rule_engine = voice_assistant.voice_rule_engine:main",
            "voice_task_dispatcher = voice_assistant.voice_task_dispatcher:main",
            "doorbell_wav_detector = voice_assistant.doorbell_wav_detector:main",
            "doorbell_audio_stream_detector = voice_assistant.doorbell_audio_stream_detector:main",
            "listen_action_server = voice_assistant.listen_action_server:main",
            "doorbell_task_manager_demo = voice_assistant.doorbell_task_manager_demo:main",
        ],
    },
)
