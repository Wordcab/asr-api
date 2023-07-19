# Copyright 2023 The Wordcab Team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Models module of the Wordcab Transcribe."""

from typing import List, Optional

from pydantic import BaseModel, field_validator


class Word(BaseModel):
    """Word model for the API."""

    word: str
    start: float
    end: float
    score: float


class Utterance(BaseModel):
    """Utterance model for the API."""

    text: str
    start: float
    end: float
    speaker: Optional[int]
    words: Optional[List[Word]]


class BaseResponse(BaseModel):
    """Base response model, not meant to be used directly."""

    utterances: List[Utterance]
    audio_duration: float
    alignment: bool
    diarization: bool
    source_lang: str
    timestamps: str
    use_batch: bool
    vocab: List[str]
    word_timestamps: bool
    internal_vad: bool


class AudioResponse(BaseResponse):
    """Response model for the ASR audio file and url endpoint."""

    dual_channel: bool

    class Config:
        """Pydantic config class."""

        json_schema_extra = {
            "example": {
                "utterances": [
                    {
                        "text": "Hello World!",
                        "start": 0.345,
                        "end": 1.234,
                        "speaker": 0,
                    },
                    {
                        "text": "Wordcab is awesome",
                        "start": 1.234,
                        "end": 2.678,
                        "speaker": 1,
                    },
                ],
                "audio_duration": 2.678,
                "alignment": False,
                "diarization": False,
                "source_lang": "en",
                "timestamps": "s",
                "use_batch": False,
                "vocab": [
                    "custom company name",
                    "custom product name",
                    "custom co-worker name",
                ],
                "word_timestamps": False,
                "internal_vad": False,
                "dual_channel": False,
            }
        }


