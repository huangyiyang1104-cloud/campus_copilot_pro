import http from '@/api/http'

/** 提交给后端的单门课程 */
export interface CoursePayload {
  name: string
  teacher: string
  room: string
  day: number
  section: number
  color: string
}

/** 后端返回的课程，多了数据库 id */
export interface CourseItem extends CoursePayload {
  id: number
}

export function fetchCourses() {
  return http.get<CourseItem[]>('/courses').then((response) => response.data)
}

export function saveCourses(courses: CoursePayload[]) {
  return http.put<CourseItem[]>('/courses', { courses }).then((response) => response.data)
}
