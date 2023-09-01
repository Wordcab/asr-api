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
"""Utils module of the Wordcab Transcribe."""
import asyncio
import math
import re
import subprocess  # noqa: S404
import sys
from pathlib import Path
from typing import Awaitable, Dict, List, Optional, Tuple, Union

import aiofiles
import aiohttp
import huggingface_hub
import pandas as pd
import torch
import torchaudio
from fastapi import UploadFile
from loguru import logger
from yt_dlp import YoutubeDL


# pragma: no cover
async def async_run_subprocess(command: List[str]) -> tuple:
    """
    Run a subprocess asynchronously.

    Args:
        command (List[str]): Command to run.

    Returns:
        tuple: Tuple with the return code, stdout and stderr.
    """
    process = await asyncio.create_subprocess_exec(
        *command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    return process.returncode, stdout, stderr


# pragma: no cover
def run_subprocess(command: List[str]) -> tuple:
    """
    Run a subprocess synchronously.

    Args:
        command (List[str]): Command to run.

    Returns:
        tuple: Tuple with the return code, stdout and stderr.
    """
    process = subprocess.Popen(  # noqa: S603,S607
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    stdout, stderr = process.communicate()

    return process.returncode, stdout, stderr


def check_ffmpeg() -> bool:
    """Check if ffmpeg is installed and available on the system."""
    try:
        result = run_subprocess(["ffmpeg", "-version"])

        if result[0] != 0:
            raise subprocess.CalledProcessError(result[0], "ffmpeg")

        return True
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,  # noqa: S404
    ):
        return False


def check_number_of_segments(chunk_size: int, duration: Union[int, float]) -> int:
    """
    Check the number of chunks considering the duration of the audio.

    Args:
        chunk_size (int): Size of each chunk.
        duration (Union[int, float]): Duration of the audio in milliseconds.

    Returns:
        int: Number of chunks after ceil the division of the duration by the chunk size.
    """
    _duration = _convert_ms_to_s(duration)

    return math.ceil(_duration / chunk_size)


def convert_timestamp(
    timestamp: float, target: str, round_digits: Optional[int] = 3
) -> Union[str, float]:
    """
    Use the right function to convert the timestamp.

    Args:
        timestamp (float): Timestamp to convert.
        target (str): Timestamp to convert.
        round_digits (int, optional): Number of digits to round the timestamp. Defaults to 3.

    Returns:
        Union[str, float]: Converted timestamp.

    Raises:
        ValueError: If the target is invalid. Valid targets are: ms, hms, s.
    """
    if target == "ms":
        return round(_convert_s_to_ms(timestamp), round_digits)
    elif target == "hms":
        return _convert_s_to_hms(timestamp)
    elif target == "s":
        return round(timestamp, round_digits)
    else:
        raise ValueError(
            f"Invalid conversion target: {target}. Valid targets are: ms, hms, s."
        )


def _convert_ms_to_hms(timestamp: float) -> str:
    """
    Convert a timestamp from milliseconds to hours, minutes and seconds.

    Args:
        timestamp (float): Timestamp in milliseconds to convert.

    Returns:
        str: Hours, minutes and seconds.
    """
    hours, remainder = divmod(timestamp / 1000, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = math.floor((seconds % 1) * 1000)

    output = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}.{milliseconds:03}"

    return output


def _convert_ms_to_s(timestamp: float) -> float:
    """
    Convert a timestamp from milliseconds to seconds.

    Args:
        timestamp (float): Timestamp in milliseconds to convert.

    Returns:
        float: Seconds.
    """
    return timestamp / 1000


def _convert_s_to_ms(timestamp: float) -> float:
    """
    Convert a timestamp from seconds to milliseconds.

    Args:
        timestamp (float): Timestamp in seconds to convert.

    Returns:
        float: Milliseconds.
    """
    return timestamp * 1000


def _convert_s_to_hms(timestamp: float) -> str:
    """
    Convert a timestamp from seconds to hours, minutes and seconds.

    Args:
        timestamp (float): Timestamp in seconds to convert.

    Returns:
        str: Hours, minutes and seconds.
    """
    hours, remainder = divmod(timestamp, 3600)
    minutes, seconds = divmod(remainder, 60)

    output = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}.000"

    return output


