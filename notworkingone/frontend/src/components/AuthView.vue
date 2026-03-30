<template>
  <div class="auth-view">
    <h1 class="title">Weapon Detection System</h1>

    <div class="auth-form">
      <div class="form-toggle">
        <button 
          @click="isRegisterMode = false" 
          :class="{ active: !isRegisterMode }"
          class="toggle-btn"
        >
          Login
        </button>
        <button 
          @click="isRegisterMode = true" 
          :class="{ active: isRegisterMode }"
          class="toggle-btn"
        >
          Register
        </button>
      </div>

      <!-- Login Form -->
      <div v-if="!isRegisterMode" class="input-container">
        <input
          v-model="loginData.username"
          placeholder="Username"
          class="input-field"
          @input="clearMessages"
        />
        <input
          type="password"
          v-model="loginData.password"
          placeholder="Password"
          class="input-field"
          @input="clearMessages"
          @keyup.enter="login"
        />
        
        <div v-if="errorMessage" class="error-message">{{ errorMessage }}</div>
        <div v-if="successMessage" class="success-message">{{ successMessage }}</div>
        
        <button @click="login" class="auth-btn" :disabled="isLoading">
          {{ isLoading ? 'Please wait...' : 'Login' }}
        </button>
      </div>

      <!-- Register Form -->
      <div v-else class="input-container">
        <div class="form-row">
          <input 
            v-model="registerData.first_name" 
            placeholder="First Name *" 
            class="input-field"
            @input="clearMessages"
          />
          <input 
            v-model="registerData.last_name" 
            placeholder="Last Name *" 
            class="input-field"
            @input="clearMessages"
          />
        </div>
        
        <input 
          v-model="registerData.username" 
          placeholder="Username (min 3 chars) *" 
          class="input-field"
          @input="clearMessages"
        />
        <input 
          v-model="registerData.email" 
          type="email"
          placeholder="Email *" 
          class="input-field"
          @input="clearMessages"
        />
        <input 
          v-model="registerData.phone" 
          placeholder="Phone Number" 
          class="input-field"
          @input="clearMessages"
        />
        
        <select v-model="registerData.role" class="input-field">
          <option value="guard">Guard</option>
          <option value="supervisor">Supervisor</option>
          <option value="admin">Administrator</option>
        </select>
        
        <input 
          v-model="registerData.department" 
          placeholder="Department" 
          class="input-field"
          @input="clearMessages"
        />
        
        <input
          type="password"
          v-model="registerData.password"
          placeholder="Password (min 6 chars) *"
          class="input-field"
          @input="clearMessages"
        />
        <input
          type="password"
          v-model="registerData.confirm_password"
          placeholder="Confirm Password *"
          class="input-field"
          @input="clearMessages"
          @keyup.enter="register"
        />
        
        <div v-if="errorMessage" class="error-message">{{ errorMessage }}</div>
        <div v-if="successMessage" class="success-message">{{ successMessage }}</div>
        
        <button @click="register" class="auth-btn" :disabled="isLoading">
          {{ isLoading ? 'Creating Account...' : 'Create Account' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['login-success'])

const isRegisterMode = ref(false)
const isLoading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

const loginData = ref({
  username: 'admin',
  password: 'admin123'
})

const registerData = ref({
  username: '',
  password: '',
  confirm_password: '',
  email: '',
  first_name: '',
  last_name: '',
  phone: '',
  role: 'guard',
  department: ''
})

function clearMessages() {
  errorMessage.value = ''
  successMessage.value = ''
}

async function login() {
  clearMessages()
  
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
      emit('login-success', {
        token: data.access_token,
        username: data.username,
        fullName: data.full_name || data.username,
        role: data.role || 'guard'
      })
    } else {
      errorMessage.value = data.error || 'Login failed'
    }
  } catch (error) {
    errorMessage.value = 'Network error. Please try again.'
    console.error('Login error:', error)
  }
  
  isLoading.value = false
}

async function register() {
  clearMessages()
  
  // Validation
  if (!registerData.value.username || !registerData.value.password || !registerData.value.email) {
    errorMessage.value = 'Please fill all required fields (*)'
    return
  }
  
  if (registerData.value.username.length < 3) {
    errorMessage.value = 'Username must be at least 3 characters'
    return
  }
  
  if (registerData.value.password.length < 6) {
    errorMessage.value = 'Password must be at least 6 characters'
    return
  }
  
  if (registerData.value.password !== registerData.value.confirm_password) {
    errorMessage.value = 'Passwords do not match'
    return
  }
  
  if (!registerData.value.email.includes('@')) {
    errorMessage.value = 'Please enter a valid email'
    return
  }
  
  isLoading.value = true
  
  try {
    const res = await fetch('/api/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(registerData.value)
    })
    
    const data = await res.json()
    
    if (res.status === 201) {
      successMessage.value = 'Account created successfully! Please log in.'
      isRegisterMode.value = false
      
      // Clear form
      registerData.value = {
        username: '', password: '', confirm_password: '', email: '',
        first_name: '', last_name: '', phone: '', role: 'guard', department: ''
      }
    } else {
      errorMessage.value = data.error || 'Registration failed'
    }
  } catch (error) {
    errorMessage.value = 'Network error. Please try again.'
    console.error('Register error:', error)
  }
  
  isLoading.value = false
}
</script>

<style scoped>
.auth-view {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 20px;
}

.title {
  font-size: 2.5rem;
  color: #ffffff;
  margin-bottom: 30px;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.8);
  z-index: 1;
}

.auth-form {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  padding: 30px;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  width: 500px;
  max-width: 90vw;
  z-index: 1;
}

.form-toggle {
  display: flex;
  margin-bottom: 25px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #e0e0e0;
}

.toggle-btn {
  flex: 1;
  padding: 12px;
  background: #f8f9fa;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  transition: all 0.3s ease;
}

.toggle-btn.active {
  background: #4a90e2;
  color: white;
}

.input-container {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
}

.input-field {
  padding: 14px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 1rem;
  transition: border-color 0.3s ease;
}

.input-field:focus {
  border-color: #4a90e2;
  outline: none;
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

.auth-btn {
  padding: 14px 20px;
  background-color: #4a90e2;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1rem;
  transition: background-color 0.3s ease;
}

.auth-btn:hover:not(:disabled) {
  background-color: #357ab7;
}

.auth-btn:disabled {
  background-color: #bdc3c7;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .title {
    font-size: 2rem;
  }
  
  .auth-form {
    width: 95vw;
  }
  
  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>