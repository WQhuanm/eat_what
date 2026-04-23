App({
  globalData: {
    token: '',
    userInfo: null,
    isAdmin: false, // 是否为管理员
    baseUrl: 'http://localhost:8000',
    showDebugCoordinates: true, // 调试时显示经纬度
    recommendCache: null // 用于页面间传递推荐结果，避免URL超限
  },
  onLaunch() {
    const token = wx.getStorageSync('token')
    const isAdmin = wx.getStorageSync('isAdmin') // 从本地存储读取管理员身份
    if (token) {
      this.globalData.token = token
      this.globalData.isAdmin = !!isAdmin // 确保正确初始化
    }
  },
  checkLogin() {
    if (!this.globalData.token) {
      wx.reLaunch({ url: '/pages/login/login' })
      return false
    }
    return true
  }
})
