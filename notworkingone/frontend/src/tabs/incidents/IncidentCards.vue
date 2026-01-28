<!-- src/tabs/incidents/IncidentCards.vue -->
<template>
  <div class="incident-cards">
    <div v-for="incident in incidents" :key="incident.id" 
         :class="['incident-card', incident.status]"
         @click="$emit('select', incident)">
      <!-- Image Thumbnail -->
      <div v-if="incident.image_path" class="incident-image-thumb">
        <img 
          :src="`/api/incident_images/${incident.image_path}`" 
          :alt="`${incident.weapon_type} detection`"
          @error="handleImageError"
        />
      </div>
      
      <div class="incident-header-row">
        <div :class="['status-badge', incident.status]">
          {{ formatStatus(incident.status) }}
        </div>
      </div>
      
      <div class="incident-info">
        <div class="info-row">
          <span class="label">Camera:</span>
          <span class="value">{{ incident.camera_name }}</span>
        </div>
        <div class="info-row">
          <span class="label">Location:</span>
          <span class="value">{{ incident.camera_location }}</span>
        </div>
        <div class="info-row">
          <span class="label">Weapon:</span>
          <span :class="['weapon-badge', incident.weapon_type]">
            {{ formatWeaponName(incident.weapon_type) }}
          </span>
        </div>
        <div class="info-row">
          <span class="label">Detected:</span>
          <span class="value">{{ formatDateTime(incident.detected_at) }}</span>
        </div>
        <div v-if="incident.assigned_to_username" class="info-row">
          <span class="label">Assigned:</span>
          <span class="value">{{ incident.assigned_to_username }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  incidents: {
    type: Array,
    required: true
  }
})

defineEmits(['select'])

function handleImageError(event) {
  console.error('Failed to load image:', event.target.src)
  event.target.style.display = 'none'
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
.incident-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 15px;
}

.incident-card {
  background: #f8f9fa;
  padding: 18px;
  border-radius: 10px;
  border-left: 4px solid #e74c3c;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
}

.incident-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.incident-card.pending { 
  border-left-color: #e74c3c;
  box-shadow: 0 0 0 2px rgba(231, 76, 60, 0.2);
}

.incident-card.responding { 
  border-left-color: #f39c12; 
}

.incident-card.resolved { 
  border-left-color: #27ae60; 
}

.incident-image-thumb {
  position: relative;
  width: 100%;
  height: 180px;
  margin-bottom: 12px;
  border-radius: 8px;
  overflow: hidden;
  background: #000;
}

.incident-image-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.incident-header-row {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  margin-bottom: 12px;
}

.incident-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
}

.label {
  color: #7f8c8d;
  min-width: 60px;
}

.value {
  color: #2c3e50;
  font-weight: 500;
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

@media (max-width: 768px) {
  .incident-cards {
    grid-template-columns: 1fr;
  }
}
</style>