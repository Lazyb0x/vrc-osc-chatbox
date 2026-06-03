import logging
from os.path import expanduser
from typing import AsyncIterator

from doubaoime_asr import transcribe_realtime, ResponseType
from doubaoime_asr.config import ASRConfig

logger = logging.getLogger(__name__)


async def asr_stream(
    audio_source: AsyncIterator[bytes],
    credential_path: str | None = None,
) -> AsyncIterator[dict]:
    """
    对 PCM 音频流进行实时语音识别，产出识别结果字典。

    Args:
        audio_source: PCM 16-bit mono 16kHz 音频数据的异步迭代器
        credential_path: 凭据缓存文件路径（首次使用自动注册设备）

    Yields:
        {"type": "interim" | "final" | "error", "text": str}
    """
    if credential_path:
        credential_path = expanduser(credential_path)

    config = ASRConfig(credential_path=credential_path)

    try:
        async for response in transcribe_realtime(audio_source, config=config):
            if response.type == ResponseType.INTERIM_RESULT:
                yield {"type": "interim", "text": response.text}
            elif response.type == ResponseType.FINAL_RESULT:
                yield {"type": "final", "text": response.text}
            elif response.type == ResponseType.ERROR:
                logger.error(f"ASR error: {response.error_msg}")
                yield {"type": "error", "text": response.error_msg}
                return
            # TASK_STARTED / SESSION_STARTED / VAD_START / SESSION_FINISHED: 忽略
    except Exception as e:
        logger.error(f"ASR stream error: {e}", exc_info=True)
        yield {"type": "error", "text": str(e)}
