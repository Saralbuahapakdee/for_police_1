<template>
  <div class="cameras-tab">

    <!-- ── Header ── -->
    <div class="cameras-header">
      <div>
        <h2>📷 Camera Management</h2>
        <p class="header-sub">Configure cameras, RTSP streams, and MQTT detection topics</p>
      </div>
      <button @click="openCreateModal" class="create-btn">➕ Add Camera</button>
    </div>

    <!-- ── How it works ── -->
    <div class="info-box">
      <div class="info-title">🔗 How cameras link to AI detections</div>
      <div class="info-flow">
        <div class="flow-step">
          <div class="flow-icon">🤖</div>
          <div class="flow-label">AI Model</div>
          <div class="flow-desc">Detects weapons in video feed</div>
        </div>
        <div class="flow-arrow">→</div>
        <div class="flow-step">
          <div class="flow-icon">📡</div>
          <div class="flow-label">MQTT Topic</div>
          <div class="flow-desc">AI publishes result to a topic<br><code>e.g. cam/entrance</code></div>
        </div>
        <div class="flow-arrow">→</div>
        <div class="flow-step">
          <div class="flow-icon">🗄️</div>
          <div class="flow-label">This System</div>
          <div class="flow-desc">Matches topic → Camera ID<br>logs incident + image</div>
        </div>
        <div class="flow-arrow">→</div>
        <div class="flow-step">
          <div class="flow-icon">📹</div>
          <div class="flow-label">RTSP Stream</div>
          <div class="flow-desc">Live video shown in<br>Live Stream tab</div>
        </div>
      </div>
      <div class="info-tips">
        <span class="tip">💡 <strong>MQTT Topic:</strong> Must match exactly what your AI model publishes to. Use <code>#</code> (wildcard) to match all topics — the system will then use the <code>camera_id</code> field inside the JSON payload to identify the camera.</span>
        <span class="tip">💡 <strong>RTSP URL:</strong> Used only for the live video display. Not required for detection logging.</span>
      </div>
    </div>

    <!-- ── Stats ── -->
    <div class="stats-row">
      <div class="stat-card active-stat">
        <div class="stat-icon">🟢</div>
        <div class="stat-info">
          <div class="stat-value">{{ cameras.filter(c => c.is_active).length }}</div>
          <div class="stat-label">Active</div>
        </div>
      </div>
      <div class="stat-card mqtt-stat">
        <div class="stat-icon">📡</div>
        <div class="stat-info">
          <div class="stat-value">{{ cameras.filter(c => c.mqtt_topic).length }}</div>
          <div class="stat-label">With MQTT</div>
        </div>
      </div>
      <div class="stat-card rtsp-stat">
        <div class="stat-icon">📹</div>
        <div class="stat-info">
          <div class="stat-value">{{ cameras.filter(c => c.rtsp_url).length }}</div>
          <div class="stat-label">With Stream</div>
        </div>
      </div>
      <div class="stat-card total-stat">
        <div class="stat-icon">📷</div>
        <div class="stat-info">
          <div class="stat-value">{{ cameras.length }}</div>
          <div class="stat-label">Total</div>
        </div>
      </div>
    </div>

    <!-- ── Camera Cards ── -->
    <div class="cameras-list">
      <div v-if="isLoading" class="loading">Loading cameras...</div>
      <div v-else-if="cameras.length === 0" class="no-cameras">
        No cameras configured yet. Click "Add Camera" to get started.
      </div>
      <div v-else class="camera-cards">
        <div v-for="camera in cameras" :key="camera.id" :class="['camera-card', { inactive: !camera.is_active }]">
          <div :class="['status-strip', camera.is_active ? 'active' : 'inactive']"></div>
          <div class="camera-card-body">

            <!-- Title row -->
            <div class="camera-title-row">
              <div class="camera-title-left">
                <span class="camera-icon-emoji">📷</span>
                <div>
                  <h3 class="camera-name">{{ camera.camera_name }}</h3>
                  <p class="camera-location">📍 {{ camera.location }}</p>
                </div>
              </div>
              <div class="camera-badges">
                <span :class="['status-badge', camera.is_active ? 'active' : 'inactive']">
                  {{ camera.is_active ? '🟢 Active' : '🔴 Inactive' }}
                </span>
                <span class="id-badge">ID: {{ camera.id }}</span>
              </div>
            </div>

            <p v-if="camera.description" class="camera-description">{{ camera.description }}</p>

            <!-- Config rows -->
            <div class="config-rows">
              <div class="config-row" :class="{ 'config-missing': !camera.mqtt_topic }">
                <div class="config-icon">📡</div>
                <div class="config-content">
                  <div class="config-label">MQTT Topic</div>
                  <div v-if="camera.mqtt_topic" class="config-value">
                    <code>{{ camera.mqtt_topic }}</code>
                  </div>
                  <div v-else class="config-empty">⚠️ Not configured — detections won't link to this camera</div>
                </div>
              </div>

              <div class="config-row" :class="{ 'config-missing': !camera.rtsp_url }">
                <div class="config-icon">📹</div>
                <div class="config-content">
                  <div class="config-label">RTSP Stream</div>
                  <div v-if="camera.rtsp_url" class="config-value">
                    <code>{{ maskRtsp(camera.rtsp_url) }}</code>
                  </div>
                  <div v-else class="config-empty">No live stream configured</div>
                </div>
              </div>
            </div>

            <!-- Actions -->
            <div class="camera-actions">
              <button @click="openEditModal(camera)" class="action-btn edit-btn">✏️ Edit</button>
              <button @click="toggleStatus(camera)"
                :class="['action-btn', camera.is_active ? 'deactivate-btn' : 'activate-btn']"
                :disabled="togglingId === camera.id">
                {{ togglingId === camera.id ? '...' : (camera.is_active ? '⏸ Deactivate' : '▶ Activate') }}
              </button>
              <button @click="confirmDelete(camera)" class="action-btn delete-btn">🗑️ Delete</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Create / Edit Modal ── -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <div class="modal-header">
          <h3>{{ editingCamera ? '✏️ Edit Camera' : '➕ Add New Camera' }}</h3>
          <button @click="closeModal" class="close-btn">✕</button>
        </div>

        <div class="modal-body">

          <!-- Basic Info -->
          <div class="form-section">
            <div class="section-title">📋 Basic Information</div>
            <div class="form-row-2">
              <div class="form-group">
                <label>Camera Name <span class="required">*</span></label>
                <input v-model="form.camera_name" class="input-field" placeholder="e.g. Main Entrance" @input="clearMessages" />
              </div>
              <div class="form-group">
                <label>Location <span class="required">*</span></label>
                <input v-model="form.location" class="input-field" placeholder="e.g. Building A - Front Gate" @input="clearMessages" />
              </div>
            </div>
            <div class="form-group">
              <label>Description</label>
              <textarea v-model="form.description" class="input-field textarea" placeholder="What does this camera monitor?" rows="2" @input="clearMessages"></textarea>
            </div>
            <div class="form-group">
              <label class="checkbox-label">
                <input type="checkbox" v-model="form.is_active" class="checkbox" />
                <span>Camera is active and online</span>
              </label>
            </div>
          </div>

          <!-- MQTT -->
          <div class="form-section">
            <div class="section-title">📡 MQTT Detection Topic</div>
            <div class="section-hint">
              The MQTT topic your AI model publishes weapon detection results to.
              The system uses this to know <strong>which camera triggered the alert</strong>.
            </div>

            <div class="form-group">
              <label>MQTT Topic</label>
              <input v-model="form.mqtt_topic" class="input-field" placeholder='e.g. cam/entrance' @input="clearMessages" />
            </div>

            <div class="mqtt-examples">
              <div class="example-title">Click a pattern to use it:</div>
              <div class="examples-grid">

                <div class="example-item" @click="form.mqtt_topic = 'detection/camera/' + (form.camera_name || 'cam').toLowerCase().replace(/ /g,'_')">
                  <code>detection/camera/{{ (form.camera_name || 'cam').toLowerCase().replace(/ /g,'_') }}</code>
                  <span>Exact topic per camera (recommended)</span>
                </div>
                <div class="example-item" @click="form.mqtt_topic = 'weapons/' + (editingCamera ? editingCamera.id : 'N')">
                  <code>weapons/{{ editingCamera ? editingCamera.id : 'N' }}</code>
                  <span>Topic by camera ID number</span>
                </div>
              </div>
            </div>

            <div class="payload-preview">
              <div class="payload-title">Expected MQTT payload format:</div>
              <pre class="payload-code">{
  "detected": true,
  "objects": {
    "pistol": {
      "confidences": [0.92],
      "boxes": [[x1, y1, x2, y2]]
    }
  }
}</pre>
              <div class="payload-note">
                ℹ️ The camera is identified strictly by the MQTT topic. No camera ID mapping in the JSON payload is needed!
              </div>
            </div>
          </div>

          <!-- RTSP -->
          <div class="form-section">
            <div class="section-title">📹 RTSP Live Stream</div>
            <div class="section-hint">
              Used only for displaying live video in the "Live Stream" tab.
              Detections are logged regardless of whether an RTSP stream is configured.
            </div>
            <div class="form-group">
              <label>RTSP URL</label>
              <input v-model="form.rtsp_url" class="input-field" placeholder="rtsp://username:password@192.168.1.100:554/stream" @input="clearMessages" />
              <p class="field-hint">Credentials in the URL are masked when displayed in the camera list</p>
            </div>
            <div class="rtsp-format-box">
              <span class="rtsp-format-label">Format:</span>
              <code>rtsp://[user]:[password]@[ip_address]:[port]/[stream_path]</code>
            </div>
          </div>

          <div v-if="formError" class="error-message">{{ formError }}</div>
          <div v-if="formSuccess" class="success-message">{{ formSuccess }}</div>
        </div>

        <div class="modal-footer">
          <button @click="closeModal" class="cancel-btn">Cancel</button>
          <button @click="saveCamera" class="save-btn" :disabled="isSaving">
            {{ isSaving ? 'Saving...' : (editingCamera ? 'Save Changes' : 'Add Camera') }}
          </button>
        </div>
      </div>
    </div>

    <!-- ── Delete Modal ── -->
    <div v-if="showDeleteModal" class="modal-overlay" @click.self="showDeleteModal = false">
      <div class="modal modal-sm">
        <div class="modal-header danger-header">
          <h3>🗑️ Delete Camera</h3>
          <button @click="showDeleteModal = false" class="close-btn">✕</button>
        </div>
        <div class="modal-body">
          <p class="confirm-text">Delete <strong>{{ cameraToDelete?.camera_name }}</strong>?</p>
          <div class="warning-box">
            ⚠️ Cameras with existing detection logs or incidents cannot be deleted.
            Use <strong>Deactivate</strong> instead to hide it from monitoring without losing data.
          </div>
          <div v-if="deleteError" class="error-message" style="margin-top:12px">{{ deleteError }}</div>
        </div>
        <div class="modal-footer">
          <button @click="showDeleteModal = false" class="cancel-btn">Cancel</button>
          <button @click="executeDelete" class="delete-confirm-btn" :disabled="isDeleting">
            {{ isDeleting ? 'Deleting...' : 'Yes, Delete' }}
          </button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const props = defineProps({ token: String })

