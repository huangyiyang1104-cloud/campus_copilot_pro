import http from '@/api/http'

export interface StudyPlanTask {
  id: number
  name: string
  done: boolean
}

export interface StudyPlan {
  id: number
  title: string
  course: string | null
  deadline: string | null
  tasks: StudyPlanTask[]
}

export function fetchStudyPlans() {
  return http.get<StudyPlan[]>('/study-plans').then((response) => response.data)
}

export function updateTaskDone(planId: number, taskId: number, done: boolean) {
  return http
    .patch<StudyPlanTask>(`/study-plans/${planId}/tasks/${taskId}`, { done })
    .then((response) => response.data)
}

export function deleteStudyPlan(planId: number) {
  return http
    .delete<{ message: string }>(`/study-plans/${planId}`)
    .then((response) => response.data)
}
