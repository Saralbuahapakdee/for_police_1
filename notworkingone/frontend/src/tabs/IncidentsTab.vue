<template>
  <div class="incidents-tab">
    <div class="incidents-header">
      <h2>🚨 Incident Management</h2>
      <div class="header-actions">
        <select v-model="filterStatus" @change="loadIncidents" class="filter-select">
          <option value="">All Status</option>
          <option value="pending">🔴 Pending</option>
          <option value="responding">🟡 Responding</option>
          <option value="resolved">🟢 Resolved</option>
        </select>
        
        <select v-if="userData.role === 'admin'" v-model="filterOfficer" @change="loadIncidents" class="filter-select">
          <option value="">All Officers</option>
          <option v-for="officer in officers" :key="officer.id" :value="officer.id">
            {{ officer.first_name }} {{ officer.last_name }} ({{ officer.badge_number }})
          </option>
        </select>
        
        <button @click="loadIncidents" class="refresh-btn">🔄 Refresh</button>
      </div>
    </div>

    <!-- Stats Summary -->
    <div class="stats-row">
      <div class="stat-card pending">
        <div class="stat-icon">🔴</div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.pending }}</div>
          <div class="stat-label">Pending</div>
        </div>
      </div>
      <div class="stat-card responding">
        <div class="stat-icon">🟡</div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.responding }}</div>
          <div class="stat-label">Responding</div>
        </div>
      </div>
      <div class="stat-card resolved">
        <div class="stat-icon">🟢</div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.resolved }}</div>
          <div class="stat-label">Resolved</div>
        </div>
      </div>
      <div class="stat-card total">
        <div class="stat-icon">📊</div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.total }}</div>
          <div class="stat-label">Total Incidents</div>
        </div>
      </div>
    </div>

    <!-- Incidents List -->
    <div class="incidents-list">
      <div v-if="isLoading" class="loading">Loading incidents...</div>
      <div v-else-if="incidents.length === 0" class="no-incidents">
        No incidents found
      </div>
      <div v-else class="incident-cards">
        <div v-for="incident in incidents" :key="incident.id" 
             :class="['incident-card', incident.status, incident.priority]"
             @click="selectIncident(incident)">
          <div class="incident-header-row">
            <div class="incident-number">{{ incident.incident_number }}</div>
            <div :class="['status-badge', incident.status]">
              {{ formatStatus(incident.status) }}
            </div>
          </div>
          
          <div class="incident-info">
            <div class="info-row">
              <span class="label">📹 Camera:</span>
              <span class="value">{{ incident.camera_name }}</span>
            </div>
            <div class="info-row">
              <span class="label">📍 Location:</span>
              <span class="value">{{ incident.camera_location }}</span>
            </div>
            <div class="info-row">
              <span class="label">⚔️ Weapon:</span>
              <span :class="['weapon-badge', incident.weapon_type]">
                {{ formatWeaponName(incident.weapon_type) }}
              </span>
            </div>
            <div class="info-row">
              <span class="label">🕐 Detected:</span>
              <span class="value">{{ formatDateTime(incident.detected_at) }}</span>
            </div>
            <div v-if="incident.assigned_to_username" class="info-row">
              <span class="label">👮 Assigned:</span>
              <span class="value">{{ incident.assigned_to_username }}</span>
            </div>
          </div>
          
          <div :class="['priority-indicator', incident.priority]" 
               :title="formatPriority(incident.priority)">
          </div>
        </div>
      </div>
    </div>

    <!-- Incident Detail Modal -->
    <div v-if="selectedIncident" class="modal-overlay" @click="closeModal">
      <div class="modal-detail" @click.stop>
        <div class="modal-header">
          <h3>{{ selectedIncident.incident_number }}</h3>
          <button @click="closeModal" class="close-btn">✕</button>
        </div>
        
        <div class="modal-content">
          <div class="detail-section">
            <h4>Incident Details</h4>
            <div class="detail-grid">
              <div class="detail-item">
                <label>Status:</label>
                <span :class="['status-badge', selectedIncident.status]">
                  {{ formatStatus(selectedIncident.status) }}
                </span>
              </div>
              <div class="detail-item">
                <label>Priority:</label>
                <span :class="['priority-badge', selectedIncident.priority]">
                  {{ formatPriority(selectedIncident.priority) }}
                </span>
              </div>
              <div class="detail-item">
                <label>Camera:</label>
                <span>{{ selectedIncident.camera_name }}</span>
              </div>
              <div class="detail-item">
                <label>Location:</label>
                <span>{{ selectedIncident.camera_location }}</span>
              </div>
              <div class="detail-item">
                <label>Weapon Type:</label>
                <span :class="['weapon-badge', selectedIncident.weapon_type]">
                  {{ formatWeaponName(selectedIncident.weapon_type) }}
                </span>
              </div>
              <div class="detail-item">
                <label>Detected At:</label>
                <span>{{ formatDateTime(selectedIncident.detected_at) }}</span>
              </div>
              <div class="detail-item">
                <label>Created By:</label>
                <span>{{ selectedIncident.created_by_username }}</span>
              </div>
              <div v-if="selectedIncident.assigned_to_username" class="detail-item">
                <label>Assigned To:</label>
                <span>{{ selectedIncident.assigned_to_username }}</span>
              </div>
            </div>
          </div>

          <div v-if="selectedIncident.description" class="detail-section">
            <h4>Description</h4>
            <p class="description-text">{{ selectedIncident.description }}</p>
          </div>

          <div v-if="selectedIncident.response_notes" class="detail-section">
            <h4>Response Notes</h4>
            <p class="description-text">{{ selectedIncident.response_notes }}</p>
          </div>

          <div v-if="selectedIncident.resolution_notes" class="detail-section">
            <h4>Resolution Notes</h4>
            <p class="description-text">{{ selectedIncident.resolution_notes }}</p>
          </div>

          <!-- Action Form -->
          <div class="detail-section">
            <h4>Take Action</h4>
            
            <div v-if="selectedIncident.status === 'pending'" class="action-form">
              <div v-if="userData.role === 'admin'" class="form-group">
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
              
              <button @click="updateStatus('responding')" class="action-btn responding">
                🟡 Start Responding
              </button>
            </div>
            
            <div v-else-if="selectedIncident.status === 'responding'" class="action-form">
              <div class="form-group">
                <label>Resolution Notes:</label>
                <textarea v-model="actionData.resolution_notes" class="textarea-field" 
                          placeholder="Enter resolution details..." rows="2"></textarea>
              </div>
              
              <button @click="updateStatus('resolved')" class="action-btn resolved">
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const props = defineProps({
  token: String,
  userData: Object
})

