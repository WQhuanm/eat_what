const api = require('../../utils/api')

Page({
  data: {
    shopId: null,
    shopName: '',
    address: '',
    dishes: [],
    loading: true
  },

  async onLoad(options) {
    const shopId = options.id
    if (!shopId) {
      wx.showToast({ title: '商家ID缺失', icon: 'none' })
      return
    }
    this.setData({ shopId })
    await this.loadShopDetail(shopId)
  },

  async loadShopDetail(shopId) {
    this.setData({ loading: true })
    try {
      const res = await api.getShopDishes(shopId)
      this.setData({
        shopName: res.shop_name,
        address: res.address,
        dishes: res.dishes || [],
        loading: false
      })
    } catch (e) {
      wx.showToast({ title: e.message || '加载失败', icon: 'none' })
      this.setData({ loading: false })
    }
  },

  goDishDetail(e) {
    const dishId = e.currentTarget.dataset.id
    wx.navigateTo({
      url: `/pages/dishDetail/dishDetail?id=${dishId}`
    })
  }
})
