/**
 * VRC OSC Chatbox - ASR AudioWorklet Processor
 *
 * 将麦克风音频重采样为 16kHz Int16 PCM，
 * 通过 RMS 能量检测 (VAD) 仅在有人声时发送数据到主线程。
 * 语音结束后不立即切断，而是用真实的环境音频自然衰减，
 * 让云端 VAD 检测到语音结束并返回最终结果。
 */
class ASRProcessor extends AudioWorkletProcessor {
  constructor() {
    super()

    // ── PCM 重采样缓冲 ──
    /** 重采样后的 PCM 缓冲（Int16, 16kHz mono）*/
    this.pcmBuffer = new Int16Array(8192)
    /** 缓冲中有效数据的写入位置 */
    this.pcmWritePos = 0

    // ── VAD 状态 ──
    /** 指数平滑后的能量值 */
    this.smoothEnergy = 0.0
    /** 连续语音帧计数 */
    this.speechFrameCount = 0
    /** 连续静音帧计数 */
    this.silenceFrameCount = 0
    /** 当前是否处于语音段（含挂起）*/
    this.isSpeaking = false
    /** 挂起剩余帧数。挂起期间继续发送真实音频，让云端 VAD 听到自然的衰减 */
    this.hangoverRemaining = 0

    // ── VAD 参数（可由主线程通过 postMessage 覆盖）──
    /**
     * RMS 能量阈值（归一化 0–1）。
     * 0.003 可检测轻声说话，同时过滤底噪。
     */
    this.energyThreshold = 0.003
    /** 能量指数平滑系数 (EMA α)，越小越平滑 */
    this.smoothCoeff = 0.15
    /** 连续语音帧数确认阈值（~120ms @ 40ms/帧）*/
    this.speechStartFrames = 3
    /**
     * 连续静音帧数阈值，达到后语音结束、进入挂起。
     * 15 帧 × 40ms = 600ms。
     */
    this.speechEndFrames = 15
    /**
     * 挂起持续帧数。
     * 语音结束后继续发送真实环境音频的时长，
     * 给云端 VAD 足够的衰减信号来判断语音已结束。
     * 25 帧 × 40ms = 1000ms。
     */
    this.hangoverFrames = 25        // 挂起持续（~1000ms，让云端检测衰减）

    // VAD 开关。关闭时所有音频直接发送
    this.vadEnabled = true

    // 预语音缓冲（保留句首 ~200ms）
    this.preSpeech = []
    this.maxPreSpeechFrames = 5

    // ── 接收主线程配置 ──
    this.port.onmessage = (event) => {
      const msg = event.data
      if (msg && msg.type === 'config') {
        if (typeof msg.energyThreshold === 'number') {
          this.energyThreshold = msg.energyThreshold
        }
        if (typeof msg.smoothCoeff === 'number') {
          this.smoothCoeff = msg.smoothCoeff
        }
        if (typeof msg.vadEnabled === 'boolean') {
          this.vadEnabled = msg.vadEnabled
        }
      }
    }
  }

  /**
   * 计算 Int16 PCM 块的归一化 RMS 能量
   * @param {Int16Array} samples
   * @param {number} offset
   * @param {number} len
   * @returns {number} 归一化 RMS 值 (0–1)
   */
  calcRMS(samples, offset, len) {
    let sum = 0.0
    const end = offset + len
    for (let i = offset; i < end; i++) {
      const s = samples[i] / 32768.0
      sum += s * s
    }
    return Math.sqrt(sum / len)
  }

  /**
   * 将 Int16Array 块零拷贝发送到主线程
   * @param {Int16Array} chunk 独立副本（会 transfer 其底层 buffer）
   */
  sendChunk(chunk) {
    this.port.postMessage(chunk.buffer, [chunk.buffer])
  }

  /**
   * VAD 状态机决策：传入当前帧 RMS 能量，返回是否应发送该帧。
   * 副作用：更新预语音缓冲、flush preSpeech、状态转换。
   * @param {number} frameEnergy 当前帧的归一化 RMS 能量
   * @returns {boolean}
   */
  vadDecision(frameEnergy) {
    // 指数平滑
    this.smoothEnergy =
      this.smoothCoeff * frameEnergy + (1 - this.smoothCoeff) * this.smoothEnergy

    const isSpeech = this.smoothEnergy > this.energyThreshold

    if (isSpeech) {
      this.silenceFrameCount = 0
      this.speechFrameCount++

      if (!this.isSpeaking && this.speechFrameCount >= this.speechStartFrames) {
        // ── 语音开始：flush 预语音缓冲 ──
        this.isSpeaking = true
        this.hangoverRemaining = 0
        for (const frame of this.preSpeech) {
          this.sendChunk(frame)
        }
        this.preSpeech = []
      }
      return true
    } else {
      this.speechFrameCount = 0

      if (this.isSpeaking) {
        // 仍在语音段内，继续发送（等待挂起触发）
        this.silenceFrameCount++
        if (this.silenceFrameCount >= this.speechEndFrames) {
          // 语音结束，进入挂起 —— 继续发送真实音频让云端 VAD 听到自然衰减
          this.isSpeaking = false
          this.hangoverRemaining = this.hangoverFrames
        }
        return true
      } else if (this.hangoverRemaining > 0) {
        // 挂起中，继续发送真实环境音频
        this.hangoverRemaining--
        return true
      }

      // ── 完全静音（挂起已耗尽）：加入预语音缓冲，不发送 ──
      this.silenceFrameCount++
      return false
    }
  }

  /**
   * 将帧加入预语音缓冲（环形覆盖）
   * @param {Int16Array} frame
   */
  bufferPreSpeech(frame) {
    this.preSpeech.push(frame)
    while (this.preSpeech.length > this.maxPreSpeechFrames) {
      this.preSpeech.shift()
    }
  }

  process(inputs) {
    const input = inputs[0]
    if (!input || !input.length) return true

    const channelData = input[0]
    if (!channelData || !channelData.length) return true

    // ── 重采样到 16kHz ──
    const fromRate = sampleRate
    const targetLength = Math.floor((channelData.length * 16000) / fromRate)
    if (targetLength === 0) return true

    // 确保 buffer 有足够空间
    const needed = this.pcmWritePos + targetLength
    if (needed > this.pcmBuffer.length) {
      let newLen = Math.max(needed, this.pcmBuffer.length * 2)
      // 限制最大 10 秒以防异常增长
      if (newLen > 160000) newLen = 160000
      const newBuf = new Int16Array(newLen)
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

    // 每 40ms（640 samples）一帧
    while (this.pcmWritePos >= 640) {
      const frame = this.pcmBuffer.slice(0, 640)
      this.pcmBuffer.copyWithin(0, 640, this.pcmWritePos)
      this.pcmWritePos -= 640

      if (this.vadEnabled) {
        // 实时模式：VAD 过滤静音
        const frameEnergy = this.calcRMS(frame, 0, 640)
        if (this.vadDecision(frameEnergy)) {
          this.sendChunk(frame)
        } else {
          this.bufferPreSpeech(frame)
        }
      } else {
        // 非实时模式：直接发送所有音频
        this.sendChunk(frame)
      }
    }

    return true
  }
}

registerProcessor('asr-processor', ASRProcessor)
