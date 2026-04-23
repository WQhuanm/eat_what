const api = require('../../utils/api')
const locationUtil = require('../../utils/location')

Page({
  data: {
    items: [],
    radiusKm: 5,
    isAdmin: false,
    adminPlaceName: '',
    latitude: null,
    longitude: null,
    locationStatus: '',
    hasManualAdminLocation: false,
    showCoords: false,
  },

  onShow() {
    this.setData({
      isAdmin: !!wx.getStorageSync('isAdmin'),
      showCoords: !!getApp().globalData.showDebugCoordinates,
    })
    this.loadNearby()
  },

  loadNearby() {
    wx.getSetting({
      success: (setting) => {
        const granted = !!(setting.authSetting && setting.authSetting['scope.userLocation'])
        if (!granted) {
          wx.authorize({
            scope: 'scope.userLocation',
            success: () => this.fetchNearbyByLocation(),
            fail: () => {
              this.setData({ locationStatus: '定位未授权，请在小程序设置中允许定位' })
              wx.showToast({ title: '定位未授权', icon: 'none' })
            }
          })
          return
        }
        this.fetchNearbyByLocation()
      },
      fail: () => {
        this.setData({ locationStatus: '定位权限检查失败' })
      }
    })
  },

  fetchNearbyByLocation() {
    locationUtil.getLocationWithName()
      .then(async (loc) => {
        if (this.data.hasManualAdminLocation && this.data.isAdmin) {
          return
        }

        this.setData({
          locationStatus: '定位成功（已用于附近商品检索）',
          latitude: loc.latitude,
          longitude: loc.longitude,
          adminPlaceName: loc.placeName || '当前位置',
        })
        try {
          const items = await api.getNearbyDishes(loc.latitude, loc.longitude, this.data.radiusKm, 50, 0)
          this.setData({ items: items || [] })
        } catch (e) {
          wx.showToast({ title: e.message || '加载失败', icon: 'none' })
        }
      })
      .catch(() => {
        this.setData({ locationStatus: '定位失败，请检查系统定位是否开启' })
        wx.showToast({ title: '定位失败', icon: 'none' })
      })
      .finally(() => {
        wx.stopLocationUpdate({ fail: () => {} })
      })
  },

  goDetail(e) {
    const idx = e.currentTarget.dataset.index
    const item = this.data.items[idx]
    wx.navigateTo({
      url: '/pages/dishDetail/dishDetail?payload=' + encodeURIComponent(JSON.stringify(item))
    })
  },

  chooseAdminLocation() {
    wx.chooseLocation({
      success: async (res) => {
        const lat = res.latitude
        const lng = res.longitude
        this.setData({
          latitude: lat,
          longitude: lng,
          adminPlaceName: res.name || res.address || '已选择位置',
          locationStatus: `管理位置已切换：${res.name || '已选择位置'}`,
          hasManualAdminLocation: true,
        })
        try {
          const items = await api.getNearbyDishes(lat, lng, this.data.radiusKm, 50, 0)
          this.setData({ items: items || [] })
          wx.showToast({ title: '已切换管理位置', icon: 'success' })
        } catch (e) {
          wx.showToast({ title: e.message || '加载失败', icon: 'none' })
        }
      },
      fail: () => {
        wx.showToast({ title: '未选择位置', icon: 'none' })
      }
    })
  },

  async useCurrentLocation() {
    try {
      const loc = await locationUtil.getLocationWithName()
      this.setData({
        latitude: loc.latitude,
        longitude: loc.longitude,
        adminPlaceName: loc.placeName || '当前位置',
        locationStatus: '已切换为当前位置',
        hasManualAdminLocation: false,
      })
      const items = await api.getNearbyDishes(loc.latitude, loc.longitude, this.data.radiusKm, 50, 0)
      this.setData({ items: items || [] })
      wx.showToast({ title: '已切换当前位置', icon: 'success' })
    } catch (e) {
      wx.showToast({ title: '定位失败', icon: 'none' })
    } finally {
      wx.stopLocationUpdate({ fail: () => {} })
    }
  },

})
