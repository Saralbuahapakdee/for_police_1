<!-- src/tabs/incidents/IncidentModal.vue -->
<template>
  <div class="modal-overlay" @click="$emit('close')">
    <div class="modal-detail" @click.stop>
      <div class="modal-header">
        <h3>{{ incident.incident_number }}</h3>
        <button @click="$emit('close')" class="close-btn">✕</button>
      </div>
      
      <div class="modal-content">
        <!-- Incident Image Section -->
        <div v-if="incident.image_path" class="detail-section image-section">
          <h4>Captured Evidence</h4>
          <div class="incident-image-container">
            <img 
              :src="`/api/incident_images/${incident.image_path}`" 
              alt="Incident capture" 
              class="incident-image"
              @click="$emit('view-image', `/api/incident_images/${incident.image_path}`)"
              @error="handleImageError"
            />
            <div class="image-caption">
              Click image to view full screen
            </div>
          </div>
        </div>

        <div class="detail-section">
          <h4>Incident Details</h4>
          <div class="detail-grid">
            <div class="detail-item">
              <label>Incident ID:</label>
              <span class="incident-number-text">{{ incident.incident_number }}</span>
            </div>
            <div class="detail-item">
              <label>Status:</label>
              <span :class="['status-badge', incident.status]">
                {{ formatStatus(incident.status) }}
              </span>
            </div>
            <div class="detail-item">
              <label>Camera:</label>
              <span>{{ incident.camera_name }}</span>
            </div>
            <div class="detail-item">
              <label>Location:</label>
              <span>{{ incident.camera_location }}</span>
            </div>
            <div class="detail-item">
              <label>Weapon Type:</label>
              <span :class="['weapon-badge', incident.weapon_type]">
                {{ formatWeaponName(incident.weapon_type) }}
              </span>
            </div>
            <div class="detail-item">
              <label>Detected At:</label>
              <span>{{ formatDateTime(incident.detected_at) }}</span>
            </div>
            <div class="detail-item">
              <label>Created By:</label>
              <span>{{ incident.created_by_username }}</span>
            </div>
            <div v-if="incident.assigned_to_username" class="detail-item">
              <label>Assigned To:</label>
              <span>{{ incident.assigned_to_username }}</span>
            </div>
          </div>
        </div>

        <div v-if="incident.description" class="detail-section">
          <h4>Description</h4>
          <p class="description-text">{{ incident.description }}</p>
        </div>

        <div v-if="incident.response_notes" class="detail-section">
          <h4>Response Notes</h4>
          <p class="description-text">{{ incident.response_notes }}</p>
        </div>

        <div v-if="incident.resolution_notes" class="detail-section">
          <h4>Resolution Notes</h4>
          <p class="description-text">{{ incident.resolution_notes }}</p>
        </div>

        <div class="detail-section">
          <h4>Take Action</h4>
          
          <div v-if="incident.status === 'pending'" class="action-form">
            <div v-if="isAdmin" class="form-group">
              <label>Assign to Officer:</label>
              <select v-model="actionData.assigned_to" class="input-field">
                <option value="">Select Officer</option>
                <option v-for="officer in officers" :key="officer.id" :value="officer.id">
                  {{ officer.first_name }} {{ officer.last_name }} ({{ officer.badge_number }})
                </option>
              </select>
            </div>
            
            <div class="form-group">
              <label>Response Notes:</label>
              <textarea v-model="actionData.response_notes" class="textarea-field" 
                        placeholder="Enter response details..." rows="2"></textarea>
            </div>
            
            <button @click="handleStatusUpdate('responding')" class="action-btn responding">
              🟡 Start Responding
            </button>
          </div>
          
          <div v-else-if="incident.status === 'responding'" class="action-form">
            <div class="form-group">
              <label>Resolution Notes:</label>
              <textarea v-model="actionData.resolution_notes" class="textarea-field" 
                        placeholder="Enter resolution details..." rows="2"></textarea>
            </div>
            
            <button @click="handleStatusUpdate('resolved')" class="action-btn resolved">
              🟢 Mark as Resolved
            </button>
          </div>
          
          <div v-else class="resolved-message">
            ✓ This incident has been resolved
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  incident: Object,
  officers: Array,
  isAdmin: Boolean
})

const emit = defineEmits(['close', 'update-status', 'view-image'])

