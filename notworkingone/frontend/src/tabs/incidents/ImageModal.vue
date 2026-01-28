<!-- src/tabs/incidents/ImageModal.vue -->
<template>
  <div class="fullscreen-modal" @click="$emit('close')">
    <div class="fullscreen-content">
      <button @click="$emit('close')" class="fullscreen-close">✕</button>
      <img :src="imageUrl" alt="Incident capture fullscreen" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  imageUrl: {
    type: String,
    required: true
  }
})

defineEmits(['close'])
</script>

<style scoped>
.fullscreen-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.95);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 20px;
}

.fullscreen-content {
  position: relative;
  max-width: 95vw;
  max-height: 95vh;
}

.fullscreen-content img {
  max-width: 100%;
  max-height: 95vh;
  object-fit: contain;
  border-radius: 8px;
}

.fullscreen-close {
  position: absolute;
  top: -40px;
  right: 0;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: none;
  font-size: 2rem;
  width: 50px;
  height: 50px;
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.3s ease;
}

.fullscreen-close:hover {
  background: rgba(255, 255, 255, 0.3);
}

@media (max-width: 768px) {
  .fullscreen-close {
    top: 10px;
    right: 10px;
  }
}
</style>