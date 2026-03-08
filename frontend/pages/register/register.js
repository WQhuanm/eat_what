const api = require('../../utils/api')

Page({
  data: { username: '', password: '', confirm: '', loading: false },
  onUsernameInput(e) { this.setData({ username: e.detail.value }) },
  onPasswordInput(e) { this.setData({ password: e.detail.value }) },
  onConfirmInput(e) { this.setData({ confirm: e.detail.value }) },

  async onRegister() {
    const { username, password, confirm } = this.data
    if (!username || !password) {
      wx.showToast({ title: '请填写完整', icon: 'none' }); return
    }
    if (password !== confirm) {
      wx.showToast({ title: '两次密码不一致', icon: 'none' }); return
    }
    this.setData({ loading: true })
    try {
      await api.register({ username, password })
      wx.showToast({ title: '注册成功', icon: 'success' })
      setTimeout(() => wx.navigateBack(), 1500)
    } catch (err) {
      wx.showToast({ title: err.message || '注册失败', icon: 'none' })
    }
    this.setData({ loading: false })
  }
})
