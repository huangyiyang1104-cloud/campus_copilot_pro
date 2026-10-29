import * as XLSX from 'xlsx'

export interface ImportedCourse {
  name: string
  teacher: string
  room: string
  day: number // 1-5：周一到周五
  section: number // 1-5：第 1-2 / 3-4 / 5-6 / 7-8 / 9-10 节
}

const DAY_MAP: Record<string, number> = {
  周一: 1,
  星期一: 1,
  礼拜一: 1,
  一: 1,
  周二: 2,
  星期二: 2,
  礼拜二: 2,
  二: 2,
  周三: 3,
  星期三: 3,
  礼拜三: 3,
  三: 3,
  周四: 4,
  星期四: 4,
  礼拜四: 4,
  四: 4,
  周五: 5,
  星期五: 5,
  礼拜五: 5,
  五: 5,
}

const HEADER_ALIASES = {
  name: ['课程名称', '课程', '名称', 'course'],
  teacher: ['任课教师', '教师', '老师', 'teacher'],
  room: ['上课地点', '教室', '地点', 'room'],
  day: ['星期', '周几', 'day'],
  section: ['节次', '大节', 'section'],
}

function parseDay(value: unknown): number | null {
  const text = String(value ?? '').replace(/\s/g, '')
  if (/^[1-5]$/.test(text)) return Number(text)
  return DAY_MAP[text] ?? null
}

/** “第3-4节”按真实节次换算成大节；直接填 1-5 则当作第几大节 */
function parseSection(value: unknown): number | null {
  const text = String(value ?? '').replace(/\s/g, '')
  if (!text) return null
  if (/^[1-5]$/.test(text)) return Number(text)

  const first = text.match(/\d+/)
  if (!first) return null
  const section = Math.ceil(Number(first[0]) / 2)
  return Math.min(5, Math.max(1, section))
}

function findHeader(headers: string[], aliases: string[]) {
  return headers.find((header) =>
    aliases.some((alias) => header.toLowerCase().includes(alias.toLowerCase())),
  )
}

/** 读取上传的文件，解析成课程列表；格式不对的行直接跳过并计数 */
export async function parseScheduleFile(
  file: File,
): Promise<{ courses: ImportedCourse[]; skipped: number }> {
  const buffer = await file.arrayBuffer()
  let workbook: XLSX.WorkBook

  if (file.name.toLowerCase().endsWith('.csv')) {
    // Excel 导出的 CSV 可能是 GBK，先按 UTF-8 严格解码，失败再退到 GBK
    let text: string
    try {
      text = new TextDecoder('utf-8', { fatal: true }).decode(buffer)
    } catch {
      text = new TextDecoder('gbk').decode(buffer)
    }
    workbook = XLSX.read(text, { type: 'string', raw: true })
  } else {
    workbook = XLSX.read(buffer, { type: 'array' })
  }

  const sheet = workbook.Sheets[workbook.SheetNames[0]]
  if (!sheet) throw new Error('文件里没有可读取的工作表')

  // raw: false 按显示文本取值，避免 "3-4" 被当成日期序列号
  const rows = XLSX.utils.sheet_to_json<Record<string, unknown>>(sheet, {
    defval: '',
    raw: false,
  })
  if (!rows.length) throw new Error('表格是空的，没有解析到数据')

  const headers = Object.keys(rows[0])
  const nameKey = findHeader(headers, HEADER_ALIASES.name)
  const dayKey = findHeader(headers, HEADER_ALIASES.day)
  const sectionKey = findHeader(headers, HEADER_ALIASES.section)
  const teacherKey = findHeader(headers, HEADER_ALIASES.teacher)
  const roomKey = findHeader(headers, HEADER_ALIASES.room)

  if (!nameKey || !dayKey || !sectionKey) {
    throw new Error('表头缺少必需列：课程名称、星期、节次')
  }

  const courses: ImportedCourse[] = []
  const occupied = new Set<string>()
  let skipped = 0

  for (const row of rows) {
    const name = String(row[nameKey] ?? '').trim()
    const day = parseDay(row[dayKey])
    const section = parseSection(row[sectionKey])
    const slot = `${day}-${section}`

    if (!name || !day || !section || occupied.has(slot)) {
      skipped += 1
      continue
    }

    occupied.add(slot)
    courses.push({
      name,
      day,
      section,
      teacher: teacherKey ? String(row[teacherKey] ?? '').trim() : '',
      room: roomKey ? String(row[roomKey] ?? '').trim() : '',
    })
  }

  return { courses, skipped }
}
