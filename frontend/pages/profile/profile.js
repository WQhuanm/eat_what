const app = getApp()

Page({
  data: { username: '', isAdmin: false },

  onShow() {
    if (!app.checkLogin()) return
      this.setData({
      username: wx.getStorageSync('username') || '用户',
      isAdmin: app.globalData.isAdmin // 确保动态设置管理员身份
    })
  },

  goEditProfile() {
    wx.navigateTo({ url: '/pages/editProfile/editProfile' })
  },
  goAddDish() {
    wx.navigateTo({ url: '/pages/addDish/addDish' })
  },
  goAddShop() {
    wx.navigateTo({ url: '/pages/addShop/addShop' })
  },
  goHistory() {
    wx.switchTab({ url: '/pages/history/history' })
  },
  goReview() {
    wx.navigateTo({ url: '/pages/review/review' }) // 确保路径正确
  },
  onLogout() {
    wx.showModal({
      title: '提示',
      content: '确认退出登录？',
      success(res) {
        if (!res.confirm) return
        wx.removeStorageSync('token')
        wx.removeStorageSync('username')
        app.globalData.token = ''
        wx.reLaunch({ url: '/pages/login/login' })
      }
    })
  }
})
