/** 第一版先用假数据，接口接好后换成后端返回 */

export interface Course {
  id: number
  name: string
  teacher: string
  room: string
  day: number // 1-5：周一到周五
  section: number // 1-5：第 1-2 / 3-4 / 5-6 / 7-8 / 9-10 节
  color: string
}

export const courses: Course[] = [
  { id: 1, name: '数据结构', teacher: '王强', room: '信工楼 A301', day: 1, section: 1, color: 'linear-gradient(135deg,#6366f1,#818cf8)' },
  { id: 2, name: '大学英语', teacher: 'Linda', room: '文科楼 B204', day: 1, section: 3, color: 'linear-gradient(135deg,#0ea5e9,#22d3ee)' },
  { id: 3, name: '操作系统', teacher: '李敏', room: '信工楼 A205', day: 2, section: 2, color: 'linear-gradient(135deg,#a855f7,#d946ef)' },
  { id: 4, name: '体育（篮球）', teacher: '赵勇', room: '东区体育馆', day: 2, section: 5, color: 'linear-gradient(135deg,#f97316,#fbbf24)' },
  { id: 5, name: '计算机网络', teacher: '陈立', room: '信工楼 A402', day: 3, section: 1, color: 'linear-gradient(135deg,#10b981,#34d399)' },
  { id: 6, name: '数据库原理', teacher: '周颖', room: '信工楼 A308', day: 3, section: 4, color: 'linear-gradient(135deg,#ec4899,#f472b6)' },
  { id: 7, name: '人工智能导论', teacher: '孙浩', room: '信工楼 B501', day: 4, section: 2, color: 'linear-gradient(135deg,#6366f1,#a855f7)' },
  { id: 8, name: '线性代数', teacher: '吴梅', room: '理科楼 C102', day: 4, section: 4, color: 'linear-gradient(135deg,#0ea5e9,#6366f1)' },
  { id: 9, name: '数据结构实验', teacher: '王强', room: '机房 A-2', day: 5, section: 2, color: 'linear-gradient(135deg,#8b5cf6,#22d3ee)' },
]

export const sections = ['第 1-2 节', '第 3-4 节', '第 5-6 节', '第 7-8 节', '第 9-10 节']
export const weekdays = ['周一', '周二', '周三', '周四', '周五']

export interface PlanTask {
  id: number
  name: string
  done: boolean
}

export interface StudyPlan {
  id: number
  title: string
  course: string
  deadline: string
  tasks: PlanTask[]
}

export const studyPlans: StudyPlan[] = [
  {
    id: 1,
    title: '数据结构期末冲刺',
    course: '数据结构',
    deadline: '2026-11-08',
    tasks: [
      { id: 1, name: '复盘树与二叉树遍历', done: true },
      { id: 2, name: '手写图的最短路径算法', done: true },
      { id: 3, name: '完成 20 道排序真题', done: false },
      { id: 4, name: '整理错题本并复盘', done: false },
    ],
  },
  {
    id: 2,
    title: '计算机网络实验报告',
    course: '计算机网络',
    deadline: '2026-11-03',
    tasks: [
      { id: 1, name: '抓包分析 TCP 三次握手', done: true },
      { id: 2, name: '整理 Wireshark 截图', done: false },
      { id: 3, name: '撰写实验结论', done: false },
    ],
  },
  {
    id: 3,
    title: '数据库大作业',
    course: '数据库原理',
    deadline: '2026-11-15',
    tasks: [
      { id: 1, name: '设计 ER 图', done: true },
      { id: 2, name: '建表并写触发器', done: false },
      { id: 3, name: '完成前端展示页面', done: false },
      { id: 4, name: '录制演示视频', done: false },
    ],
  },
]

export interface Material {
  id: number
  name: string
  course: string
  size: string
  uploadedAt: string
  status: 'indexed' | 'indexing'
}

export const materials: Material[] = [
  { id: 1, name: '数据结构 第3章 树与二叉树.pdf', course: '数据结构', size: '2.4 MB', uploadedAt: '2026-10-20', status: 'indexed' },
  { id: 2, name: '计算机网络 实验指导书.pdf', course: '计算机网络', size: '1.1 MB', uploadedAt: '2026-10-22', status: 'indexed' },
  { id: 3, name: '数据库 复习提纲.docx', course: '数据库原理', size: '386 KB', uploadedAt: '2026-10-25', status: 'indexing' },
  { id: 4, name: '人工智能导论 课程笔记.md', course: '人工智能导论', size: '128 KB', uploadedAt: '2026-10-26', status: 'indexed' },
]
