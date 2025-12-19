<template>
  <div id="app">
    <!-- Login Screen -->
    <div v-if="!token" class="login-container">
      <div class="login-card">
        <div class="login-header">
          <div class="badge-icon">🛡️</div>
          <h1>Weapon Detection System</h1>
          <p class="subtitle">Law Enforcement Portal</p>
        </div>

        <div class="login-form">
          <div class="input-group">
            <label>Username / Badge Number</label>
            <input
              v-model="loginData.username"
              placeholder="Enter your username"
              class="input-field"
              @input="clearError"
              @keyup.enter="login"
            />
          </div>

          <div class="input-group">
            <label>Password</label>
            <input
              type="password"
              v-model="loginData.password"
              placeholder="Enter your password"
              class="input-field"
              @input="clearError"
              @keyup.enter="login"
            />
          </div>
          
          <div v-if="errorMessage" class="error-message">{{ errorMessage }}</div>
          
          <button @click="login" class="login-btn" :disabled="isLoading">
            {{ isLoading ? 'Signing in...' : 'Sign In' }}
          </button>
        </div>

        <div class="login-footer">
          <p>Authorized Personnel Only</p>
        </div>
      </div>
    </div>

    <!-- Main App (Logged In) -->
    <MainApp 
      v-if="token"
      :token="token"
      :user-data="userData"
      @logout="handleLogout"
    />

    <!-- Global Detection Alert Banner (Shows on all pages when logged in) -->
    <div v-if="token && currentDetection.detected && hasObjects" class="global-alert-banner">
      <div class="alert-content">
        <div class="alert-icon">🚨</div>
        <div class="alert-info">
          <strong>WEAPON DETECTED!</strong>
          <span>
            <span v-for="(data, weaponType) in currentDetection.objects" :key="weaponType">
              {{ formatWeaponName(weaponType) }} ({{ data.count }})
            </span>
          </span>
        </div>
        <div class="alert-time">{{ formatTime(currentDetection.timestamp) }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import MainApp from './components/MainApp.vue'
import detectionService from './services/detectionService.js'

const token = ref('')
const userData = ref({
  username: '',
  fullName: '',
  role: '',
  userId: null
})

const isLoading = ref(false)
const errorMessage = ref('')

const loginData = ref({
  username: '',
  password: ''
})

// Detection state
const currentDetection = ref({
  detected: false,
  objects: {},
  timestamp: null
})

let unsubscribeDetection = null

const hasObjects = computed(() => {
  return Object.keys(currentDetection.value.objects || {}).length > 0
})

onMounted(() => {
  const savedToken = localStorage.getItem('authToken')
  if (savedToken) {
    token.value = savedToken
    userData.value = {
      username: localStorage.getItem('currentUsername') || '',
      fullName: localStorage.getItem('userFullName') || '',
      role: localStorage.getItem('userRole') || '',
      userId: parseInt(localStorage.getItem('userId')) || null
    }
    
    // Start detection service when user is logged in
    startDetectionService()
  }

  // Request notification permission
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission()
  }
})

onUnmounted(() => {
  stopDetectionService()
})

function startDetectionService() {
  // Subscribe to detection updates
  unsubscribeDetection = detectionService.subscribe((state) => {
    currentDetection.value = state.currentDetection
  })
  
  // Start polling
  detectionService.startPolling(token.value)
  
  console.log('✅ Global detection service started')
}

function stopDetectionService() {
  if (unsubscribeDetection) {
    unsubscribeDetection()
    unsubscribeDetection = null
  }
  
  detectionService.stopPolling()
  
  console.log('🛑 Global detection service stopped')
}

function clearError() {
  errorMessage.value = ''
}

async function login() {
  clearError()
  
  if (!loginData.value.username || !loginData.value.password) {
    errorMessage.value = 'Please enter username and password'
    return
  }
  
  isLoading.value = true
  
  try {
    const res = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(loginData.value)
    })
    
    const data = await res.json()
    
    if (res.ok && data.access_token) {
      token.value = data.access_token
      userData.value = {
        username: data.username,
        fullName: data.full_name || data.username,
        role: data.role || 'officer',
        userId: data.user_id
      }
      
      localStorage.setItem('authToken', data.access_token)
      localStorage.setItem('currentUsername', data.username)
      localStorage.setItem('userFullName', data.full_name || data.username)
      localStorage.setItem('userRole', data.role || 'officer')
      localStorage.setItem('userId', data.user_id)
      
      loginData.value = { username: '', password: '' }
      
      // Start detection service after successful login
      startDetectionService()
    } else {
      errorMessage.value = data.error || 'Invalid credentials'
    }
  } catch (error) {
    errorMessage.value = 'Network error. Please try again.'
    console.error('Login error:', error)
  }
  
  isLoading.value = false
}

