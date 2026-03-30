<template>
  <div class="officers-tab">
    <div class="officers-header">
      <h2>👮 Officer Management</h2>
      <button @click="showCreateModal = true" class="create-btn">
        ➕ Create New Officer
      </button>
    </div>

    <!-- Officers List -->
    <div class="officers-list">
      <div v-if="isLoading" class="loading">Loading officers...</div>
      <div v-else-if="officers.length === 0" class="no-officers">
        No officers found
      </div>
      <div v-else class="officer-cards">
        <div v-for="officer in officers" :key="officer.id" class="officer-card">
          <div class="officer-header">
            <div class="officer-avatar">👮</div>
            <div class="officer-info">
              <h3>{{ officer.first_name }} {{ officer.last_name }}</h3>
              <p class="badge-number">Badge: {{ officer.badge_number || 'N/A' }}</p>
              <p class="username">@{{ officer.username }}</p>
            </div>
            <div :class="['status-indicator', officer.is_active ? 'active' : 'inactive']">
              {{ officer.is_active ? '🟢 Active' : '🔴 Inactive' }}
            </div>
          </div>
          
          <div class="officer-details">
            <div class="detail-row">
              <span class="label">Department:</span>
              <span class="value">{{ officer.department || 'Not assigned' }}</span>
            </div>
          </div>
          
          <div class="officer-actions">
            <button @click="confirmDelete(officer)" class="delete-btn">
              🗑️ Delete
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Create Officer Modal -->
    <div v-if="showCreateModal" class="modal-overlay" @click="closeCreateModal">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <h3>Create New Officer</h3>
          <button @click="closeCreateModal" class="close-btn">✕</button>
        </div>
        
        <div class="modal-content">
          <div class="form-row">
            <div class="form-group">
              <label>First Name *</label>
              <input v-model="newOfficer.first_name" class="input-field" @input="clearError" />
            </div>
            <div class="form-group">
              <label>Last Name *</label>
              <input v-model="newOfficer.last_name" class="input-field" @input="clearError" />
            </div>
          </div>
          
          <div class="form-group">
            <label>Username * (min 3 characters)</label>
            <input v-model="newOfficer.username" class="input-field" @input="clearError" />
          </div>
          
          <div class="form-group">
            <label>Email *</label>
            <input v-model="newOfficer.email" type="email" class="input-field" @input="clearError" />
          </div>
          
          <div class="form-row">
            <div class="form-group">
              <label>Badge Number</label>
              <input v-model="newOfficer.badge_number" class="input-field" @input="clearError" />
            </div>
            <div class="form-group">
              <label>Phone</label>
              <input v-model="newOfficer.phone" class="input-field" @input="clearError" />
            </div>
          </div>
          
          <div class="form-group">
            <label>Department</label>
            <input v-model="newOfficer.department" class="input-field" @input="clearError" />
          </div>
          
          <div class="form-group">
            <label>Password * (min 6 characters)</label>
            <input v-model="newOfficer.password" type="password" class="input-field" @input="clearError" />
          </div>
          
          <div v-if="error" class="error-message">{{ error }}</div>
          <div v-if="success" class="success-message">{{ success }}</div>
        </div>
        
        <div class="modal-actions">
          <button @click="closeCreateModal" class="cancel-btn">Cancel</button>
          <button @click="createOfficer" class="confirm-btn" :disabled="isCreating">
            {{ isCreating ? 'Creating...' : 'Create Officer' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div v-if="showDeleteModal" class="modal-overlay" @click="showDeleteModal = false">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <h3>Confirm Deletion</h3>
          <button @click="showDeleteModal = false" class="close-btn">✕</button>
        </div>
        
        <div class="modal-content">
          <p>Are you sure you want to delete officer <strong>{{ officerToDelete?.username }}</strong>?</p>
          <p class="warning-text">
            This will permanently delete all associated data including detection logs and incident history.
          </p>
        </div>
        
        <div class="modal-actions">
          <button @click="showDeleteModal = false" class="cancel-btn">Cancel</button>
          <button @click="deleteOfficer" class="delete-confirm-btn" :disabled="isDeleting">
            {{ isDeleting ? 'Deleting...' : 'Yes, Delete Officer' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const props = defineProps({
  token: String
})

const officers = ref([])
const isLoading = ref(false)
const showCreateModal = ref(false)
const showDeleteModal = ref(false)
const officerToDelete = ref(null)
const isCreating = ref(false)
const isDeleting = ref(false)
const error = ref('')
const success = ref('')

const newOfficer = ref({
  username: '',
  password: '',
  email: '',
  first_name: '',
  last_name: '',
  badge_number: '',
  phone: '',
  department: ''
})

onMounted(() => {
  loadOfficers()
})

async function loadOfficers() {
  isLoading.value = true
  
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
  
  isLoading.value = false
}

function clearError() {
  error.value = ''
  success.value = ''
}

function closeCreateModal() {
  showCreateModal.value = false
  newOfficer.value = {
    username: '', password: '', email: '',
    first_name: '', last_name: '', badge_number: '',
    phone: '', department: ''
  }
  clearError()
}

async function createOfficer() {
  clearError()
  
  // Validation
  if (!newOfficer.value.username || !newOfficer.value.password || !newOfficer.value.email) {
    error.value = 'Please fill all required fields (*)'
    return
  }
  
  if (newOfficer.value.username.length < 3) {
    error.value = 'Username must be at least 3 characters'
    return
  }
  
  if (newOfficer.value.password.length < 6) {
    error.value = 'Password must be at least 6 characters'
    return
  }
  
  if (!newOfficer.value.email.includes('@')) {
    error.value = 'Please enter a valid email'
    return
  }
  
  isCreating.value = true
  
  try {
    const res = await fetch('/api/create-officer', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${props.token}`
      },
      body: JSON.stringify(newOfficer.value)
    })
    
    const data = await res.json()
    
    if (res.ok) {
      success.value = 'Officer created successfully!'
      await loadOfficers()
      setTimeout(() => {
        closeCreateModal()
      }, 1500)
    } else {
      error.value = data.error || 'Failed to create officer'
    }
  } catch (error) {
    error.value = 'Network error. Please try again.'
    console.error('Create officer error:', error)
  }
  
  isCreating.value = false
}

function confirmDelete(officer) {
  officerToDelete.value = officer
  showDeleteModal.value = true
}

async function deleteOfficer() {
  if (!officerToDelete.value) return
  
  isDeleting.value = true
  
  try {
    const res = await fetch(`/api/delete-officer/${officerToDelete.value.username}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    
    if (res.ok) {
      await loadOfficers()
      showDeleteModal.value = false
      officerToDelete.value = null
    } else {
      const data = await res.json()
      alert(data.error || 'Failed to delete officer')
    }
  } catch (error) {
    alert('Network error. Please try again.')
    console.error('Delete officer error:', error)
  }
  
  isDeleting.value = false
}
</script>

<style scoped>
.officers-tab {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.officers-header {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.officers-header h2 {
  color: #2c3e50;
  margin: 0;
}

.create-btn {
  padding: 10px 20px;
  background: #27ae60;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.95rem;
  transition: all 0.3s ease;
}

.create-btn:hover {
  background: #229954;
  transform: translateY(-2px);
}

.officers-list {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  min-height: 400px;
}

.loading,
.no-officers {
  text-align: center;
  padding: 60px 20px;
  color: #7f8c8d;
  font-style: italic;
}

.officer-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 20px;
}

.officer-card {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 10px;
  border-left: 4px solid #3498db;
  transition: all 0.3s ease;
}

.officer-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.officer-header {
  display: flex;
  gap: 15px;
  margin-bottom: 15px;
  align-items: flex-start;
}

.officer-avatar {
  font-size: 2.5rem;
  width: 60px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #e8f4fd;
  border-radius: 50%;
}

.officer-info {
  flex: 1;
}

.officer-info h3 {
  margin: 0 0 5px 0;
  color: #2c3e50;
  font-size: 1.1rem;
}

.badge-number {
  color: #3498db;
  font-weight: 600;
  font-size: 0.9rem;
  margin: 3px 0;
}

.username {
  color: #7f8c8d;
  font-size: 0.85rem;
  margin: 3px 0;
}

.status-indicator {
  padding: 4px 10px;
  border-radius: 10px;
  font-size: 0.8rem;
  font-weight: 600;
}

.status-indicator.active {
  background: #d4edda;
  color: #27ae60;
}

.status-indicator.inactive {
  background: #f8d7da;
  color: #e74c3c;
}

.officer-details {
  margin-bottom: 15px;
  padding-top: 15px;
  border-top: 1px solid #e0e0e0;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.label {
  color: #7f8c8d;
  font-weight: 500;
}

.value {
  color: #2c3e50;
  font-weight: 600;
}

.officer-actions {
  display: flex;
  gap: 10px;
  padding-top: 15px;
  border-top: 1px solid #e0e0e0;
}

.delete-btn {
  padding: 8px 16px;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.3s ease;
}

.delete-btn:hover {
  background: #c0392b;
}

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

.modal {
  background: white;
  border-radius: 12px;
  width: 100%;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 25px;
  border-bottom: 1px solid #e0e0e0;
  background: #f8f9fa;
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
  padding: 25px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
}

.form-group {
  margin-bottom: 18px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  color: #2c3e50;
  font-weight: 600;
  font-size: 0.9rem;
}

.input-field {
  width: 100%;
  padding: 10px 12px;
  border: 2px solid #e0e0e0;
  border-radius: 6px;
  font-size: 1rem;
  transition: border-color 0.3s ease;
}

.input-field:focus {
  border-color: #3498db;
  outline: none;
}

.error-message {
  background: #fee;
  border: 1px solid #fcc;
  color: #c33;
  padding: 12px;
  border-radius: 6px;
  margin-top: 15px;
  font-size: 0.9rem;
}

.success-message {
  background: #d4edda;
  border: 1px solid #c3e6cb;
  color: #27ae60;
  padding: 12px;
  border-radius: 6px;
  margin-top: 15px;
  font-size: 0.9rem;
}

.warning-text {
  color: #e74c3c;
  font-weight: 600;
  margin-top: 10px;
}

.modal-actions {
  display: flex;
  gap: 10px;
  padding: 20px 25px;
  border-top: 1px solid #e0e0e0;
  background: #f8f9fa;
  justify-content: flex-end;
}

.cancel-btn {
  padding: 10px 20px;
  background: #95a5a6;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  transition: background-color 0.3s ease;
}

.cancel-btn:hover {
  background: #7f8c8d;
}

.confirm-btn {
  padding: 10px 20px;
  background: #27ae60;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.3s ease;
}

.confirm-btn:hover:not(:disabled) {
  background: #229954;
}

.confirm-btn:disabled {
  background: #bdc3c7;
  cursor: not-allowed;
}

.delete-confirm-btn {
  padding: 10px 20px;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.3s ease;
}

.delete-confirm-btn:hover:not(:disabled) {
  background: #c0392b;
}

.delete-confirm-btn:disabled {
  background: #bdc3c7;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .officers-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 15px;
  }
  
  .create-btn {
    width: 100%;
  }
  
  .officer-cards {
    grid-template-columns: 1fr;
  }
  
  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>