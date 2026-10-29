import { ref } from 'vue'
import { defineStore } from 'pinia'

import {
  deleteStudyPlan,
  fetchStudyPlans,
  updateTaskDone,
  type StudyPlan,
} from '@/api/studyPlans'

export const useStudyPlanStore = defineStore('studyPlan', () => {
  const plans = ref<StudyPlan[]>([])
  const loading = ref(false)

  async function load() {
    loading.value = true
    try {
      plans.value = await fetchStudyPlans()
    } finally {
      loading.value = false
    }
  }

  async function setTaskDone(planId: number, taskId: number, done: boolean) {
    const updated = await updateTaskDone(planId, taskId, done)

    const plan = plans.value.find((item) => item.id === planId)
    const task = plan?.tasks.find((item) => item.id === taskId)
    if (task) task.done = updated.done
  }

  async function remove(planId: number) {
    await deleteStudyPlan(planId)
    plans.value = plans.value.filter((item) => item.id !== planId)
  }

  return { plans, loading, load, setTaskDone, remove }
})
