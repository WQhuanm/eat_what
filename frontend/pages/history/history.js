const api = require('../../utils/api')
const app = getApp()

Page({
  data: {
    records: [],
    skip: 0,
    limit: 20,
    hasMore: true
  },

  onShow() {
    if (!app.checkLogin()) return
    this.setData({ records: [], skip: 0, hasMore: true })
    this.loadData()
  },

  async loadData() {
    try {
      const list = await api.getHistory(this.data.skip, this.data.limit)
      const formatted = list.map(r => ({
        ...r,
        dining_time_fmt: r.dining_time ? r.dining_time.replace('T', ' ').substring(0, 16) : ''
      }))
      this.setData({
        records: [...this.data.records, ...formatted],
        skip: this.data.skip + list.length,
        hasMore: list.length >= this.data.limit
      })
    } catch (e) {
      wx.showToast({ title: '加载失败', icon: 'none' })
    }
  },

  loadMore() { this.loadData() },

  goDetail(e) {
    const record = this.data.records[e.currentTarget.dataset.index]
    wx.navigateTo({
      url: '/pages/dishDetail/dishDetail?payload=' + encodeURIComponent(JSON.stringify(record))
    })
  },

  // 再来一次：基于历史选择重新选择同一菜品
  reSelect(e) {
    const record = this.data.records[e.currentTarget.dataset.index]
    if (!record.selected_dish_id) return
    wx.showModal({
      title: '再来一次',
      content: `确认再次选择「${record.dish_name}」？`,
      success: async (res) => {
        if (!res.confirm) return
        try {
          await api.confirmSelection({
            batch_id: 'reselect-' + Date.now(),
            selected_dish_id: record.selected_dish_id
          })
          wx.showToast({ title: '已记录选择', icon: 'success' })
        } catch (err) {
          wx.showToast({ title: err.message || '操作失败', icon: 'none' })
        }
      }
    })
  }
})
