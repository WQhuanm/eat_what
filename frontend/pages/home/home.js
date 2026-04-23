const app = getApp()
const locationUtil = require('../../utils/location')

Page({
  data: {
    currentLocationText: '定位中...',
    showCoords: false,
  },

  onLoad() {
    this.setData({ showCoords: !!app.globalData.showDebugCoordinates })
  },

  onShow() {
    app.checkLogin()
    this.loadLocationLabel()
  },
  startRecommend() {
    wx.navigateTo({ url: '/pages/questionnaire/questionnaire' })
  },
  goNearby() {
    wx.navigateTo({ url: '/pages/nearby/nearby' })
  },

  loadLocationLabel() {
    wx.getSetting({
      success: (setting) => {
        const granted = !!(setting.authSetting && setting.authSetting['scope.userLocation'])
        if (!granted) {
          wx.authorize({
            scope: 'scope.userLocation',
            success: () => this.fetchLocationText(),
            fail: () => this.setData({ currentLocationText: '当前位置：未授权，请在设置中开启定位权限' })
          })
          return
        }
        this.fetchLocationText()
      },
      fail: () => {
        this.setData({ currentLocationText: '当前位置：权限检查失败' })
      }
    })
  },

  fetchLocationText() {
    locationUtil.getLocationWithName()
      .then((loc) => {
        const title = this.data.showCoords
          ? `${loc.latitude.toFixed(4)}, ${loc.longitude.toFixed(4)}`
          : '已获取'
        this.setData({
          currentLocationText: `当前位置：${title}`
        })
      })
      .catch(() => {
        this.setData({ currentLocationText: '当前位置：获取失败，请检查定位权限与系统定位开关' })
      })
      .finally(() => {
        wx.stopLocationUpdate({ fail: () => {} })
      })
  }
})
