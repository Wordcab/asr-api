# Copyright 2023 The Wordcab Team. All rights reserved.
#
# Licensed under the Wordcab Transcribe License 0.1 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://github.com/Wordcab/wordcab-transcribe/blob/main/LICENSE
#
# Except as expressly provided otherwise herein, and to the fullest
# extent permitted by law, Licensor provides the Software (and each
# Contributor provides its Contributions) AS IS, and Licensor
# disclaims all warranties or guarantees of any kind, express or
# implied, whether arising under any law or from any usage in trade,
# or otherwise including but not limited to the implied warranties
# of merchantability, non-infringement, quiet enjoyment, fitness
# for a particular purpose, or otherwise.
#
# See the License for the specific language governing permissions
# and limitations under the License.
"""Diarization Service for audio files."""

from typing import List, NamedTuple, Tuple

import torch

from wordcab_transcribe.services.diarization.clustering_module import ClusteringModule
from wordcab_transcribe.services.diarization.models import (
    MultiscaleEmbeddingsAndTimestamps,
)
from wordcab_transcribe.services.diarization.segmentation_module import (
    SegmentationModule,
)
from wordcab_transcribe.services.vad_service import VadService


class DiarizationModels(NamedTuple):
    """Diarization Models."""

    segmentation: SegmentationModule
    clustering: ClusteringModule
    device: str


class DiarizeService:
    """Diarize Service for audio files."""

    def __init__(
        self,
        device: str,
        device_index: List[int],
        window_lengths: List[float],
        shift_lengths: List[float],
        multiscale_weights: List[int],
        max_num_speakers: int = 8,
    ) -> None:
        """Initialize the Diarize Service.

        This service uses the NVIDIA NeMo diarization models.

        Args:
            device (str): Device to use for inference. Can be "cpu" or "cuda".
            device_index (Union[int, List[int]]): Index of the device to use for inference.
            window_lengths (List[float]): List of window lengths.
            shift_lengths (List[float]): List of shift lengths.
            multiscale_weights (List[int]): List of weights for each scale.
            max_num_speakers (int): Maximum number of speakers. Defaults to 8.
        """
        self.device = device
        self.models = {}

        self.max_num_speakers = max_num_speakers
        self.default_window_lengths = window_lengths
        self.default_shift_lengths = shift_lengths
        self.default_multiscale_weights = multiscale_weights

        if len(self.default_multiscale_weights) > 3:
            self.default_segmentation_batch_size = 64
        elif len(self.default_multiscale_weights) > 1:
            self.default_segmentation_batch_size = 128
        else:
            self.default_segmentation_batch_size = 256

        self.default_scale_dict = {
            k: (w, s)
            for k, (w, s) in enumerate(zip(window_lengths, shift_lengths, strict=True))
        }

        for idx in device_index:
            _device = f"cuda:{idx}" if self.device == "cuda" else "cpu"

            segmentation_module = SegmentationModule(_device)
            clustering_module = ClusteringModule(_device, self.max_num_speakers)

            self.models[idx] = DiarizationModels(
                segmentation=segmentation_module,
                clustering=clustering_module,
                device=_device,
            )

    def __call__(
        self,
        waveform: torch.Tensor,
        audio_duration: float,
        oracle_num_speakers: int,
        model_index: int,
        vad_service: VadService,
    ) -> List[dict]:
        """
        Run inference with the diarization model.

        Args:
            waveform (torch.Tensor): Waveform to run inference on.
            audio_duration (float): Duration of the audio file in seconds.
            oracle_num_speakers (int): Number of speakers in the audio file.
            model_index (int): Index of the model to use for inference.
            vad_service (VadService): VAD service instance to use for Voice Activity Detection.

        Returns:
            List[dict]: List of segments with the following keys: "start", "end", "speaker".
        """
        vad_outputs, _ = vad_service(waveform, group_timestamps=False)

        if len(vad_outputs) == 0:  # Empty audio
            return None

        if audio_duration < 3600:
            scale_dict = self.default_scale_dict
            segmentation_batch_size = self.default_segmentation_batch_size
            multiscale_weights = self.default_multiscale_weights
        elif audio_duration < 10800:
            scale_dict = {
                k: (w, s)
                for k, (w, s) in enumerate(
                    zip(
                        [3.0, 2.5, 2.0, 1.5, 1.0],
                        self.default_shift_lengths,
                        strict=True,
                    )
                )
            }
            segmentation_batch_size = 64
            multiscale_weights = self.default_multiscale_weights
        else:
            scale_dict = {
                k: (w, s)
                for k, (w, s) in enumerate(
                    zip([3.0, 2.0, 1.0], [0.75, 0.5, 0.25], strict=True)
                )
            }
            segmentation_batch_size = 32
            multiscale_weights = [1.0, 1.0, 1.0]

        ms_emb_ts: MultiscaleEmbeddingsAndTimestamps = self.models[
            model_index
        ].segmentation(
            waveform=waveform,
            batch_size=segmentation_batch_size,
            vad_outputs=vad_outputs,
            scale_dict=scale_dict,
            multiscale_weights=multiscale_weights,
        )

        clustering_outputs = self.models[model_index].clustering(
            ms_emb_ts, oracle_num_speakers
        )

        _outputs = self.get_contiguous_stamps(clustering_outputs)
        outputs = self.merge_stamps(_outputs)

        return outputs

    @staticmethod
    def get_contiguous_stamps(
        stamps: List[Tuple[float, float, int]]
    ) -> List[Tuple[float, float, int]]:
        """
        Return contiguous timestamps.

        Args:
            stamps (List[Tuple[float, float, int]]): List of segments containing the start time, end time and speaker.

        Returns:
            List[Tuple[float, float, int]]: List of segments containing the start time, end time and speaker.
        """
        contiguous_stamps = []
        for i in range(len(stamps) - 1):
            start, end, speaker = stamps[i]
            next_start, next_end, next_speaker = stamps[i + 1]

            if end > next_start:
                avg = (next_start + end) / 2.0
                stamps[i + 1] = (avg, next_end, next_speaker)
                contiguous_stamps.append((start, avg, speaker))
            else:
                contiguous_stamps.append((start, end, speaker))

        start, end, speaker = stamps[-1]
        contiguous_stamps.append((start, end, speaker))

        return contiguous_stamps

    @staticmethod
    def merge_stamps(
        stamps: List[Tuple[float, float, int]]
    ) -> List[Tuple[float, float, int]]:
        """
        Merge timestamps of the same speaker.

        Args:
            stamps (List[Tuple[float, float, int]]): List of segments containing the start time, end time and speaker.

        Returns:
            List[Tuple[float, float, int]]: List of segments containing the start time, end time and speaker.
        """
        overlap_stamps = []
        for i in range(len(stamps) - 1):
            start, end, speaker = stamps[i]
            next_start, next_end, next_speaker = stamps[i + 1]

            if end == next_start and speaker == next_speaker:
                stamps[i + 1] = (start, next_end, next_speaker)
            else:
                overlap_stamps.append((start, end, speaker))

        start, end, speaker = stamps[-1]
        overlap_stamps.append((start, end, speaker))

        return overlap_stamps
