import { ref } from 'vue'
import { defineStore } from 'pinia'

import {
  fetchCourses,
  saveCourses,
  type CourseItem,
  type CoursePayload,
} from '@/api/courses'
import { courses as mockCourses, type Course } from '@/mock/data'

const palette = [
  'linear-gradient(135deg,#6366f1,#818cf8)',
  'linear-gradient(135deg,#0ea5e9,#22d3ee)',
  'linear-gradient(135deg,#a855f7,#d946ef)',
  'linear-gradient(135deg,#f97316,#fbbf24)',
  'linear-gradient(135deg,#10b981,#34d399)',
  'linear-gradient(135deg,#ec4899,#f472b6)',
  'linear-gradient(135deg,#8b5cf6,#22d3ee)',
]

/** 新增/编辑时提交的字段 */
export type CourseInput = Omit<Course, 'id' | 'color'>

function toCourse(item: CourseItem, index: number): Course {
  return {
    id: item.id,
    name: item.name,
    teacher: item.teacher,
    room: item.room,
    day: item.day,
    section: item.section,
    color: item.color || palette[index % palette.length],
  }
}

function toPayload(course: Course): CoursePayload {
  return {
    name: course.name,
    teacher: course.teacher,
    room: course.room,
    day: course.day,
    section: course.section,
    color: course.color,
  }
}

export const useScheduleStore = defineStore('schedule', () => {
  // 先放示例课表，load() 之后以数据库为准
  const courses = ref<Course[]>(mockCourses.map((item) => ({ ...item })))
  const loading = ref(false)

  async function load() {
    loading.value = true
    try {
      const remote = await fetchCourses()
      if (remote.length) {
        courses.value = remote.map(toCourse)
      } else if (courses.value.length) {
        // 第一次接入数据库：把页面上已有的课表同步过去，避免页面有课、库里是空的
        const saved = await saveCourses(courses.value.map(toPayload))
        courses.value = saved.map(toCourse)
      }
    } finally {
      loading.value = false
    }
  }

  async function persist(next: Course[]) {
    const saved = await saveCourses(next.map(toPayload))
    courses.value = saved.map(toCourse)
  }

  async function add(payload: CourseInput) {
    const course: Course = {
      ...payload,
      id: 0,
      color: palette[courses.value.length % palette.length],
    }
    await persist([...courses.value, course])
  }

  async function update(id: number, payload: CourseInput) {
    const next = courses.value.map((item) =>
      item.id === id ? { ...item, ...payload } : item,
    )
    await persist(next)
  }

  async function remove(id: number) {
    await persist(courses.value.filter((item) => item.id !== id))
  }

  async function replaceAll(list: CourseInput[]) {
    const next = list.map((item, index) => ({
      ...item,
      id: 0,
      color: palette[index % palette.length],
    }))
    await persist(next)
  }

  return { courses, loading, load, add, update, remove, replaceAll }
})
