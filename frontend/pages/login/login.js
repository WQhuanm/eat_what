const api = require('../../utils/api')
const app = getApp()

Page({
  data: {
    username: '',
    password: '',
    loading: false
  },
  onUsernameInput(e) { this.setData({ username: e.detail.value }) },
  onPasswordInput(e) { this.setData({ password: e.detail.value }) },

  async onLogin() {
    if (!this.data.username || !this.data.password) {
      wx.showToast({ title: '请填写完整', icon: 'none' }); return
    }
    this.setData({ loading: true })
    try {
      const res = await api.login({
        username: this.data.username,
        password: this.data.password
      })
      app.globalData.token = res.access_token
      app.globalData.isAdmin = res.is_admin // 确保保存管理员身份
      wx.setStorageSync('token', res.access_token)
      wx.setStorageSync('username', res.username || this.data.username)
      wx.setStorageSync('isAdmin', res.is_admin) // 确保保存到本地存储

      if (res.is_admin) {
        wx.showToast({ title: '欢迎管理员登录', icon: 'none' }) // 提示管理员登录
      }
      wx.switchTab({ url: '/pages/home/home' })
    } catch (err) {
      wx.showToast({ title: err.message || '登录失败', icon: 'none' })
    }
    this.setData({ loading: false })
  },

  goRegister() {
    wx.navigateTo({ url: '/pages/register/register' })
  }
})