const incidents = ref([])
const officers = ref([])
const selectedIncident = ref(null)
const filterStatus = ref('')
const filterOfficer = ref('')
const isLoading = ref(false)

const actionData = ref({
  assigned_to: '',
  response_notes: '',
  resolution_notes: ''
})

const stats = computed(() => {
  return {
    pending: incidents.value.filter(i => i.status === 'pending').length,
    responding: incidents.value.filter(i => i.status === 'responding').length,
    resolved: incidents.value.filter(i => i.status === 'resolved').length,
    total: incidents.value.length
  }
})

onMounted(async () => {
  await loadOfficers()
  await loadIncidents()
  
  // Auto-refresh every 30 seconds
  setInterval(loadIncidents, 30000)
})

async function loadOfficers() {
  if (props.userData.role !== 'admin') return
  
  try {
    const res = await fetch('/api/officers', {
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    
    if (res.ok) {
      const data = await res.json()
      officers.value = data.officers
    }
  } catch (error) {
    console.error('Could not load officers:', error)
  }
}

async function loadIncidents() {
  isLoading.value = true
  
  try {
    let url = '/api/incidents?limit=100'
    if (filterStatus.value) url += `&status=${filterStatus.value}`
    if (filterOfficer.value) url += `&assigned_to=${filterOfficer.value}`
    
    const res = await fetch(url, {
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    
    if (res.ok) {
      const data = await res.json()
      incidents.value = data.incidents
    }
  } catch (error) {
    console.error('Could not load incidents:', error)
  }
  
  isLoading.value = false
}

function selectIncident(incident) {
  selectedIncident.value = incident
  actionData.value = {
    assigned_to: incident.assigned_to || '',
    response_notes: '',
    resolution_notes: ''
  }
}

function closeModal() {
  selectedIncident.value = null
  actionData.value = {
    assigned_to: '',
    response_notes: '',
    resolution_notes: ''
  }
}

async function updateStatus(newStatus) {
  if (!selectedIncident.value) return
  
  const updates = { status: newStatus }
  
  if (newStatus === 'responding') {
    if (actionData.value.assigned_to) {
      updates.assigned_to = actionData.value.assigned_to
    }
    if (actionData.value.response_notes) {
      updates.response_notes = actionData.value.response_notes
    }
  } else if (newStatus === 'resolved') {
    if (!actionData.value.resolution_notes) {
      alert('Please enter resolution notes')
      return
    }
    updates.resolution_notes = actionData.value.resolution_notes
  }
  
  try {
    const res = await fetch(`/api/incidents/${selectedIncident.value.id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${props.token}`
      },
      body: JSON.stringify(updates)
    })
    
    if (res.ok) {
      await loadIncidents()
      closeModal()
    } else {
      alert('Failed to update incident')
    }
  } catch (error) {
    console.error('Could not update incident:', error)
    alert('Network error. Please try again.')
  }
}

function formatStatus(status) {
  const map = {
    'pending': 'Pending',
    'responding': 'Responding',
    'resolved': 'Resolved'
  }
  return map[status] || status
}

function formatPriority(priority) {
  const map = {
    'low': 'Low Priority',
    'medium': 'Medium Priority',
    'high': 'High Priority'
  }
  return map[priority] || priority
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
.incidents-tab {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.incidents-header {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 15px;
}

.incidents-header h2 {
  color: #2c3e50;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.filter-select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: white;
  cursor: pointer;
}

.refresh-btn {
  padding: 8px 16px;
  background: #4a90e2;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.refresh-btn:hover {
  background: #357ab7;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.stat-card {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  gap: 15px;
  border-left: 4px solid #ddd;
}

.stat-card.pending { border-left-color: #e74c3c; }
.stat-card.responding { border-left-color: #f39c12; }
.stat-card.resolved { border-left-color: #27ae60; }
.stat-card.total { border-left-color: #3498db; }

.stat-icon {
  font-size: 2.5rem;
}

.stat-value {
  font-size: 2rem;
  font-weight: 700;
  color: #2c3e50;
}

.stat-label {
  font-size: 0.9rem;
  color: #7f8c8d;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.incidents-list {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  min-height: 400px;
}

.loading,
.no-incidents {
  text-align: center;
  padding: 60px 20px;
  color: #7f8c8d;
  font-style: italic;
}

.incident-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 15px;
}

.incident-card {
  background: #f8f9fa;
  padding: 18px;
  border-radius: 10px;
  border-left: 4px solid #ddd;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.incident-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.incident-card.pending { border-left-color: #e74c3c; }
.incident-card.responding { border-left-color: #f39c12; }
.incident-card.resolved { border-left-color: #27ae60; }

.incident-card.high {
  box-shadow: 0 0 0 2px rgba(231, 76, 60, 0.2);
}

.incident-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.incident-number {
  font-weight: 700;
  color: #2c3e50;
  font-size: 1.05rem;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
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

.incident-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
}

.label {
  color: #7f8c8d;
  min-width: 90px;
}

.value {
  color: #2c3e50;
  font-weight: 500;
}

.weapon-badge {
  padding: 3px 10px;
  border-radius: 10px;
  font-size: 0.8rem;
  font-weight: 600;
}

.weapon-badge.knife {
  background: #ffebee;
  color: #e74c3c;
}

.weapon-badge.pistol {
  background: #fff3e0;
  color: #f39c12;
}

.weapon-badge.heavy_weapon {
  background: #f3e5f5;
  color: #9b59b6;
}

.priority-indicator {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.priority-indicator.high { background: #e74c3c; }
.priority-indicator.medium { background: #f39c12; }
.priority-indicator.low { background: #95a5a6; }

/* Modal Styles */
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
  max-width: 700px;
  max-height: 85vh;
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

.detail-section h4 {
  color: #2c3e50;
  margin-bottom: 12px;
  border-bottom: 2px solid #e0e0e0;
  padding-bottom: 6px;
  font-size: 0.95rem;
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
  letter-spacing: 0.5px;
}

.detail-item span {
  color: #2c3e50;
  font-size: 1rem;
}

.description-text {
  color: #2c3e50;
  line-height: 1.5;
  font-size: 0.95rem;
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
  font-size: 0.95rem;
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

.priority-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 600;
}

.priority-badge.high {
  background: #fee;
  color: #e74c3c;
}

.priority-badge.medium {
  background: #fff3cd;
  color: #f39c12;
}

.priority-badge.low {
  background: #e9ecef;
  color: #95a5a6;
}

@media (max-width: 768px) {
  .incidents-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .header-actions {
    width: 100%;
    flex-direction: column;
  }
  
  .filter-select,
  .refresh-btn {
    width: 100%;
  }
  
  .incident-cards {
    grid-template-columns: 1fr;
  }
  
  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>