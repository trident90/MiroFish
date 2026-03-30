import service from './index'

export function getLlmSettings() {
  return service.get('/api/settings/llm')
}

export function saveLlmSettings(data) {
  return service.post('/api/settings/llm', data)
}
