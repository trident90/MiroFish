<template>
  <Teleport to="body">
    <div v-if="visible" class="settings-overlay" @click.self="close">
      <div class="settings-modal">
        <!-- Header -->
        <div class="modal-header">
          <div class="modal-title">
            <span class="icon">⚙</span> LLM Model Settings
          </div>
          <button class="close-btn" @click="close">✕</button>
        </div>

        <!-- Loading state -->
        <div v-if="loading" class="modal-loading">Loading settings...</div>

        <!-- Content -->
        <div v-else class="modal-body">
          <p class="modal-desc">
            Configure separate LLM models for simulation and report generation.
            Leave fields empty to use the shared default (<code>LLM_*</code> env values).
          </p>

          <!-- Shared (readonly info) -->
          <section class="settings-section">
            <div class="section-title">
              <span class="badge badge-default">Default</span>
              Shared LLM <span class="section-hint">(set via .env / LLM_*)</span>
            </div>
            <div class="info-row">
              <div class="info-item">
                <label>API Key</label>
                <div class="info-value" :class="{ 'not-set': !shared.api_key?.is_set }">
                  {{ shared.api_key?.is_set ? shared.api_key.value : 'Not configured' }}
                </div>
              </div>
              <div class="info-item">
                <label>Base URL</label>
                <div class="info-value" :class="{ 'not-set': !shared.base_url?.is_set }">
                  {{ shared.base_url?.value || 'Not configured' }}
                </div>
              </div>
              <div class="info-item">
                <label>Model</label>
                <div class="info-value" :class="{ 'not-set': !shared.model?.is_set }">
                  {{ shared.model?.value || 'Not configured' }}
                </div>
              </div>
            </div>
          </section>

          <!-- Simulation LLM -->
          <section class="settings-section">
            <div class="section-title">
              <span class="badge badge-sim">Simulation</span>
              Simulation LLM
              <span class="section-hint">Ontology, profile, simulation config generation</span>
            </div>
            <div class="effective-row" v-if="simulation.model?.effective">
              <span class="effective-label">Currently using:</span>
              <span class="effective-value">{{ simulation.model.effective }}</span>
            </div>
            <div class="field-grid">
              <div class="field-item">
                <label>API Key</label>
                <input
                  v-model="form.SIMULATION_LLM_API_KEY"
                  type="password"
                  :placeholder="simulation.api_key?.is_set ? simulation.api_key.value : 'Same as default'"
                  autocomplete="new-password"
                />
              </div>
              <div class="field-item">
                <label>Base URL</label>
                <input
                  v-model="form.SIMULATION_LLM_BASE_URL"
                  type="text"
                  :placeholder="simulation.base_url?.effective || 'Same as default'"
                />
              </div>
              <div class="field-item">
                <label>Model Name</label>
                <input
                  v-model="form.SIMULATION_LLM_MODEL_NAME"
                  type="text"
                  :placeholder="simulation.model?.effective || 'Same as default'"
                />
              </div>
            </div>
          </section>

          <!-- Report LLM -->
          <section class="settings-section">
            <div class="section-title">
              <span class="badge badge-report">Report</span>
              Report LLM
              <span class="section-hint">Report generation (recommend large-context model)</span>
            </div>
            <div class="effective-row" v-if="report.model?.effective">
              <span class="effective-label">Currently using:</span>
              <span class="effective-value">{{ report.model.effective }}</span>
            </div>
            <div class="field-grid">
              <div class="field-item">
                <label>API Key</label>
                <input
                  v-model="form.REPORT_LLM_API_KEY"
                  type="password"
                  :placeholder="report.api_key?.is_set ? report.api_key.value : 'Same as default'"
                  autocomplete="new-password"
                />
              </div>
              <div class="field-item">
                <label>Base URL</label>
                <input
                  v-model="form.REPORT_LLM_BASE_URL"
                  type="text"
                  :placeholder="report.base_url?.effective || 'Same as default'"
                />
              </div>
              <div class="field-item">
                <label>Model Name</label>
                <input
                  v-model="form.REPORT_LLM_MODEL_NAME"
                  type="text"
                  :placeholder="report.model?.effective || 'Same as default'"
                />
              </div>
            </div>
          </section>

          <!-- Preset quick-fill buttons -->
          <section class="settings-section presets-section">
            <div class="section-title">
              <span class="badge badge-default">Presets</span>
              Quick Fill — Report LLM + Recommended Parameters
            </div>
            <div class="preset-buttons">
              <button
                v-for="p in presetList"
                :key="p.key"
                class="preset-btn"
                :class="{ 'preset-active': activePreset === p.key }"
                @click="applyPreset(p.key)"
              >{{ p.label }}</button>
              <button class="preset-btn preset-clear" @click="clearReport">Clear</button>
            </div>
            <!-- Recommendation hint shown after preset click -->
            <div v-if="activePreset && PRESETS[activePreset]" class="preset-hint">
              <div class="hint-title">Recommended settings for <b>{{ PRESETS[activePreset].label }}</b></div>
              <div class="hint-grid">
                <div class="hint-item" v-for="(val, key) in PRESETS[activePreset].params" :key="key">
                  <span class="hint-key">{{ PARAM_LABELS[key] }}</span>
                  <span class="hint-val">{{ val }}</span>
                  <span class="hint-desc">{{ PARAM_DESCS[key] }}</span>
                </div>
              </div>
              <button class="btn-apply-params" @click="applyPresetParams(activePreset)">
                Apply Recommended Parameters ↓
              </button>
            </div>
          </section>

          <!-- Advanced: Report Generation Parameters -->
          <section class="settings-section">
            <div class="section-title" @click="showAdvanced = !showAdvanced" style="cursor:pointer">
              <span class="badge badge-report">Advanced</span>
              Report Generation Parameters
              <span class="toggle-arrow">{{ showAdvanced ? '▲' : '▼' }}</span>
            </div>
            <div v-if="showAdvanced" class="field-grid field-grid-2">
              <div class="field-item">
                <label>Max Output Tokens
                  <span class="field-hint">per section</span>
                </label>
                <input v-model.number="form.REPORT_LLM_MAX_TOKENS" type="number" min="512" max="32000" step="512"
                  :placeholder="report.max_tokens?.effective ?? 4096" />
              </div>
              <div class="field-item">
                <label>Temperature
                  <span class="field-hint">0.0 – 1.0</span>
                </label>
                <input v-model.number="form.REPORT_LLM_TEMPERATURE" type="number" min="0" max="1" step="0.05"
                  :placeholder="report.temperature?.effective ?? 0.5" />
              </div>
              <div class="field-item">
                <label>Tool Result Limit
                  <span class="field-hint">chars per tool call</span>
                </label>
                <input v-model.number="form.REPORT_LLM_TOOL_RESULT_LIMIT" type="number" min="500" max="50000" step="500"
                  :placeholder="report.tool_result_limit?.effective ?? 3000" />
              </div>
              <div class="field-item">
                <label>Sim Requirement Limit
                  <span class="field-hint">chars in system prompt</span>
                </label>
                <input v-model.number="form.REPORT_LLM_SIM_REQ_LIMIT" type="number" min="200" max="20000" step="200"
                  :placeholder="report.sim_req_limit?.effective ?? 800" />
              </div>
              <div class="field-item">
                <label>Prev Section Limit
                  <span class="field-hint">chars per prev section</span>
                </label>
                <input v-model.number="form.REPORT_LLM_PREV_SECTION_LIMIT" type="number" min="200" max="10000" step="200"
                  :placeholder="report.prev_section_limit?.effective ?? 1000" />
              </div>
              <div class="field-item field-item-info">
                <label>Context Budget Guide</label>
                <div class="budget-info">
                  <div>System prompt: ~{{ Math.round((form.REPORT_LLM_SIM_REQ_LIMIT || report.sim_req_limit?.effective || 800) / 4) }} tokens</div>
                  <div>Prev sections: ~{{ Math.round(((form.REPORT_LLM_PREV_SECTION_LIMIT || report.prev_section_limit?.effective || 1000) * 2) / 4) }} tokens</div>
                  <div>Tool results ×5: ~{{ Math.round(((form.REPORT_LLM_TOOL_RESULT_LIMIT || report.tool_result_limit?.effective || 3000) * 5) / 4) }} tokens</div>
                  <div class="budget-total">Output: {{ form.REPORT_LLM_MAX_TOKENS || report.max_tokens?.effective || 4096 }} tokens</div>
                </div>
              </div>
            </div>
          </section>
        </div>

        <!-- Footer -->
        <div v-if="!loading" class="modal-footer">
          <span v-if="saveStatus" class="save-status" :class="saveStatus">
            {{ saveStatus === 'success' ? '✓ Saved' : '✗ Save failed' }}
          </span>
          <div class="footer-buttons">
            <button class="btn-cancel" @click="close">Cancel</button>
            <button class="btn-save" :disabled="saving" @click="save">
              {{ saving ? 'Saving...' : 'Save Settings' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'
import { getLlmSettings, saveLlmSettings } from '../api/settings'

const props = defineProps({
  visible: { type: Boolean, default: false }
})
const emit = defineEmits(['update:visible'])

const loading = ref(false)
const saving = ref(false)
const saveStatus = ref('')

const shared = ref({})
const simulation = ref({})
const report = ref({})

const showAdvanced = ref(false)
const activePreset = ref('')

const form = ref({
  SIMULATION_LLM_API_KEY: '',
  SIMULATION_LLM_BASE_URL: '',
  SIMULATION_LLM_MODEL_NAME: '',
  REPORT_LLM_API_KEY: '',
  REPORT_LLM_BASE_URL: '',
  REPORT_LLM_MODEL_NAME: '',
  REPORT_LLM_MAX_TOKENS: '',
  REPORT_LLM_TEMPERATURE: '',
  REPORT_LLM_TOOL_RESULT_LIMIT: '',
  REPORT_LLM_SIM_REQ_LIMIT: '',
  REPORT_LLM_PREV_SECTION_LIMIT: '',
})

const PARAM_LABELS = {
  max_tokens:         'Max Output Tokens',
  temperature:        'Temperature',
  tool_result_limit:  'Tool Result Limit (chars)',
  sim_req_limit:      'Sim Req Limit (chars)',
  prev_section_limit: 'Prev Section Limit (chars)',
}

const PARAM_DESCS = {
  max_tokens:         'tokens per section',
  temperature:        'creativity',
  tool_result_limit:  'per tool call',
  sim_req_limit:      'in system prompt',
  prev_section_limit: 'context continuity',
}

const PRESETS = {
  claude: {
    label: 'Claude API',
    REPORT_LLM_BASE_URL: 'https://api.anthropic.com/v1',
    REPORT_LLM_MODEL_NAME: 'claude-sonnet-4-6',
    // Claude: 200k context → no truncation needed, large output
    params: { max_tokens: 8192, temperature: 0.5, tool_result_limit: 20000, sim_req_limit: 8000, prev_section_limit: 4000 },
  },
  openai: {
    label: 'OpenAI',
    REPORT_LLM_BASE_URL: 'https://api.openai.com/v1',
    REPORT_LLM_MODEL_NAME: 'gpt-4o',
    // GPT-4o: 128k context
    params: { max_tokens: 8192, temperature: 0.5, tool_result_limit: 15000, sim_req_limit: 5000, prev_section_limit: 3000 },
  },
  openrouter: {
    label: 'OpenRouter',
    REPORT_LLM_BASE_URL: 'https://openrouter.ai/api/v1',
    REPORT_LLM_MODEL_NAME: 'anthropic/claude-sonnet-4-5',
    // OpenRouter/Claude: 200k context
    params: { max_tokens: 8192, temperature: 0.5, tool_result_limit: 20000, sim_req_limit: 8000, prev_section_limit: 4000 },
  },
  vllm: {
    label: 'Local vLLM',
    REPORT_LLM_BASE_URL: 'http://192.168.0.150:8001/v1',
    REPORT_LLM_MODEL_NAME: 'Qwen/Qwen3-32B',
    // Qwen3-32B: 40960 max context — tight budget
    params: { max_tokens: 4096, temperature: 0.5, tool_result_limit: 3000, sim_req_limit: 800, prev_section_limit: 1000 },
  },
}

const presetList = Object.entries(PRESETS).map(([key, v]) => ({ key, label: v.label }))

function applyPreset(name) {
  const preset = PRESETS[name]
  if (!preset) return
  activePreset.value = name
  showAdvanced.value = true
  form.value.REPORT_LLM_BASE_URL = preset.REPORT_LLM_BASE_URL
  form.value.REPORT_LLM_MODEL_NAME = preset.REPORT_LLM_MODEL_NAME
}

function applyPresetParams(name) {
  const preset = PRESETS[name]
  if (!preset?.params) return
  form.value.REPORT_LLM_MAX_TOKENS = preset.params.max_tokens
  form.value.REPORT_LLM_TEMPERATURE = preset.params.temperature
  form.value.REPORT_LLM_TOOL_RESULT_LIMIT = preset.params.tool_result_limit
  form.value.REPORT_LLM_SIM_REQ_LIMIT = preset.params.sim_req_limit
  form.value.REPORT_LLM_PREV_SECTION_LIMIT = preset.params.prev_section_limit
}

function clearReport() {
  form.value.REPORT_LLM_API_KEY = ''
  form.value.REPORT_LLM_BASE_URL = ''
  form.value.REPORT_LLM_MODEL_NAME = ''
  form.value.REPORT_LLM_MAX_TOKENS = ''
  form.value.REPORT_LLM_TEMPERATURE = ''
  form.value.REPORT_LLM_TOOL_RESULT_LIMIT = ''
  form.value.REPORT_LLM_SIM_REQ_LIMIT = ''
  form.value.REPORT_LLM_PREV_SECTION_LIMIT = ''
  activePreset.value = ''
}

async function loadSettings() {
  loading.value = true
  try {
    const res = await getLlmSettings()
    shared.value = res.data.shared || {}
    simulation.value = res.data.simulation || {}
    report.value = res.data.report || {}
    // Pre-fill stored values (non-masked)
    form.value.SIMULATION_LLM_BASE_URL = simulation.value.base_url?.value || ''
    form.value.SIMULATION_LLM_MODEL_NAME = simulation.value.model?.value || ''
    form.value.REPORT_LLM_BASE_URL = report.value.base_url?.value || ''
    form.value.REPORT_LLM_MODEL_NAME = report.value.model?.value || ''
    // Generation parameters (empty = use default)
    form.value.REPORT_LLM_MAX_TOKENS = report.value.max_tokens?.value || ''
    form.value.REPORT_LLM_TEMPERATURE = report.value.temperature?.value || ''
    form.value.REPORT_LLM_TOOL_RESULT_LIMIT = report.value.tool_result_limit?.value || ''
    form.value.REPORT_LLM_SIM_REQ_LIMIT = report.value.sim_req_limit?.value || ''
    form.value.REPORT_LLM_PREV_SECTION_LIMIT = report.value.prev_section_limit?.value || ''
    // API keys: leave blank (masked, user must re-enter to change)
  } catch (e) {
    console.error('Failed to load settings', e)
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  saveStatus.value = ''
  try {
    await saveLlmSettings(form.value)
    saveStatus.value = 'success'
    await loadSettings() // Refresh displayed values
    setTimeout(() => { saveStatus.value = '' }, 3000)
  } catch (e) {
    saveStatus.value = 'error'
    console.error('Failed to save settings', e)
  } finally {
    saving.value = false
  }
}

function close() {
  emit('update:visible', false)
}

watch(() => props.visible, (val) => {
  if (val) loadSettings()
})
</script>

<style scoped>
.settings-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  backdrop-filter: blur(2px);
}

.settings-modal {
  background: #fff;
  border: 2px solid #000;
  width: 680px;
  max-width: 95vw;
  max-height: 88vh;
  display: flex;
  flex-direction: column;
  font-family: 'JetBrains Mono', monospace;
  box-shadow: 6px 6px 0 #000;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 2px solid #000;
  background: #000;
  color: #fff;
  flex-shrink: 0;
}

.modal-title {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.05em;
}

.modal-title .icon { margin-right: 8px; }

.close-btn {
  background: none;
  border: 1px solid #fff;
  color: #fff;
  width: 26px;
  height: 26px;
  cursor: pointer;
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover { background: #333; }

.modal-loading {
  padding: 40px;
  text-align: center;
  color: #666;
  font-size: 13px;
}

.modal-body {
  overflow-y: auto;
  padding: 20px;
  flex: 1;
}

.modal-desc {
  font-size: 12px;
  color: #555;
  margin-bottom: 20px;
  line-height: 1.6;
}

.modal-desc code {
  background: #f0f0f0;
  padding: 1px 5px;
  font-family: inherit;
}

/* Section */
.settings-section {
  border: 1px solid #ddd;
  margin-bottom: 16px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 14px;
  background: #f8f8f8;
  border-bottom: 1px solid #ddd;
  font-size: 12px;
  font-weight: 700;
}

.section-hint {
  font-weight: 400;
  color: #888;
  font-size: 11px;
}

.badge {
  padding: 2px 7px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.05em;
  border: 1px solid;
}

.badge-default { background: #e8e8e8; border-color: #999; color: #555; }
.badge-sim     { background: #e8f0ff; border-color: #4477cc; color: #2255aa; }
.badge-report  { background: #fff0e0; border-color: #cc7700; color: #995500; }

/* Shared info rows */
.info-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0;
  padding: 12px 14px;
}

.info-item label {
  display: block;
  font-size: 10px;
  color: #888;
  margin-bottom: 3px;
  text-transform: uppercase;
}

.info-value {
  font-size: 12px;
  color: #333;
  word-break: break-all;
}

.info-value.not-set { color: #ccc; font-style: italic; }

/* Field grid */
.field-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 0;
}

.field-item {
  padding: 12px 14px;
  border-right: 1px solid #eee;
}

.field-item:last-child { border-right: none; }

.field-item label {
  display: block;
  font-size: 10px;
  color: #888;
  text-transform: uppercase;
  margin-bottom: 5px;
}

.field-item input {
  width: 100%;
  padding: 6px 8px;
  border: 1px solid #ccc;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  outline: none;
  box-sizing: border-box;
  color: #333;
}

.field-item input:focus { border-color: #000; }

/* Effective row */
.effective-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  background: #fafafa;
  border-bottom: 1px solid #eee;
  font-size: 11px;
}

.effective-label { color: #888; }
.effective-value { color: #333; font-weight: 600; }

/* Presets */
.presets-section .preset-buttons {
  display: flex;
  gap: 8px;
  padding: 12px 14px;
  flex-wrap: wrap;
}

.preset-btn {
  padding: 5px 12px;
  border: 1px solid #000;
  background: #fff;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  cursor: pointer;
  font-weight: 600;
}

.preset-btn:hover { background: #000; color: #fff; }
.preset-btn.preset-active { background: #000; color: #fff; }
.preset-clear { border-color: #999; color: #999; }
.preset-clear:hover { background: #999; color: #fff; }

/* Preset hint */
.preset-hint {
  margin: 0 14px 12px;
  border: 1px solid #e0e0e0;
  background: #fafafa;
  padding: 10px 12px;
}

.hint-title {
  font-size: 11px;
  color: #555;
  margin-bottom: 8px;
}

.hint-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 6px;
  margin-bottom: 10px;
}

.hint-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.hint-key {
  font-size: 10px;
  color: #888;
  text-transform: uppercase;
}

.hint-val {
  font-size: 13px;
  font-weight: 700;
  color: #000;
}

.hint-desc {
  font-size: 10px;
  color: #aaa;
}

.btn-apply-params {
  padding: 5px 12px;
  border: 1px solid #000;
  background: #fff;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  cursor: pointer;
  font-weight: 600;
}
.btn-apply-params:hover { background: #000; color: #fff; }

/* Advanced parameters grid */
.field-grid-2 {
  grid-template-columns: repeat(2, 1fr);
}

.field-item-info {
  background: #f8f8f8;
}

.field-hint {
  font-weight: 400;
  color: #aaa;
  font-size: 10px;
  margin-left: 4px;
}

.budget-info {
  font-size: 11px;
  line-height: 1.8;
  color: #555;
}

.budget-total {
  color: #000;
  font-weight: 700;
  margin-top: 4px;
  border-top: 1px solid #ddd;
  padding-top: 4px;
}

.toggle-arrow {
  margin-left: auto;
  font-size: 11px;
  color: #888;
}

/* Footer */
.modal-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  border-top: 2px solid #000;
  background: #f8f8f8;
  flex-shrink: 0;
}

.save-status {
  font-size: 12px;
  font-weight: 700;
}

.save-status.success { color: #2a7a2a; }
.save-status.error   { color: #cc2222; }

.footer-buttons { display: flex; gap: 8px; }

.btn-cancel, .btn-save {
  padding: 7px 18px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  border: 2px solid #000;
}

.btn-cancel { background: #fff; color: #000; }
.btn-cancel:hover { background: #f0f0f0; }

.btn-save { background: #000; color: #fff; }
.btn-save:hover { background: #333; }
.btn-save:disabled { background: #888; border-color: #888; cursor: not-allowed; }
</style>