const cameras    = ref([])
const isLoading  = ref(false)
const togglingId = ref(null)

const showModal     = ref(false)
const editingCamera = ref(null)
const isSaving      = ref(false)
const formError     = ref('')
const formSuccess   = ref('')

const emptyForm = () => ({
  camera_name: '', location: '', description: '',
  rtsp_url: '', mqtt_topic: '', is_active: true,
})
const form = ref(emptyForm())

const showDeleteModal = ref(false)
const cameraToDelete  = ref(null)
const isDeleting      = ref(false)
const deleteError     = ref('')

onMounted(loadCameras)

async function loadCameras() {
  isLoading.value = true
  try {
    const res = await fetch('/api/admin/cameras', {
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) cameras.value = (await res.json()).cameras
  } catch (e) { console.error(e) }
  isLoading.value = false
}

function openCreateModal() {
  editingCamera.value = null
  form.value = emptyForm()
  clearMessages()
  showModal.value = true
}

function openEditModal(camera) {
  editingCamera.value = camera
  form.value = {
    camera_name: camera.camera_name,
    location:    camera.location,
    description: camera.description  || '',
    rtsp_url:    camera.rtsp_url     || '',
    mqtt_topic:  camera.mqtt_topic   || '',
    is_active:   Boolean(camera.is_active),
  }
  clearMessages()
  showModal.value = true
}

function closeModal() {
  showModal.value = false
  editingCamera.value = null
  clearMessages()
}

function clearMessages() {
  formError.value = formSuccess.value = deleteError.value = ''
}

async function saveCamera() {
  clearMessages()
  if (!form.value.camera_name.trim()) { formError.value = 'Camera name is required'; return }
  if (!form.value.location.trim())    { formError.value = 'Location is required';    return }

  isSaving.value = true
  try {
    const url    = editingCamera.value ? `/api/admin/cameras/${editingCamera.value.id}` : '/api/admin/cameras'
    const method = editingCamera.value ? 'PUT' : 'POST'
    const res    = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${props.token}` },
      body: JSON.stringify(form.value),
    })
    const data = await res.json()
    if (res.ok) {
      formSuccess.value = editingCamera.value ? 'Camera updated!' : 'Camera added!'
      await loadCameras()
      setTimeout(closeModal, 1200)
    } else {
      formError.value = data.error || 'Failed to save camera'
    }
  } catch { formError.value = 'Network error. Please try again.' }
  isSaving.value = false
}

async function toggleStatus(camera) {
  togglingId.value = camera.id
  try {
    const res = await fetch(`/api/admin/cameras/${camera.id}/toggle`, {
      method: 'PATCH', headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) await loadCameras()
  } catch (e) { console.error(e) }
  togglingId.value = null
}

function confirmDelete(camera) {
  cameraToDelete.value  = camera
  deleteError.value     = ''
  showDeleteModal.value = true
}

async function executeDelete() {
  if (!cameraToDelete.value) return
  isDeleting.value = true; deleteError.value = ''
  try {
    const res  = await fetch(`/api/admin/cameras/${cameraToDelete.value.id}`, {
      method: 'DELETE', headers: { 'Authorization': `Bearer ${props.token}` }
    })
    const data = await res.json()
    if (res.ok) { showDeleteModal.value = false; cameraToDelete.value = null; await loadCameras() }
    else deleteError.value = data.error || 'Failed to delete camera'
  } catch { deleteError.value = 'Network error.' }
  isDeleting.value = false
}

function maskRtsp(url) {
  if (!url) return ''
  try { return url.replace(/(rtsp:\/\/)[^@]+@/, '$1***:***@') }
  catch { return url.length > 55 ? url.slice(0, 52) + '...' : url }
}
</script>

<style scoped>
.cameras-tab { display: flex; flex-direction: column; gap: 20px; }

/* Header */
.cameras-header {
  background: white; padding: 20px 25px; border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,.08);
  display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px;
}
.cameras-header h2 { color: #2c3e50; margin: 0 0 4px; font-size: 1.4rem; }
.header-sub { color: #7f8c8d; margin: 0; font-size: .9rem; }

.create-btn {
  padding: 10px 22px;
  background: linear-gradient(135deg,#27ae60,#2ecc71);
  color: white; border: none; border-radius: 8px; cursor: pointer;
  font-size: .95rem; font-weight: 600;
  box-shadow: 0 3px 10px rgba(39,174,96,.3); transition: all .25s;
}
.create-btn:hover { transform: translateY(-2px); box-shadow: 0 5px 16px rgba(39,174,96,.4); }

/* Info box */
.info-box {
  background: #f0f7ff; border: 1px solid #c5d8f0; border-radius: 12px; padding: 18px 22px;
}
.info-title { font-weight: 700; color: #1e3c72; margin-bottom: 14px; font-size: .95rem; }
.info-flow { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 14px; }
.flow-step {
  background: white; border: 1px solid #d0e4f7; border-radius: 10px;
  padding: 12px 16px; text-align: center; min-width: 120px; flex: 1;
}
.flow-icon  { font-size: 1.8rem; margin-bottom: 5px; }
.flow-label { font-weight: 700; color: #2c3e50; font-size: .88rem; margin-bottom: 3px; }
.flow-desc  { font-size: .77rem; color: #5d6d7e; line-height: 1.4; }
.flow-arrow { font-size: 1.3rem; color: #3498db; font-weight: 700; flex-shrink: 0; }
.info-tips  { display: flex; flex-direction: column; gap: 6px; }
.tip {
  font-size: .84rem; color: #2c3e50;
  background: white; border-left: 3px solid #3498db;
  padding: 7px 12px; border-radius: 0 6px 6px 0;
}
.tip code { background: #e8f4fd; padding: 1px 5px; border-radius: 3px; font-size: .8rem; }

/* Stats */
.stats-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 14px; }
.stat-card {
  background: white; padding: 16px 18px; border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,.08);
  display: flex; align-items: center; gap: 14px; border-left: 4px solid #ddd;
}
.active-stat { border-left-color: #27ae60; }
.mqtt-stat   { border-left-color: #9b59b6; }
.rtsp-stat   { border-left-color: #3498db; }
.total-stat  { border-left-color: #95a5a6; }
.stat-icon  { font-size: 1.9rem; }
.stat-value { font-size: 1.8rem; font-weight: 700; color: #2c3e50; line-height: 1; }
.stat-label { font-size: .8rem; color: #7f8c8d; text-transform: uppercase; letter-spacing: .5px; margin-top: 3px; }

/* Camera list */
.cameras-list {
  background: white; padding: 20px; border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,.08); min-height: 200px;
}
.loading, .no-cameras { text-align: center; padding: 60px; color: #7f8c8d; font-style: italic; }
.camera-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(400px,1fr)); gap: 16px; }

/* Camera card */
.camera-card {
  border-radius: 10px; border: 1px solid #e0e6ed; overflow: hidden;
  background: #fafbfc; transition: all .25s; display: flex; flex-direction: column;
}
.camera-card:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,.1); }
.camera-card.inactive { opacity: .68; background: #f4f4f4; }

.status-strip { height: 4px; }
.status-strip.active   { background: linear-gradient(90deg,#27ae60,#2ecc71); }
.status-strip.inactive { background: linear-gradient(90deg,#95a5a6,#bdc3c7); }

.camera-card-body { padding: 16px; display: flex; flex-direction: column; gap: 12px; }

.camera-title-row {
  display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; flex-wrap: wrap;
}
.camera-title-left { display: flex; gap: 11px; align-items: flex-start; }
.camera-icon-emoji { font-size: 2rem; line-height: 1; margin-top: 2px; }
.camera-name     { margin: 0 0 3px; font-size: 1rem; font-weight: 700; color: #2c3e50; }
.camera-location { margin: 0; font-size: .84rem; color: #5d6d7e; }
.camera-description { margin: 0; font-size: .82rem; color: #7f8c8d; font-style: italic; }

.camera-badges { display: flex; gap: 6px; flex-wrap: wrap; align-items: flex-start; }
.status-badge {
  padding: 3px 10px; border-radius: 10px; font-size: .77rem; font-weight: 600;
}
.status-badge.active   { background: #d4edda; color: #27ae60; }
.status-badge.inactive { background: #f2f3f4; color: #7f8c8d; }
.id-badge { padding: 3px 10px; border-radius: 10px; font-size: .77rem; font-weight: 600; background: #e8f4fd; color: #3498db; }

/* Config rows on card */
.config-rows { display: flex; flex-direction: column; gap: 7px; }
.config-row {
  display: flex; gap: 9px; align-items: flex-start;
  background: #f0f7ff; border-radius: 8px; padding: 9px 12px;
  border-left: 3px solid #3498db;
}
.config-row.config-missing { background: #fafafa; border-left-color: #e0e0e0; }
.config-icon  { font-size: 1.05rem; flex-shrink: 0; margin-top: 2px; }
.config-label { font-size: .72rem; font-weight: 700; color: #7f8c8d; text-transform: uppercase; letter-spacing: .5px; margin-bottom: 4px; }
.config-value code {
  font-family: 'Courier New', monospace; font-size: .8rem; color: #2c3e50;
  background: white; padding: 1px 6px; border-radius: 3px; border: 1px solid #dce1e7; word-break: break-all;
}
.config-empty { font-size: .82rem; color: #b2bec3; font-style: italic; }
.wildcard-badge {
  display: inline-block; margin-left: 7px; padding: 1px 8px;
  background: #9b59b6; color: white; border-radius: 8px;
  font-size: .7rem; font-weight: 700; vertical-align: middle;
}

/* Card actions */
.camera-actions { display: flex; gap: 7px; flex-wrap: wrap; }
.action-btn {
  flex: 1; min-width: 72px; padding: 7px 10px;
  border: none; border-radius: 6px; cursor: pointer; font-size: .82rem; font-weight: 600; transition: all .2s;
}
.edit-btn         { background: #e8f4fd; color: #2980b9; }
.edit-btn:hover   { background: #cce5ff; }
.deactivate-btn   { background: #fff3cd; color: #e67e22; }
.deactivate-btn:hover { background: #fdebd0; }
.activate-btn     { background: #d4edda; color: #27ae60; }
.activate-btn:hover { background: #c3e6cb; }
.delete-btn       { background: #fde8e8; color: #e74c3c; }
.delete-btn:hover { background: #f8c5c5; }
.action-btn:disabled { opacity: .6; cursor: not-allowed; }

/* Modal */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.55);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000; padding: 20px; backdrop-filter: blur(2px);
}
.modal {
  background: white; border-radius: 14px; width: 100%; max-width: 660px;
  max-height: 92vh; overflow-y: auto; box-shadow: 0 20px 60px rgba(0,0,0,.25);
  display: flex; flex-direction: column;
}
.modal-sm { max-width: 420px; }

.modal-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 17px 22px; border-bottom: 1px solid #e8ecef;
  background: #f8f9fa; border-radius: 14px 14px 0 0;
  position: sticky; top: 0; z-index: 1;
}
.danger-header { background: #fde8e8; }
.modal-header h3 { margin: 0; color: #2c3e50; font-size: 1.05rem; }
.close-btn { background: none; border: none; font-size: 1.4rem; cursor: pointer; color: #7f8c8d; transition: color .2s; }
.close-btn:hover { color: #2c3e50; }

.modal-body { padding: 20px 22px; flex: 1; }

.form-section {
  margin-bottom: 24px; padding-bottom: 20px; border-bottom: 1px solid #ecf0f1;
}
.form-section:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }

.section-title { font-size: .94rem; font-weight: 700; color: #2c3e50; margin-bottom: 6px; }
.section-hint  { font-size: .84rem; color: #7f8c8d; margin-bottom: 13px; line-height: 1.5; }

.form-row-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 13px; }
.form-group { margin-bottom: 13px; }
.form-group:last-child { margin-bottom: 0; }
.form-group label { display: block; margin-bottom: 6px; font-weight: 600; color: #2c3e50; font-size: .88rem; }
.required { color: #e74c3c; }

.input-field {
  width: 100%; padding: 9px 12px; border: 2px solid #e0e0e0; border-radius: 7px;
  font-size: .93rem; transition: border-color .25s; box-sizing: border-box; font-family: inherit;
}
.input-field:focus { border-color: #3498db; outline: none; }
.textarea { resize: vertical; min-height: 65px; }
.field-hint { margin: 4px 0 0; font-size: .77rem; color: #95a5a6; }

.checkbox-label { display: flex; align-items: center; gap: 9px; cursor: pointer; font-weight: 600; color: #2c3e50; font-size: .88rem; }
.checkbox { width: 16px; height: 16px; cursor: pointer; accent-color: #27ae60; }

/* MQTT examples */
.mqtt-examples {
  background: #f8f9fa; border: 1px solid #e0e6ed;
  border-radius: 8px; padding: 11px 13px; margin-bottom: 13px;
}
.example-title { font-size: .75rem; font-weight: 700; color: #5d6d7e; margin-bottom: 8px; text-transform: uppercase; letter-spacing: .5px; }
.examples-grid { display: flex; flex-direction: column; gap: 5px; }
.example-item {
  display: flex; gap: 10px; align-items: baseline;
  padding: 7px 10px; background: white; border: 1px solid #dce1e7;
  border-radius: 6px; cursor: pointer; transition: all .2s; font-size: .82rem;
}
.example-item:hover { border-color: #3498db; background: #f0f7ff; }
.example-item code { font-family: 'Courier New', monospace; color: #2980b9; font-weight: 700; flex-shrink: 0; }
.example-item span { color: #5d6d7e; line-height: 1.4; }

/* Payload preview */
.payload-preview {
  background: #1e2a3a; border-radius: 8px; padding: 13px 15px;
}
.payload-title  { font-size: .74rem; font-weight: 700; color: #7fb3d3; text-transform: uppercase; letter-spacing: .5px; margin-bottom: 7px; }
.payload-code   { font-family: 'Courier New', monospace; font-size: .8rem; color: #a8d8a8; margin: 0 0 9px; white-space: pre; line-height: 1.55; }
.payload-note   { font-size: .77rem; color: #8eacc4; line-height: 1.4; }
.payload-note code { color: #f0c08a; }

/* RTSP format */
.rtsp-format-box {
  margin-top: 10px; background: #f8f9fa; border: 1px solid #e0e6ed;
  border-radius: 7px; padding: 9px 13px; display: flex; align-items: center; gap: 10px;
}
.rtsp-format-label { font-size: .78rem; font-weight: 700; color: #5d6d7e; white-space: nowrap; }
.rtsp-format-box code { font-family: 'Courier New', monospace; font-size: .8rem; color: #2980b9; word-break: break-all; }

/* Messages */
.error-message   { background: #fde8e8; border: 1px solid #f5c6c6; color: #c0392b; padding: 10px 13px; border-radius: 7px; font-size: .88rem; margin-top: 10px; }
.success-message { background: #d4edda; border: 1px solid #c3e6cb; color: #27ae60; padding: 10px 13px; border-radius: 7px; font-size: .88rem; margin-top: 10px; }

/* Modal footer */
.modal-footer {
  display: flex; gap: 10px; justify-content: flex-end;
  padding: 15px 22px; border-top: 1px solid #e8ecef;
  background: #f8f9fa; border-radius: 0 0 14px 14px;
  position: sticky; bottom: 0;
}
.cancel-btn { padding: 9px 20px; background: #ecf0f1; color: #2c3e50; border: none; border-radius: 7px; cursor: pointer; font-weight: 600; transition: background .2s; }
.cancel-btn:hover { background: #d5dbdb; }
.save-btn {
  padding: 9px 22px; background: linear-gradient(135deg,#2980b9,#3498db);
  color: white; border: none; border-radius: 7px; cursor: pointer; font-weight: 600;
  box-shadow: 0 3px 10px rgba(52,152,219,.3); transition: all .2s;
}
.save-btn:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 5px 14px rgba(52,152,219,.4); }
.save-btn:disabled { background: #bdc3c7; cursor: not-allowed; box-shadow: none; }

/* Delete modal */
.confirm-text { color: #2c3e50; margin-bottom: 13px; font-size: .98rem; }
.warning-box  { background: #fff3cd; border: 1px solid #ffc107; border-radius: 7px; padding: 10px 13px; font-size: .86rem; color: #856404; line-height: 1.5; }
.delete-confirm-btn {
  padding: 9px 22px; background: linear-gradient(135deg,#c0392b,#e74c3c);
  color: white; border: none; border-radius: 7px; cursor: pointer; font-weight: 600;
  box-shadow: 0 3px 10px rgba(231,76,60,.3); transition: all .2s;
}
.delete-confirm-btn:hover:not(:disabled) { transform: translateY(-1px); }
.delete-confirm-btn:disabled { background: #bdc3c7; cursor: not-allowed; box-shadow: none; }

/* Responsive */
@media (max-width: 900px) {
  .flow-arrow { display: none; }
  .camera-cards { grid-template-columns: 1fr; }
  .form-row-2 { grid-template-columns: 1fr; }
}
@media (max-width: 600px) {
  .cameras-header { flex-direction: column; align-items: flex-start; }
  .create-btn { width: 100%; text-align: center; }
  .stats-row { grid-template-columns: 1fr 1fr; }
}
</style>