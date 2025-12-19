class DetectionService {
  constructor() {
    this.listeners = []
    this.currentDetection = {
      detected: false,
      objects: {},
      timestamp: null
    }
    this.detectionHistory = []
    this.isPolling = false
    this.pollInterval = null
    this.lastCheckTime = 'Never'
    this.isConnected = false
  }

  // Start polling for detections
  startPolling(token) {
    if (this.isPolling) return
    
    this.isPolling = true
    this.token = token
    
    // Initial check
    this.checkDetection()
    
    // Poll every 2 seconds
    this.pollInterval = setInterval(() => {
      this.checkDetection()
    }, 2000)
    
    console.log('🔍 Detection service started - polling every 2 seconds')
  }

  // Stop polling
  stopPolling() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval)
      this.pollInterval = null
    }
    this.isPolling = false
    console.log('🛑 Detection service stopped')
  }

  // Check for new detections
  async checkDetection() {
    try {
      const response = await fetch('http://localhost:6001/detection', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        this.isConnected = true
        this.lastCheckTime = new Date().toLocaleTimeString()
        
        // Check if this is a new detection
        const hasObjects = data.objects && Object.keys(data.objects).length > 0
        const isNewDetection = data.detected && hasObjects && 
                               data.timestamp !== this.currentDetection.timestamp
        
        if (isNewDetection) {
          console.log('🚨 NEW DETECTION:', data)
          
          // Add to history
          this.detectionHistory.unshift({
            detected: data.detected,
            objects: data.objects,
            timestamp: data.timestamp
          })
          
          // Keep only last 50 detections
          if (this.detectionHistory.length > 50) {
            this.detectionHistory = this.detectionHistory.slice(0, 50)
          }
          
          // Play alert sound
          this.playAlertSound()
          
          // Show browser notification
          this.showNotification(data)
          
          // Auto-log detection to backend
          this.logDetectionToBackend(data)
        }
        
        // Update current detection
        this.currentDetection = data
        
        // Notify all listeners
        this.notifyListeners()
      } else {
        this.isConnected = false
        this.notifyListeners()
      }
    } catch (error) {
      console.error('Error checking detection:', error)
      this.isConnected = false
      this.notifyListeners()
    }
  }

  // Log detection to backend
  async logDetectionToBackend(detection) {
    if (!this.token) return
    
    try {
      // Log each detected weapon
      for (const [weaponType, data] of Object.entries(detection.objects)) {
        const count = data.count || 0
        const confidences = data.confidences || []
        
        if (count > 0 && confidences.length > 0) {
          const avgConfidence = confidences.reduce((a, b) => a + b, 0) / confidences.length
          
          // Normalize weapon type
          const normalizedType = this.normalizeWeaponType(weaponType)
          
          // Log to backend
          await fetch('/api/log-detection', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${this.token}`
            },
            body: JSON.stringify({
              camera_id: 1, // Default camera, you can make this dynamic
              weapon_type: normalizedType,
              confidence_score: avgConfidence
            })
          })
          
          console.log(`✓ Logged ${normalizedType} detection (${(avgConfidence * 100).toFixed(1)}% confidence)`)
        }
      }
    } catch (error) {
      console.error('Error logging detection to backend:', error)
    }
  }

  // Normalize weapon type
  normalizeWeaponType(weaponType) {
    const mapping = {
      'gun': 'pistol',
      'heavy-weapon': 'heavy_weapon',
      'knife': 'knife',
      'pistol': 'pistol',
      'heavy_weapon': 'heavy_weapon'
    }
    return mapping[weaponType.toLowerCase()] || weaponType.toLowerCase()
  }

  // Play alert sound
  playAlertSound() {
    try {
      const audioContext = new (window.AudioContext || window.webkitAudioContext)()
      
      // Play 3 beeps
      this.playBeep(audioContext, 880, 0.2, 0)
      this.playBeep(audioContext, 880, 0.2, 0.3)
      this.playBeep(audioContext, 880, 0.4, 0.6)
    } catch (error) {
      console.error('Could not play alert sound:', error)
    }
  }

  playBeep(audioContext, frequency, duration, delay) {
    setTimeout(() => {
      const oscillator = audioContext.createOscillator()
      const gainNode = audioContext.createGain()
      
      oscillator.connect(gainNode)
      gainNode.connect(audioContext.destination)
      
      oscillator.frequency.value = frequency
      oscillator.type = 'sine'
      
      gainNode.gain.setValueAtTime(0.3, audioContext.currentTime)
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + duration)
      
      oscillator.start(audioContext.currentTime)
      oscillator.stop(audioContext.currentTime + duration)
    }, delay * 1000)
  }

  // Show browser notification
  async showNotification(detection) {
    if ('Notification' in window && Notification.permission === 'granted') {
      const weaponList = Object.keys(detection.objects)
        .map(w => this.formatWeaponName(w))
        .join(', ')
      
      new Notification('🚨 Weapon Detected!', {
        body: `${weaponList} detected at ${new Date().toLocaleTimeString()}`,
        icon: '/favicon.ico',
        tag: 'weapon-detection',
        requireInteraction: true
      })
    } else if ('Notification' in window && Notification.permission === 'default') {
      await Notification.requestPermission()
    }
  }

  // Format weapon name
  formatWeaponName(weaponType) {
    const names = {
      'gun': 'Gun/Pistol',
      'heavy-weapon': 'Heavy Weapon',
      'heavy_weapon': 'Heavy Weapon',
      'knife': 'Knife',
      'pistol': 'Pistol'
    }
    return names[weaponType] || weaponType.replace('-', ' ').replace('_', ' ')
  }

  // Subscribe to detection updates
  subscribe(callback) {
    this.listeners.push(callback)
    
    // Immediately call with current state
    callback({
      currentDetection: this.currentDetection,
      detectionHistory: this.detectionHistory,
      lastCheckTime: this.lastCheckTime,
      isConnected: this.isConnected
    })
    
    // Return unsubscribe function
    return () => {
      this.listeners = this.listeners.filter(cb => cb !== callback)
    }
  }

  // Notify all listeners
  notifyListeners() {
    const state = {
      currentDetection: this.currentDetection,
      detectionHistory: this.detectionHistory,
      lastCheckTime: this.lastCheckTime,
      isConnected: this.isConnected
    }
    
    this.listeners.forEach(callback => {
      try {
        callback(state)
      } catch (error) {
        console.error('Error in detection listener:', error)
      }
    })
  }

  // Get current state
  getState() {
    return {
      currentDetection: this.currentDetection,
      detectionHistory: this.detectionHistory,
      lastCheckTime: this.lastCheckTime,
      isConnected: this.isConnected
    }
  }
}

// Create singleton instance
const detectionService = new DetectionService()

export default detectionService