async def convert_file_to_wav(filepath: str) -> str:
    """
    Convert a file to wav format using ffmpeg.

    Args:
        filepath (str): Path to the file to convert.

    Raises:
        FileNotFoundError: If the file does not exist.
        Exception: If there is an error converting the file.

    Returns:
        str: Path to the converted file.
    """
    if isinstance(filepath, str):
        _filepath = Path(filepath)

    if not _filepath.exists():
        raise FileNotFoundError(f"File {filepath} does not exist.")

    new_filepath = f"{_filepath.stem}_{_filepath.stat().st_mtime_ns}.wav"
    cmd = [
        "ffmpeg",
        "-i",
        filepath,
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        "-y",
        new_filepath,
    ]
    result = await async_run_subprocess(cmd)

    if result[0] != 0:
        raise Exception(f"Error converting file {filepath} to wav format: {result[2]}")

    return new_filepath


# pragma: no cover
async def download_audio_file(
    source: str,
    url: str,
    filename: str,
    url_headers: Optional[Dict[str, str]] = None,
) -> Union[str, Awaitable[str]]:
    """
    Download an audio file from a URL.

    Args:
        source (str): Source of the audio file. Can be "youtube" or "url".
        url (str): URL of the audio file.
        filename (str): Filename to save the file as.
        url_headers (Optional[Dict[str, str]]): Headers to send with the request. Defaults to None.

    Raises:
        ValueError: If the source is invalid. Valid sources are: youtube, url.

    Returns:
        Union[str, Awaitable[str]]: Path to the downloaded file.
    """
    if source == "youtube":
        filename = await asyncio.get_running_loop().run_in_executor(
            None, _download_file_from_youtube, url, filename
        )
    elif source == "url":
        filename = await _download_file_from_url(url, filename, url_headers)
    else:
        raise ValueError(f"Invalid source: {source}. Valid sources are: youtube, url.")

    return filename


# pragma: no cover
def _download_file_from_youtube(url: str, filename: str) -> str:
    """
    Download a file from YouTube using youtube-dl.

    Args:
        url (str): URL of the YouTube video.
        filename (str): Filename to save the file as.

    Returns:
        str: Path to the downloaded file.
    """
    with YoutubeDL(
        {
            "format": "bestaudio",
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}],
            "outtmpl": f"{filename}",
        }
    ) as ydl:
        ydl.download([url])

    return filename + ".wav"


# pragma: no cover
async def _download_file_from_url(
    url: str,
    filename: str,
    url_headers: Optional[Dict[str, str]] = None,
) -> str:
    """
    Download a file from a URL using aiohttp.

    Args:
        url (str): URL of the audio file.
        filename (str): Filename to save the file as.
        url_headers (Optional[Dict[str, str]]): Headers to send with the request. Defaults to None.

    Returns:
        str: Path to the downloaded file.

    Raises:
        Exception: If the file failed to download.
    """
    url_headers = url_headers or {}

    logger.info(f"Downloading audio file from {url} to {filename}...")
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=url_headers) as response:
            if response.status == 200:
                async with aiofiles.open(filename, "wb") as f:
                    while True:
                        chunk = await response.content.read(1024)

                        if not chunk:
                            break

                        await f.write(chunk)
            else:
                raise Exception(f"Failed to download file. Status: {response.status}")

    return filename


# pragma: no cover
def download_model(compute_type: str, language: str) -> Optional[str]:
    """
    Download the special models during the warmup phase.

    Args:
        compute_type (str): The target compute type.
        language (str): The target language.

    Returns:
        Optional[str]: The path to the downloaded model.
    """
    if compute_type == "float16":
        repo_id = f"wordcab/whisper-large-fp16-{language}"
    elif compute_type == "int8_float16":
        repo_id = f"wordcab/whisper-large-int8-fp16-{language}"
    elif compute_type == "int8":
        repo_id = f"wordcab/whisper-large-int8-{language}"
    else:
        # No other models are supported
        return None

    allow_patterns = ["config.json", "model.bin", "tokenizer.json", "vocabulary.*"]
    snapshot_path = huggingface_hub.snapshot_download(
        repo_id, local_files_only=False, allow_patterns=allow_patterns
    )

    return snapshot_path