class YouTubeResponse(BaseResponse):
    """Response model for the ASR YouTube endpoint."""

    video_url: str

    class Config:
        """Pydantic config class."""

        json_schema_extra = {
            "example": {
                "utterances": [
                    {
                        "speaker": 0,
                        "start": 0.0,
                        "end": 1.0,
                        "text": "Never gonna give you up!",
                    },
                    {
                        "speaker": 0,
                        "start": 1.0,
                        "end": 2.0,
                        "text": "Never gonna let you down!",
                    },
                ],
                "audio_duration": 2.0,
                "alignment": False,
                "diarization": False,
                "source_lang": "en",
                "timestamps": "s",
                "use_batch": False,
                "vocab": [
                    "custom company name",
                    "custom product name",
                    "custom co-worker name",
                ],
                "word_timestamps": False,
                "internal_vad": False,
                "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            }
        }


class CortexError(BaseModel):
    """Error model for the Cortex API."""

    message: str

    class Config:
        """Pydantic config class."""

        json_schema_extra = {
            "example": {
                "message": "Error message here",
            }
        }


class CortexPayload(BaseModel):
    """Request object for Cortex endpoint."""

    url_type: str = "audio_url"
    url: Optional[str] = None
    api_key: Optional[str] = None
    alignment: Optional[bool] = False
    diarization: Optional[bool] = False
    dual_channel: Optional[bool] = False
    source_lang: Optional[str] = "en"
    timestamps: Optional[str] = "s"
    use_batch: Optional[bool] = False
    vocab: Optional[List[str]] = []
    word_timestamps: Optional[bool] = False
    internal_vad: Optional[bool] = False
    job_name: Optional[str] = None
    ping: Optional[bool] = False

    @field_validator("timestamps")
    def validate_timestamps_values(cls, value: str) -> str:  # noqa: B902, N805
        """Validate the value of the timestamps field."""
        if value not in ["hms", "ms", "s"]:
            raise ValueError("`timestamps` must be one of 'hms', 'ms', 's'.")

        return value

    @field_validator("url_type")
    def validate_url_type(cls, value: str) -> str:  # noqa: B902, N805
        """Validate the value of the url_type field."""
        if value not in ["audio_url", "youtube"]:
            raise ValueError("`url_type` must be one of 'audio_url', 'youtube'.")

        return value

    class Config:
        """Pydantic config class."""

        json_schema_extra = {
            "example": {
                "url_type": "youtube",
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "api_key": "1234567890",
                "alignment": False,
                "diarization": False,
                "dual_channel": False,
                "source_lang": "en",
                "timestamps": "s",
                "use_batch": False,
                "vocab": [
                    "custom company name",
                    "custom product name",
                    "custom co-worker name",
                ],
                "word_timestamps": False,
                "internal_vad": False,
                "job_name": "job_abc123",
                "ping": False,
            }
        }


class CortexUrlResponse(AudioResponse):
    """Response model for the audio_url type of the Cortex endpoint."""

    job_name: str
    request_id: Optional[str] = None

    class Config:
        """Pydantic config class."""

        json_schema_extra = {
            "example": {
                "utterances": [
                    {
                        "speaker": 0,
                        "start": 0.0,
                        "end": 1.0,
                        "text": "Hello World!",
                    },
                    {
                        "speaker": 0,
                        "start": 1.0,
                        "end": 2.0,
                        "text": "Wordcab is awesome",
                    },
                ],
                "audio_duration": 2.0,
                "alignment": False,
                "diariation": False,
                "source_lang": "en",
                "timestamps": "s",
                "use_batch": False,
                "vocab": [
                    "custom company name",
                    "custom product name",
                    "custom co-worker name",
                ],
                "word_timestamps": False,
                "internal_vad": False,
                "dual_channel": False,
                "job_name": "job_name",
                "request_id": "request_id",
            }
        }


class CortexYoutubeResponse(YouTubeResponse):
    """Response model for the YouTube type of the Cortex endpoint."""

    job_name: str
    request_id: Optional[str] = None

    class Config:
        """Pydantic config class."""

        json_schema_extra = {
            "example": {
                "utterances": [
                    {
                        "speaker": 0,
                        "start": 0.0,
                        "end": 1.0,
                        "text": "Never gonna give you up!",
                    },
                    {
                        "speaker": 0,
                        "start": 1.0,
                        "end": 2.0,
                        "text": "Never gonna let you down!",
                    },
                ],
                "audio_duration": 2.0,
                "alignment": False,
                "diariation": False,
                "source_lang": "en",
                "timestamps": "s",
                "use_batch": False,
                "vocab": [
                    "custom company name",
                    "custom product name",
                    "custom co-worker name",
                ],
                "word_timestamps": False,
                "internal_vad": False,
                "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "job_name": "job_name",
                "request_id": "request_id",
            }
        }


class BaseRequest(BaseModel):
    """Base request model for the API."""

    alignment: bool = False
    diarization: bool = False
    source_lang: str = "en"
    timestamps: str = "s"
    use_batch: bool = False
    vocab: List[str] = []
    word_timestamps: bool = False
    internal_vad: bool = False

    @field_validator("timestamps")
    def validate_timestamps_values(cls, value: str) -> str:  # noqa: B902, N805
        """Validate the value of the timestamps field."""
        if value not in ["hms", "ms", "s"]:
            raise ValueError("`timestamps` must be one of 'hms', 'ms', 's'.")

        return value

    @field_validator("vocab")
    def validate_each_vocab_value(
        cls, value: List[str]  # noqa: B902, N805
    ) -> List[str]:
        """Validate the value of each vocab field."""
        if not all(isinstance(v, str) for v in value):
            raise ValueError("`vocab` must be a list of strings.")

        return value

    class Config:
        """Pydantic config class."""

        json_schema_extra = {
            "example": {
                "alignment": False,
                "diarization": False,
                "source_lang": "en",
                "timestamps": "s",
                "use_batch": False,
                "vocab": [
                    "custom company name",
                    "custom product name",
                    "custom co-worker name",
                ],
                "word_timestamps": False,
                "internal_vad": False,
            }
        }


class AudioRequest(BaseRequest):
    """Request model for the ASR audio file and url endpoint."""

    dual_channel: bool = False

    class Config:
        """Pydantic config class."""

        json_schema_extra = {
            "example": {
                "alignment": False,
                "diarization": False,
                "source_lang": "en",
                "timestamps": "s",
                "use_batch": False,
                "vocab": [
                    "custom company name",
                    "custom product name",
                    "custom co-worker name",
                ],
                "word_timestamps": False,
                "dual_channel": False,
                "internal_vad": False,
            }
        }


class PongResponse(BaseModel):
    """Response model for the ping endpoint."""

    message: str

    class Config:
        """Pydantic config class."""

        json_schema_extra = {
            "example": {
                "message": "pong",
            },
        }


class Token(BaseModel):
    """Token model for authentication."""

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """TokenData model for authentication."""

    username: Optional[str] = None
