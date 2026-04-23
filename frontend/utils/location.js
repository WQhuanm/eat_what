function getCurrentLocation() {
  return new Promise((resolve, reject) => {
    const tryGet = () => {
      wx.getLocation({
        type: 'gcj02',
        isHighAccuracy: true,
        highAccuracyExpireTime: 5000,
        success: resolve,
        fail: reject,
      })
    }

    wx.startLocationUpdate({
      success() {
        setTimeout(tryGet, 1200)
      },
      fail() {
        tryGet()
      },
    })
  })
}

async function getLocationWithName() {
  let lastErr = null
  for (let i = 0; i < 2; i++) {
    try {
      const loc = await getCurrentLocation()
      return {
        latitude: loc.latitude,
        longitude: loc.longitude,
        placeName: '',
      }
    } catch (err) {
      lastErr = err
    }
  }
  throw lastErr || new Error('定位失败')
}

module.exports = {
  getLocationWithName,
}
