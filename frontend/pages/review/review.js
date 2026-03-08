const api = require('../../utils/api')

Page({
  data: {
    items: [] // 待审核的菜品和店铺
  },

  onShow() {
    const isAdmin = wx.getStorageSync('isAdmin')
    if (!isAdmin) {
      wx.showToast({ title: '无管理员权限', icon: 'none' })
      setTimeout(() => { wx.navigateBack() }, 1500)
      return
    }
    this.loadPendingItems()
  },

  async loadPendingItems() {
    wx.showLoading({ title: '加载中' })
    try {
      const dishesRes = await api.getDishes('is_approved=false')
      const shopsRes = await api.getShops()
      // 兼容返回数组或 { results: [] } 格式
      const dishes = Array.isArray(dishesRes) ? dishesRes : (dishesRes.results || dishesRes.data || [])
      const shops = Array.isArray(shopsRes) ? shopsRes : (shopsRes.results || shopsRes.data || [])
      // 店铺也需要过滤未审核的
      const pendingShops = shops.filter(s => s.is_approved === false)
      const items = [
        ...dishes.map(d => ({ id: d.id, name: d.name, type: 'dish' })),
        ...pendingShops.map(s => ({ id: s.id, name: s.name, type: 'shop' }))
      ]
      this.setData({ items })
      if (items.length === 0) {
        console.log('暂无待审核项') // 调试输出
      }
    } catch (e) {
      console.error('加载待审核项失败:', e)
      wx.showToast({ title: '加载失败', icon: 'none' })
    } finally {
      wx.hideLoading()
    }
  },

  async approveItem(e) {
    const { id, type } = e.currentTarget.dataset
    try {
      if (type === 'dish') {
        await api.approveDish(id)
      } else {
        await api.approveShop(id)
      }
      wx.showToast({ title: '审核通过', icon: 'success' })
      this.loadPendingItems()
    } catch (e) {
      wx.showToast({ title: '操作失败', icon: 'none' })
    }
  },

  async rejectItem(e) {
    const { id, type } = e.currentTarget.dataset
    if (!id || !type) return
    wx.showModal({
      title: '确认拒绝',
      content: '拒绝后该项将被删除，是否继续？',
      success: async (res) => {
        if (res.confirm) {
          try {
            if (type === 'dish') {
              await api.rejectDish(id)
            } else {
              await api.rejectShop(id)
            }
            wx.showToast({ title: '已拒绝', icon: 'success' })
            this.loadPendingItems()
          } catch (e) {
            wx.showToast({ title: '操作失败', icon: 'none' })
          }
        }
      }
    })
  }
})
