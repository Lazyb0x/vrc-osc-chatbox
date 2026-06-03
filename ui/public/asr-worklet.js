/**
 * VRC OSC Chatbox - ASR AudioWorklet Processor
 * 将麦克风音频重采样为 16kHz Int16 PCM 并发送到主线程
 */
class ASRProcessor extends AudioWorkletProcessor {
  constructor() {
    super()
    /** 重采样后的 PCM buffer */
    this.pcmBuffer = new Int16Array(4096)
    this.pcmWritePos = 0
  }

  process(inputs) {
    const input = inputs[0]
    if (!input || !input.length) {
      return true // 保持 processor 存活
    }

    const channelData = input[0]
    if (!channelData || !channelData.length) {
      return true
    }

    // 重采样到 16kHz
    const fromRate = sampleRate // AudioWorkletGlobalScope 的全局变量
    const targetLength = Math.floor((channelData.length * 16000) / fromRate)
    if (targetLength === 0) return true

    // 确保 buffer 有足够空间
    const needed = this.pcmWritePos + targetLength
    if (needed > this.pcmBuffer.length) {
      const newBuf = new Int16Array(Math.max(needed, this.pcmBuffer.length * 2))
      newBuf.set(this.pcmBuffer.subarray(0, this.pcmWritePos))
      this.pcmBuffer = newBuf
    }

    const ratio = channelData.length / targetLength
    for (let i = 0; i < targetLength; i++) {
      const pos = i * ratio
      const index = Math.floor(pos)
      const frac = pos - index
      let sample
      if (index + 1 < channelData.length) {
        sample = channelData[index] * (1 - frac) + channelData[index + 1] * frac
      } else {
        sample = channelData[index] || 0
      }
      // Float32 [-1, 1] → Int16 [-32768, 32767]
      const s = Math.max(-1, Math.min(1, sample))
      this.pcmBuffer[this.pcmWritePos++] = s < 0 ? s * 0x8000 : s * 0x7fff
    }

    // 每积累约 40ms（640 采样 @ 16kHz）发送一次，减少 WebSocket 开销
    if (this.pcmWritePos >= 640) {
      const chunk = new Int16Array(this.pcmBuffer.subarray(0, this.pcmWritePos))
      this.port.postMessage(chunk.buffer, [chunk.buffer]) // transfer ownership
      this.pcmBuffer = new Int16Array(4096)
      this.pcmWritePos = 0
    }

    return true
  }
}

registerProcessor('asr-processor', ASRProcessor)
