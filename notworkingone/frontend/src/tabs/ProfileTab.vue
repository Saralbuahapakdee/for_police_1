<template>
  <div class="profile-tab">
    <div class="profile-container">
      <h2>👤 User Profile</h2>
      
      <!-- Personal Information -->
      <div class="profile-section">
        <h3>Personal Information</h3>
        <div class="profile-grid">
          <div class="profile-item">
            <label>First Name:</label>
            <input v-model="profileData.first_name" class="input-field" />
          </div>
          <div class="profile-item">
            <label>Last Name:</label>
            <input v-model="profileData.last_name" class="input-field" />
          </div>
          <div class="profile-item">
            <label>Username:</label>
            <input v-model="profileData.username" class="input-field" disabled />
          </div>
          <div class="profile-item">
            <label>Email:</label>
            <input v-model="profileData.email" class="input-field" disabled />
          </div>
          <div class="profile-item">
            <label>Phone:</label>
            <input v-model="profileData.phone" class="input-field" />
          </div>
          <div class="profile-item">
            <label>Department:</label>
            <input v-model="profileData.department" class="input-field" />
          </div>
          <div class="profile-item">
            <label>Role:</label>
            <input v-model="profileData.role" class="input-field" disabled />
          </div>
          <div class="profile-item">
            <label>Member Since:</label>
            <input :value="formatDate(profileData.created_at)" class="input-field" disabled />
          </div>
        </div>
        
        <div v-if="updateMessage" :class="['message', updateMessage.type]">
          {{ updateMessage.text }}
        </div>
        
        <button @click="updateProfile" class="save-btn" :disabled="isUpdating">
          {{ isUpdating ? 'Saving...' : 'Save Changes' }}
        </button>
      </div>

      <!-- Security -->
      <div class="profile-section">
        <h3>Security</h3>
        <p class="section-description">Change your account password</p>
        <button @click="showChangePassword = true" class="settings-btn">
          🔒 Change Password
        </button>
      </div>

      <!-- Data Management -->
      <div class="profile-section">
        <h3>Data Management</h3>
        <p class="section-description">Export your detection data for analysis</p>
        <button @click="exportData" class="settings-btn" :disabled="isExporting">
          {{ isExporting ? 'Exporting...' : '📥 Export Detection Data' }}
        </button>
      </div>

      <!-- Danger Zone -->
      <div class="profile-section danger-zone">
        <h3>Danger Zone</h3>
        <p class="section-description">Permanently delete your account and all associated data</p>
        <button @click="showDeleteConfirm = true" class="settings-btn danger">
          🗑️ Delete Account
        </button>
      </div>
    </div>

    <!-- Change Password Modal -->
    <div v-if="showChangePassword" class="modal-overlay" @click="closePasswordModal">
      <div class="modal" @click.stop>
        <h3>Change Password</h3>
        <div class="password-form">
          <input
            type="password"
            v-model="passwordData.current"
            placeholder="Current Password"
            class="input-field"
            @input="clearPasswordError"
          />
          <input
            type="password"
            v-model="passwordData.new"
            placeholder="New Password (min 6 characters)"
            class="input-field"
            @input="clearPasswordError"
          />
          <input
            type="password"
            v-model="passwordData.confirm"
            placeholder="Confirm New Password"
            class="input-field"
            @input="clearPasswordError"
            @keyup.enter="changePassword"
          />
          
          <div v-if="passwordError" class="error-message">{{ passwordError }}</div>
          <div v-if="passwordSuccess" class="success-message">{{ passwordSuccess }}</div>
        </div>
        
        <div class="modal-actions">
          <button @click="closePasswordModal" class="cancel-btn">Cancel</button>
          <button @click="changePassword" class="confirm-btn" :disabled="isChangingPassword">
            {{ isChangingPassword ? 'Changing...' : 'Change Password' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Delete Confirm Modal -->
    <div v-if="showDeleteConfirm" class="modal-overlay" @click="showDeleteConfirm = false">
      <div class="modal" @click.stop>
        <h3>Delete Account</h3>
        <p>Are you sure you want to delete your account?</p>
        <p style="color: #e74c3c; font-weight: 600;">
          This will permanently delete all your detection data and cannot be undone.
        </p>
        <div class="modal-actions">
          <button @click="showDeleteConfirm = false" class="cancel-btn">Cancel</button>
          <button @click="deleteAccount" class="delete-confirm-btn" :disabled="isDeleting">
            {{ isDeleting ? 'Deleting...' : 'Yes, Delete My Account' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const props = defineProps({
  token: String,
  userData: Object
})

const profileData = ref({
  username: '',
  email: '',
  first_name: '',
  last_name: '',
  phone: '',
  department: '',
  role: '',
  created_at: ''
})

const updateMessage = ref(null)
const isUpdating = ref(false)
const isExporting = ref(false)

// Password change
const showChangePassword = ref(false)
const passwordData = ref({
  current: '',
  new: '',
  confirm: ''
})
const passwordError = ref('')
const passwordSuccess = ref('')
const isChangingPassword = ref(false)

// Delete account
const showDeleteConfirm = ref(false)
const isDeleting = ref(false)

onMounted(() => {
  loadProfile()
})

async function loadProfile() {
  try {
    const res = await fetch('/api/user-info', {
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    
    if (res.ok) {
      const data = await res.json()
      profileData.value = data
    }
  } catch (error) {
    console.error('Could not load profile:', error)
  }
}

async function updateProfile() {
  isUpdating.value = true
  updateMessage.value = null
  
  try {
    const res = await fetch('/api/user-profile', {
      method: 'PUT',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${props.token}` 
      },
      body: JSON.stringify({
        first_name: profileData.value.first_name,
        last_name: profileData.value.last_name,
        phone: profileData.value.phone,
        department: profileData.value.department
      })
    })
    
    if (res.ok) {
      updateMessage.value = {
        type: 'success',
        text: '✓ Profile updated successfully'
      }
      setTimeout(() => updateMessage.value = null, 3000)
    } else {
      updateMessage.value = {
        type: 'error',
        text: 'Failed to update profile'
      }
    }
  } catch (error) {
    updateMessage.value = {
      type: 'error',
      text: 'Network error. Please try again.'
    }
  }
  
  isUpdating.value = false
}

async function exportData() {
  isExporting.value = true
  
  try {
    const res = await fetch(`/api/dashboard-data?days=365`, {
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    
    if (res.ok) {
      const data = await res.json()
      
      // Create CSV content
      let csvContent = 'Date,Camera,Location,Weapon Type,Total Detections,Average Confidence\n'
      data.daily_summary.forEach(item => {
        csvContent += `${item.detection_date},${item.camera_name || 'N/A'},${item.location || 'N/A'},${item.weapon_type},${item.total_detections},${item.avg_confidence}\n`
      })
      
      // Download CSV
      const blob = new Blob([csvContent], { type: 'text/csv' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `weapon-detection-data-${new Date().toISOString().split('T')[0]}.csv`
      a.click()
      window.URL.revokeObjectURL(url)
    }
  } catch (error) {
    console.error('Could not export data:', error)
  }
  
  isExporting.value = false
}

function clearPasswordError() {
  passwordError.value = ''
  passwordSuccess.value = ''
}

function closePasswordModal() {
  showChangePassword.value = false
  passwordData.value = { current: '', new: '', confirm: '' }
  clearPasswordError()
}

async function changePassword() {
  clearPasswordError()
  
  // Validation
  if (!passwordData.value.current || !passwordData.value.new || !passwordData.value.confirm) {
    passwordError.value = 'Please fill all fields'
    return
  }
  
  if (passwordData.value.new.length < 6) {
    passwordError.value = 'New password must be at least 6 characters'
    return
  }
  
  if (passwordData.value.new !== passwordData.value.confirm) {
    passwordError.value = 'Passwords do not match'
    return
  }
  
  if (passwordData.value.current === passwordData.value.new) {
    passwordError.value = 'New password must be different from current password'
    return
  }
  
  isChangingPassword.value = true
  
  try {
    const res = await fetch('/api/change-password', {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${props.token}`
      },
      body: JSON.stringify({ 
        current_password: passwordData.value.current,
        new_password: passwordData.value.new
      })
    })
    
    const data = await res.json()
    
    if (res.ok) {
      passwordSuccess.value = 'Password changed successfully!'
      passwordData.value = { current: '', new: '', confirm: '' }
      
      setTimeout(() => {
        closePasswordModal()
      }, 2000)
    } else {
      passwordError.value = data.error || 'Failed to change password'
    }
  } catch (error) {
    passwordError.value = 'Network error. Please try again.'
  }
  
  isChangingPassword.value = false
}

async function deleteAccount() {
  isDeleting.value = true
  
  try {
    const res = await fetch('/api/delete-account', {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    
    if (res.ok) {
      showDeleteConfirm.value = false
      alert('Account deleted successfully. You will be logged out.')
      // Emit logout event to parent
      window.location.reload()
    } else {
      const data = await res.json()
      alert(data.error || 'Failed to delete account')
    }
  } catch (error) {
    alert('Network error. Please try again.')
  }
  
  isDeleting.value = false
  showDeleteConfirm.value = false
}

function formatDate(dateString) {
  if (!dateString) return 'N/A'
  try {
    return new Date(dateString).toLocaleDateString()
  } catch {
    return dateString
  }
}
</script>

<style scoped>
.profile-tab {
  background: white;
  padding: 30px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.profile-container h2 {
  color: #2c3e50;
  margin-bottom: 30px;
}

.profile-section {
  margin-bottom: 30px;
  padding: 25px;
  background: #f8f9fa;
  border-radius: 10px;
}

.profile-section h3 {
  color: #2c3e50;
  margin-bottom: 10px;
}

.section-description {
  color: #7f8c8d;
  font-size: 0.9rem;
  margin-bottom: 15px;
}

.profile-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}

.profile-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.profile-item label {
  font-weight: 600;
  color: #2c3e50;
  font-size: 0.9rem;
}

.input-field {
  padding: 12px;
  border: 2px solid #e0e0e0;
  border-radius: 6px;
  font-size: 1rem;
  transition: border-color 0.3s ease;
}

.input-field:focus {
  border-color: #4a90e2;
  outline: none;
}

.input-field:disabled {
  background: #e9ecef;
  cursor: not-allowed;
  color: #6c757d;
}

.message {
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 15px;
  font-size: 0.95rem;
}

.message.success {
  background: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.message.error {
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.save-btn {
  padding: 12px 24px;
  background-color: #4a90e2;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1rem;
  transition: background-color 0.3s ease;
}

.save-btn:hover:not(:disabled) {
  background-color: #357ab7;
}

.save-btn:disabled {
  background-color: #bdc3c7;
  cursor: not-allowed;
}

.settings-btn {
  padding: 10px 20px;
  background-color: #4a90e2;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1rem;
  transition: background-color 0.3s ease;
}

.settings-btn:hover:not(:disabled) {
  background-color: #357ab7;
}

.settings-btn:disabled {
  background-color: #bdc3c7;
  cursor: not-allowed;
}

.settings-btn.danger {
  background-color: #e74c3c;
}

.settings-btn.danger:hover:not(:disabled) {
  background-color: #c0392b;
}

.danger-zone {
  border: 2px solid #e74c3c;
}

.danger-zone h3 {
  color: #e74c3c;
}

/* Modals */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  padding: 30px;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  max-width: 400px;
  width: 90%;
  text-align: center;
}

.modal h3 {
  margin-bottom: 20px;
  font-size: 1.5rem;
  color: #2c3e50;
}

.modal p {
  color: #2c3e50;
  margin-bottom: 20px;
  line-height: 1.5;
}

.password-form {
  display: flex;
  flex-direction: column;
  gap: 15px;
  margin-bottom: 25px;
}

.error-message {
  color: #e74c3c;
  font-size: 0.9rem;
  text-align: left;
}

.success-message {
  color: #27ae60;
  font-size: 0.9rem;
  text-align: left;
}

.modal-actions {
  display: flex;
  gap: 15px;
  justify-content: center;
}

.cancel-btn {
  padding: 10px 20px;
  background-color: #95a5a6;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1rem;
  transition: background-color 0.3s ease;
}

.cancel-btn:hover {
  background-color: #7f8c8d;
}

.confirm-btn {
  padding: 10px 20px;
  background-color: #4a90e2;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1rem;
  transition: background-color 0.3s ease;
}

.confirm-btn:hover:not(:disabled) {
  background-color: #357ab7;
}

.confirm-btn:disabled {
  background-color: #bdc3c7;
  cursor: not-allowed;
}

.delete-confirm-btn {
  padding: 10px 20px;
  background-color: #e74c3c;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1rem;
  transition: background-color 0.3s ease;
}

.delete-confirm-btn:hover:not(:disabled) {
  background-color: #c0392b;
}

.delete-confirm-btn:disabled {
  background-color: #bdc3c7;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .profile-grid {
    grid-template-columns: 1fr;
  }
  
  .modal {
    max-width: 95%;
    padding: 20px;
  }
}
</style>