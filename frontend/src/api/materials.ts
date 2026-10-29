import http from '@/api/http'

export interface MaterialItem {
  id: number
  name: string
  file_type: string
  size: number
  course: string | null
  chunk_count: number
  status: 0 | 1 | 2 | 3
  error_msg: string | null
  created_at: string
}

export function fetchMaterials() {
  return http.get<MaterialItem[]>('/materials').then((response) => response.data)
}

export function uploadMaterial(
  file: File,
  courseName: string | undefined,
  onProgress: (percent: number) => void,
) {
  const form = new FormData()
  form.append('file', file)
  if (courseName) form.append('course_name', courseName)

  return http
    .post<MaterialItem>('/materials/upload', form, {
      onUploadProgress: (event) => {
        if (event.total) {
          onProgress(Math.round((event.loaded / event.total) * 100))
        }
      },
    })
    .then((response) => response.data)
}

export function fetchDownloadUrl(materialId: number) {
  return http
    .get<{ url: string; file_name: string }>(`/materials/${materialId}/download-url`)
    .then((response) => response.data)
}

export function deleteMaterial(materialId: number) {
  return http
    .delete<{ message: string }>(`/materials/${materialId}`)
    .then((response) => response.data)
}