const actionData = ref({
  assigned_to: '',
  response_notes: '',
  resolution_notes: ''
})

watch(() => props.incident, (newIncident) => {
  if (newIncident) {
    actionData.value = {
      assigned_to: newIncident.assigned_to || '',
      response_notes: '',
      resolution_notes: ''
    }
  }
}, { immediate: true })

function handleImageError(event) {
  console.error('Failed to load image:', event.target.src)
  event.target.style.display = 'none'
}

function handleStatusUpdate(newStatus) {
  emit('update-status', newStatus, actionData.value)
}

function formatStatus(status) {
  const map = {
    'pending': 'Pending',
    'responding': 'Responding',
    'resolved': 'Resolved'
  }
  return map[status] || status
}

function formatWeaponName(weaponType) {
  const names = {
    'knife': 'Knife',
    'pistol': 'Pistol',
    'heavy_weapon': 'Heavy Weapon'
  }
  return names[weaponType] || weaponType
}

function formatDateTime(dateTimeString) {
  if (!dateTimeString) return 'N/A'
  try {
    const date = new Date(dateTimeString)
    return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`
  } catch {
    return dateTimeString
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-detail {
  background: white;
  border-radius: 12px;
  width: 100%;
  max-width: 800px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 25px;
  border-bottom: 1px solid #e0e0e0;
  background: #f8f9fa;
  border-radius: 12px 12px 0 0;
}

.modal-header h3 {
  color: #2c3e50;
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #7f8c8d;
  transition: color 0.3s ease;
}

.close-btn:hover {
  color: #2c3e50;
}

.modal-content {
  padding: 20px 25px;
  overflow-y: auto;
  flex: 1;
}

.detail-section {
  margin-bottom: 20px;
}

.detail-section.image-section {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
}

.detail-section h4 {
  color: #2c3e50;
  margin-bottom: 12px;
  border-bottom: 2px solid #e0e0e0;
  padding-bottom: 6px;
  font-size: 0.95rem;
}

.incident-image-container {
  text-align: center;
}

.incident-image {
  max-width: 100%;
  max-height: 400px;
  border-radius: 8px;
  cursor: pointer;
  transition: transform 0.3s ease;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.incident-image:hover {
  transform: scale(1.02);
}

.image-caption {
  margin-top: 10px;
  font-size: 0.85rem;
  color: #7f8c8d;
  font-style: italic;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.detail-item label {
  font-weight: 600;
  color: #7f8c8d;
  font-size: 0.85rem;
  text-transform: uppercase;
}

.incident-number-text {
  font-family: 'Courier New', monospace;
  font-weight: 600;
  color: #4a90e2;
}

.description-text {
  color: #2c3e50;
  line-height: 1.5;
}

.action-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-weight: 600;
  color: #2c3e50;
}

.input-field,
.textarea-field {
  padding: 8px 10px;
  border: 2px solid #e0e0e0;
  border-radius: 6px;
  transition: border-color 0.3s ease;
}

.input-field:focus,
.textarea-field:focus {
  border-color: #4a90e2;
  outline: none;
}

.textarea-field {
  resize: vertical;
  font-family: inherit;
}

.action-btn {
  padding: 12px 20px;
  border: none;
  border-radius: 8px;
  color: white;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.action-btn.responding {
  background: #f39c12;
}

.action-btn.responding:hover {
  background: #e67e22;
  transform: translateY(-2px);
}

.action-btn.resolved {
  background: #27ae60;
}

.action-btn.resolved:hover {
  background: #229954;
  transform: translateY(-2px);
}

.resolved-message {
  text-align: center;
  padding: 20px;
  background: #d4edda;
  color: #27ae60;
  border-radius: 8px;
  font-weight: 600;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  display: inline-block;
}

.status-badge.pending {
  background: #fee;
  color: #e74c3c;
}

.status-badge.responding {
  background: #fff3cd;
  color: #f39c12;
}

.status-badge.resolved {
  background: #d4edda;
  color: #27ae60;
}

.weapon-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.85rem;
  font-weight: 600;
  display: inline-block;
}

.weapon-badge.knife {
  background: #ffebf4;
  color: #e73c8c;
}

.weapon-badge.pistol {
  background: #e0e2ff;
  color: #3638ca;
}

.weapon-badge.heavy_weapon {
  background: #f3e5f5;
  color: #9b59b6;
}
</style>