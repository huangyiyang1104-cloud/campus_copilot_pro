import http from '@/api/http'

/** 一句文本合成 WAV（后端负责 TTS + RVC） */
export async function synthesizeSpeech(text: string, tag?: string): Promise<Blob> {
  const response = await http.post(
    '/tts/speech',
    { text, tag },
    { responseType: 'blob', timeout: 120_000 },
  )
  return response.data as Blob
}
