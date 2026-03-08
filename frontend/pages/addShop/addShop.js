const api = require('../../utils/api')

Page({
  data: {
    submitting: false,
    form: {
      name: '', address: '', city: '', contact: '',
      latitude: null, longitude: null
    }
  },

  onInput(e) {
    const field = e.currentTarget.dataset.field
    this.setData({ [`form.${field}`]: e.detail.value })
  },

  onGetLocation() {
    wx.getLocation({
      type: 'gcj02',
      success: (res) => {
        this.setData({
          'form.latitude': res.latitude,
          'form.longitude': res.longitude
        })
        wx.showToast({ title: '定位成功', icon: 'success' })
      },
      fail: () => {
        wx.showToast({ title: '定位失败', icon: 'none' })
      }
    })
  },

  async submitShop() {
    if (!this.data.form.name) {
      wx.showToast({ title: '请输入店铺名称', icon: 'none' }); return
    }
    const f = this.data.form
    const payload = {
      name: f.name,
      address: f.address || null,
      city: f.city || null,
      contact: f.contact || null,
      latitude: f.latitude,
      longitude: f.longitude
    }
    this.setData({ submitting: true })
    try {
      await api.createShop(payload)
      wx.showToast({ title: '店铺添加成功', icon: 'success' })
      setTimeout(() => wx.navigateBack(), 1500)
    } catch (e) {
      wx.showToast({ title: e.message || '提交失败', icon: 'none' })
    }
    this.setData({ submitting: false })
  }
})