function handleLogout() {
  stopDetectionService()
  
  token.value = ''
  userData.value = { username: '', fullName: '', role: '', userId: null }
  
  localStorage.removeItem('authToken')
  localStorage.removeItem('currentUsername')
  localStorage.removeItem('userFullName')
  localStorage.removeItem('userRole')
  localStorage.removeItem('userId')
}

function formatWeaponName(weaponType) {
  const names = {
    'gun': 'Gun/Pistol',
    'heavy-weapon': 'Heavy Weapon',
    'heavy_weapon': 'Heavy Weapon',
    'knife': 'Knife',
    'pistol': 'Pistol'
  }
  return names[weaponType] || weaponType.replace('-', ' ').replace('_', ' ')
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  try {
    return new Date(timestamp).toLocaleTimeString()
  } catch {
    return ''
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  overflow: hidden;
  background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
}

#app {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
}

.login-container {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 20px;
}

.login-card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  width: 100%;
  max-width: 420px;
  overflow: hidden;
}

.login-header {
  background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
  color: white;
  padding: 40px 30px;
  text-align: center;
}

.badge-icon {
  font-size: 4rem;
  margin-bottom: 15px;
}

.login-header h1 {
  font-size: 1.8rem;
  margin-bottom: 8px;
  font-weight: 700;
}

.subtitle {
  font-size: 1rem;
  opacity: 0.9;
  font-weight: 400;
}

.login-form {
  padding: 35px 30px;
}

.input-group {
  margin-bottom: 22px;
}

.input-group label {
  display: block;
  margin-bottom: 8px;
  color: #2c3e50;
  font-weight: 600;
  font-size: 0.9rem;
}

.input-field {
  width: 100%;
  padding: 14px 16px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 1rem;
  transition: all 0.3s ease;
}

.input-field:focus {
  border-color: #2a5298;
  outline: none;
  box-shadow: 0 0 0 3px rgba(42, 82, 152, 0.1);
}

.error-message {
  background: #fee;
  border: 1px solid #fcc;
  color: #c33;
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 20px;
  font-size: 0.9rem;
  text-align: center;
}

.login-btn {
  width: 100%;
  padding: 14px 20px;
  background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1.05rem;
  font-weight: 600;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(30, 60, 114, 0.3);
}

.login-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(30, 60, 114, 0.4);
}

.login-btn:disabled {
  background: #bdc3c7;
  cursor: not-allowed;
  box-shadow: none;
}

.login-footer {
  background: #f8f9fa;
  padding: 20px;
  text-align: center;
  border-top: 1px solid #e0e0e0;
}

.login-footer p {
  color: #7f8c8d;
  font-size: 0.85rem;
  font-weight: 600;
}

/* Global Alert Banner */
.global-alert-banner {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9999;
  min-width: 400px;
  max-width: 90vw;
  background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
  color: white;
  padding: 15px 20px;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(231, 76, 60, 0.4);
  animation: slideDown 0.3s ease-out, pulse 2s ease-in-out infinite;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

@keyframes pulse {
  0%, 100% { 
    box-shadow: 0 8px 24px rgba(231, 76, 60, 0.4);
  }
  50% { 
    box-shadow: 0 8px 32px rgba(231, 76, 60, 0.6);
  }
}

.alert-content {
  display: flex;
  align-items: center;
  gap: 15px;
}

.alert-icon {
  font-size: 2rem;
  animation: shake 0.5s ease-in-out infinite;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-3px) rotate(-5deg); }
  75% { transform: translateX(3px) rotate(5deg); }
}

.alert-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.alert-info strong {
  font-size: 1.1rem;
  letter-spacing: 0.5px;
}

.alert-info span {
  font-size: 0.95rem;
  opacity: 0.95;
}

.alert-time {
  font-size: 0.85rem;
  opacity: 0.9;
  font-weight: 600;
  white-space: nowrap;
}

@media (max-width: 768px) {
  .login-card {
    max-width: 100%;
  }
  
  .login-header h1 {
    font-size: 1.5rem;
  }
  
  .badge-icon {
    font-size: 3rem;
  }
  
  .global-alert-banner {
    min-width: 90vw;
    top: 10px;
  }
  
  .alert-content {
    flex-wrap: wrap;
  }
}
</style>