def delete_file(filepath: Union[str, Tuple[str, Optional[str]]]) -> None:
    """
    Delete a file or a list of files.

    Args:
        filepath (Union[str, Tuple[str]]): Path to the file to delete.
    """
    if isinstance(filepath, str):
        filepath = (filepath, None)

    for path in filepath:
        if path:
            Path(path).unlink(missing_ok=True)


def early_return(duration: float) -> Tuple[List[dict], dict, float]:
    """
    Early return for empty audio files.

    Args:
        duration (float): Duration of the audio file.

    Returns:
        Tuple[List[dict], dict, float]:
            Empty segments, process times and audio duration.
    """
    return (
        [
            {
                "text": "<EMPTY AUDIO>",
                "start": 0,
                "end": duration,
                "speaker": None,
                "words": None,
            }
        ],
        {
            "total": 0,
            "transcription": 0,
            "diarization": None,
            "post_processing": 0,
        },
        duration,
    )


def enhance_audio(
    audio: Union[str, torch.Tensor],
    apply_agc: Optional[bool] = True,
    apply_bandpass: Optional[bool] = False,
) -> torch.Tensor:
    """
    Enhance the audio by applying automatic gain control and bandpass filter.

    Args:
        audio (Union[str, torch.Tensor]): Path to the audio file or the waveform.
        apply_agc (Optional[bool], optional): Whether to apply automatic gain control. Defaults to True.
        apply_bandpass (Optional[bool], optional): Whether to apply bandpass filter. Defaults to False.

    Returns:
        torch.Tensor: The enhanced audio waveform.
    """
    if isinstance(audio, str):
        waveform, sample_rate = torchaudio.load(audio)

        if waveform.size(0) > 1:
            waveform = waveform.mean(dim=0, keepdim=True)

    else:
        waveform = audio
        sample_rate = 16000

    if sample_rate != 16000:
        transform = torchaudio.transforms.Resample(
            orig_freq=sample_rate,
            new_freq=16000,
        )
        waveform = transform(waveform)
        sample_rate = 16000

    if apply_agc:
        # Volmax normalization to mimic AGC
        waveform /= waveform.abs().max()

    if apply_bandpass:
        highpass = torchaudio.functional.highpass_biquad(waveform, sample_rate, 300)
        waveform = torchaudio.functional.lowpass_biquad(highpass, sample_rate, 3400)

    return waveform


def is_empty_string(text: str):
    """
    Checks if a string is empty after removing spaces and periods.

    Args:
        text (str): The text to check.

    Returns:
        bool: True if the string is empty, False otherwise.
    """
    text = text.replace(".", "")
    text = re.sub(r"\s+", "", text)
    if text.strip():
        return False
    return True


def format_punct(text: str):
    """
    Removes Whisper's '...' output, and checks for weird spacing in punctuation. Also removes extra spaces.

    Args:
        text (str): The text to format.

    Returns:
        str: The formatted text.
    """
    text = text.strip()

    if text[0].islower():
        text = text[0].upper() + text[1:]
    if text[-1] not in [".", "?", "!", ":", ";", ","]:
        text += "."

    text = text.replace("...", "")
    text = text.replace(" ?", "?")
    text = text.replace(" !", "!")
    text = text.replace(" .", ".")
    text = text.replace(" ,", ",")
    text = text.replace(" :", ":")
    text = text.replace(" ;", ";")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\bi\b", "I", text)

    return text.strip()


