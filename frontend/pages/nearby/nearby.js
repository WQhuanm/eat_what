const api = require('../../utils/api')
const locationUtil = require('../../utils/location')

Page({
  data: {
    tab: 'dishes', // dishes | shops
    items: [],
    shops: [],
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

  switchTab(e) {
    const tab = e.currentTarget.dataset.tab
    this.setData({ tab })
    if (tab === 'shops' && this.data.shops.length === 0) {
      this.fetchNearbyShops(this.data.latitude, this.data.longitude)
    }
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
        
        if (this.data.tab === 'dishes') {
          await this.fetchNearbyDishes(loc.latitude, loc.longitude)
        } else {
          await this.fetchNearbyShops(loc.latitude, loc.longitude)
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

  async fetchNearbyDishes(lat, lon) {
    try {
      const items = await api.getNearbyDishes(lat, lon, this.data.radiusKm, 50, 0)
      this.setData({ items: items || [] })
    } catch (e) {
      wx.showToast({ title: e.message || '加载失败', icon: 'none' })
    }
  },

  async fetchNearbyShops(lat, lon) {
    try {
      const shops = await api.getNearbyShops(lat, lon, this.data.radiusKm, 30, 0)
      this.setData({ shops: shops || [] })
    } catch (e) {
      wx.showToast({ title: e.message || '加载失败', icon: 'none' })
    }
  },

  goDetail(e) {
    const idx = e.currentTarget.dataset.index
    const item = this.data.items[idx]
    wx.navigateTo({
      url: `/pages/dishDetail/dishDetail?id=${item.dish_id}`
    })
  },

  goShopDetail(e) {
    const shopId = e.currentTarget.dataset.id
    wx.navigateTo({
      url: `/pages/shopDetail/shopDetail?id=${shopId}`
    })
  },

  // 管理员功能...
})
