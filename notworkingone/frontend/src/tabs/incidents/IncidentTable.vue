<!-- src/tabs/incidents/IncidentTable.vue -->
<template>
  <div class="table-view">
    <div class="table-header">
      <div class="th-status" @click="$emit('sort', 'status')">
        Status
        <span v-if="sortColumn === 'status'" class="sort-icon">
          {{ sortDirection === 'asc' ? '▲' : '▼' }}
        </span>
      </div>
      <div class="th-weapon" @click="$emit('sort', 'weapon_type')">
        Weapon
        <span v-if="sortColumn === 'weapon_type'" class="sort-icon">
          {{ sortDirection === 'asc' ? '▲' : '▼' }}
        </span>
      </div>
      <div class="th-camera" @click="$emit('sort', 'camera_name')">
        Camera
        <span v-if="sortColumn === 'camera_name'" class="sort-icon">
          {{ sortDirection === 'asc' ? '▲' : '▼' }}
        </span>
      </div>
      <div class="th-location" @click="$emit('sort', 'camera_location')">
        Location
        <span v-if="sortColumn === 'camera_location'" class="sort-icon">
          {{ sortDirection === 'asc' ? '▲' : '▼' }}
        </span>
      </div>
      <div class="th-time" @click="$emit('sort', 'detected_at')">
        Detected At
        <span v-if="sortColumn === 'detected_at'" class="sort-icon">
          {{ sortDirection === 'asc' ? '▲' : '▼' }}
        </span>
      </div>
      <div class="th-officer" @click="$emit('sort', 'assigned_to_username')">
        Assigned To
        <span v-if="sortColumn === 'assigned_to_username'" class="sort-icon">
          {{ sortDirection === 'asc' ? '▲' : '▼' }}
        </span>
      </div>
    </div>

    <div 
      v-for="incident in incidents" 
      :key="incident.id" 
      :class="['table-row', incident.status]"
      @click="$emit('select', incident)"
    >
      <div class="td-status" data-label="Status">
        <span :class="['status-badge', incident.status]">
          {{ formatStatus(incident.status) }}
        </span>
      </div>
      <div class="td-weapon" data-label="Weapon">
        <span :class="['weapon-badge', incident.weapon_type]">
          {{ formatWeaponName(incident.weapon_type) }}
        </span>
      </div>
      <div class="td-camera" data-label="Camera">
        <strong>{{ incident.camera_name }}</strong>
      </div>
      <div class="td-location" data-label="Location">
        {{ incident.camera_location }}
      </div>
      <div class="td-time" data-label="Detected At">
        {{ formatDateTime(incident.detected_at) }}
      </div>
      <div class="td-officer" data-label="Assigned To">
        {{ incident.assigned_to_username || '-' }}
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  incidents: Array,
  sortColumn: String,
  sortDirection: String
})

defineEmits(['select', 'sort'])

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
.table-view {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.table-header {
  display: grid;
  grid-template-columns: 110px 120px 150px 1fr 180px 140px;
  gap: 12px;
  padding: 12px 16px;
  background: #f8f9fa;
  border-radius: 8px;
  font-weight: 600;
  color: #2c3e50;
  font-size: 0.9rem;
}

.table-header > div {
  cursor: pointer;
  user-select: none;
  transition: color 0.2s ease;
}

.table-header > div:hover {
  color: #4a90e2;
}

.sort-icon {
  margin-left: 4px;
  color: #4a90e2;
  font-size: 0.8rem;
}

.table-row {
  display: grid;
  grid-template-columns: 110px 120px 150px 1fr 180px 140px;
  gap: 12px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  border-left: 4px solid transparent;
  align-items: center;
}

.table-row:hover {
  background: #e9ecef;
  transform: translateX(4px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.table-row.pending { border-left-color: #e74c3c; }
.table-row.responding { border-left-color: #f39c12; }
.table-row.resolved { border-left-color: #27ae60; }

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

@media (max-width: 1200px) {
  .table-header,
  .table-row {
    grid-template-columns: 100px 110px 140px 1fr 160px 120px;
    font-size: 0.85rem;
  }
}

@media (max-width: 768px) {
  .table-header {
    display: none;
  }
  
  .table-row {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 16px;
  }
  
  .table-row > div {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .table-row > div::before {
    content: attr(data-label);
    font-weight: 600;
    color: #7f8c8d;
    font-size: 0.85rem;
  }
}
</style>