def format_segments(segments: list, word_timestamps: bool) -> List[dict]:
    """
    Format the segments to a list of dicts with start, end and text keys. Optionally include word timestamps.

    Args:
        segments (list): List of segments.
        word_timestamps (bool): Whether to include word timestamps.

    Returns:
        list: List of dicts with start, end and word keys.
    """
    formatted_segments = []

    for segment in segments:
        segment_dict = {}

        segment_dict["start"] = segment["start"]
        segment_dict["end"] = segment["end"]
        segment_dict["text"] = segment["text"].strip()
        if word_timestamps:
            _words = [
                {
                    "word": word.word.strip(),
                    "start": word.start,
                    "end": word.end,
                    "score": round(word.probability, 2),
                }
                for word in segment["words"]
            ]
            segment_dict["words"] = _words

        formatted_segments.append(segment_dict)

    return formatted_segments


def get_segment_timestamp_anchor(start: float, end: float, option: str = "start"):
    """Get the timestamp anchor for a segment."""
    if option == "end":
        return end
    elif option == "mid":
        return (start + end) / 2
    return start


def interpolate_nans(x: pd.Series, method="nearest") -> pd.Series:
    """
    Interpolate NaNs in a pandas Series using a given method.

    Args:
        x (pd.Series): The Series to interpolate.
        method (str, optional): The interpolation method. Defaults to "nearest".

    Returns:
        pd.Series: The interpolated Series.
    """
    if x.notnull().sum() > 1:
        return x.interpolate(method=method).ffill().bfill()
    else:
        return x.ffill().bfill()


def read_audio(filepath: str, sample_rate: int = 16000) -> Tuple[torch.Tensor, float]:
    """
    Read an audio file and return the audio tensor.

    Args:
        filepath (str): Path to the audio file.
        sample_rate (int): The sample rate of the audio file. Defaults to 16000.

    Returns:
        Tuple[torch.Tensor, float]: The audio tensor and the audio duration.
    """
    wav, sr = torchaudio.load(filepath)

    if wav.size(0) > 1:
        wav = wav.mean(dim=0, keepdim=True)

    if sr != sample_rate:
        transform = torchaudio.transforms.Resample(orig_freq=sr, new_freq=sample_rate)
        wav = transform(wav)
        sr = sample_rate

    audio_duration = float(wav.shape[1]) / sample_rate

    return wav.squeeze(0), audio_duration


def remove_words_for_svix(dict_payload: dict) -> dict:
    """
    Remove the words from the utterances for SVIX.

    Args:
        dict_payload (dict): The dict payload.

    Returns:
        dict: The dict payload with the words removed.
    """
    for utterance in dict_payload["utterances"]:
        utterance.pop("words", None)

    return dict_payload


def retrieve_user_platform() -> str:
    """
    Retrieve the user's platform.

    Returns:
        str: User's platform. Either 'linux', 'darwin' or 'win32'.
    """
    return sys.platform


async def save_file_locally(filename: str, file: UploadFile) -> bool:
    """
    Save a file locally from an UploadFile object.

    Args:
        filename (str): The filename to save the file as.
        file (UploadFile): The UploadFile object.

    Returns:
        bool: Whether the file was saved successfully.
    """
    async with aiofiles.open(filename, "wb") as f:
        audio_bytes = await file.read()
        await f.write(audio_bytes)

    return True


async def split_dual_channel_file(filepath: str) -> Tuple[str, str]:
    """
    Split a dual channel audio file into two mono files using ffmpeg.

    Args:
        filepath (str): The path to the dual channel audio file.

    Returns:
        Tuple[str, str]: The paths to the two mono files.

    Raises:
        Exception: If the file could not be split.
    """
    logger.debug(f"Splitting dual channel file: {filepath}")

    filename = Path(filepath).stem
    filename_left = f"{filename}_left.wav"
    filename_right = f"{filename}_right.wav"

    cmd = [
        "ffmpeg",
        "-i",
        str(filepath),
        "-map_channel",
        "0.0.0",
        str(filename_left),
        "-map_channel",
        "0.0.1",
        str(filename_right),
    ]
    result = await async_run_subprocess(cmd)

    if result[0] != 0:
        raise Exception(f"Error splitting dual channel file: {filepath}. {result[2]}")

    return filename_left, filename_right