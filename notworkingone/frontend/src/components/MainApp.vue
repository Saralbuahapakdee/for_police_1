<template>
  <div class="main-app">
    <!-- Navigation Header -->
    <div class="nav-header">
      <div class="nav-left">
        <h2 class="app-title">🛡️ Police Weapon Detection System</h2>
        <div class="nav-tabs">
          <button @click="activeTab = 'incidents'" :class="{ active: activeTab === 'incidents' }" class="nav-tab">
            🚨 Incidents
          </button>
          <button @click="activeTab = 'stream'" :class="{ active: activeTab === 'stream' }" class="nav-tab">
            📹 Live Feed
          </button>
          <button @click="activeTab = 'logs'" :class="{ active: activeTab === 'logs' }" class="nav-tab">
            📋 Detection Logs
          </button>
          <button @click="activeTab = 'dashboard'" :class="{ active: activeTab === 'dashboard' }" class="nav-tab">
            📊 Analytics
          </button>
          <button v-if="userData.role === 'admin'" @click="activeTab = 'officers'" :class="{ active: activeTab === 'officers' }" class="nav-tab">
            👮 Officers
          </button>
          <button @click="activeTab = 'profile'" :class="{ active: activeTab === 'profile' }" class="nav-tab">
            👤 Profile
          </button>
        </div>
      </div>
      <div class="user-info">
        <div class="user-details">
          <span class="username-display">{{ userData.fullName || userData.username }}</span>
          <span :class="['user-role', userData.role]">{{ formatRole(userData.role) }}</span>
        </div>
        <button @click="$emit('logout')" class="logout-btn">Sign Out</button>
      </div>
    </div>

    <!-- Content Area -->
    <div class="content-area">
      <IncidentsTab v-if="activeTab === 'incidents'" :token="token" :user-data="userData" />
      <StreamTab v-if="activeTab === 'stream'" :token="token" />
      <LogsTab v-if="activeTab === 'logs'" :token="token" />
      <DashboardTab v-if="activeTab === 'dashboard'" :token="token" />
      <OfficersTab v-if="activeTab === 'officers' && userData.role === 'admin'" :token="token" />
      <ProfileTab v-if="activeTab === 'profile'" :token="token" :user-data="userData" />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import IncidentsTab from '../tabs/IncidentsTab.vue'
import StreamTab from '../tabs/StreamTab.vue'
import LogsTab from '../tabs/LogsTab.vue'
import DashboardTab from '../tabs/DashboardTab.vue'
import OfficersTab from '../tabs/OfficersTab.vue'
import ProfileTab from '../tabs/ProfileTab.vue'

const props = defineProps({
  token: String,
  userData: Object
})

defineEmits(['logout'])

const activeTab = ref('incidents')

function formatRole(role) {
  const roles = {
    'admin': 'Administrator',
    'officer': 'Police Officer'
  }
  return roles[role] || role
}
</script>

<style scoped>
.main-app {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  background-color: #f0f2f5;
}

.nav-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 25px;
  background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  color: white;
}

.nav-left {
  display: flex;
  align-items: center;
  gap: 30px;
}

.app-title {
  font-size: 1.3rem;
  font-weight: 700;
  margin: 0;
}

.nav-tabs {
  display: flex;
  gap: 5px;
}

.nav-tab {
  padding: 10px 18px;
  background: rgba(255, 255, 255, 0.1);
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.95rem;
  color: rgba(255, 255, 255, 0.9);
  transition: all 0.3s ease;
  font-weight: 500;
}

.nav-tab.active {
  background: white;
  color: #1e3c72;
  font-weight: 600;
}

.nav-tab:hover:not(.active) {
  background: rgba(255, 255, 255, 0.2);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 20px;
}

.user-details {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.username-display {
  font-weight: 600;
  font-size: 1rem;
}

.user-role {
  padding: 3px 10px;
  border-radius: 10px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.user-role.admin {
  background: rgba(231, 76, 60, 0.2);
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.user-role.officer {
  background: rgba(52, 152, 219, 0.2);
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.logout-btn {
  padding: 8px 16px;
  background-color: rgba(255, 255, 255, 0.15);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s ease;
  font-weight: 600;
}

.logout-btn:hover {
  background-color: rgba(255, 255, 255, 0.25);
  transform: translateY(-1px);
}

.content-area {
  flex: 1;
  overflow-y: auto;
  padding: 25px;
}

@media (max-width: 1200px) {
  .nav-left {
    flex-direction: column;
    align-items: flex-start;
    gap: 15px;
  }
  
  .nav-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 15px;
  }
  
  .user-info {
    width: 100%;
    justify-content: space-between;
  }
}

@media (max-width: 768px) {
  .content-area {
    padding: 15px;
  }
  
  .nav-tabs {
    flex-wrap: wrap;
    width: 100%;
  }
  
  .nav-tab {
    font-size: 0.85rem;
    padding: 8px 12px;
    flex: 1;
    min-width: 100px;
  }
  
  .app-title {
    font-size: 1.1rem;
  }
}
</style>