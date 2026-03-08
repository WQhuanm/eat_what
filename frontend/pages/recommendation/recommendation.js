const api = require('../../utils/api')
const app = getApp()

Page({
  data: {
    batch_id: '',
    items: [],
    questionSnapshot: null
  },

  onLoad(options) {
    const cache = app.globalData.recommendCache
    if (cache) {
      const items = (cache.items || []).map(it => ({
        ...it,
        score_pct: Math.min(100, Math.max(0, Math.round((it.score || 0) * 100)))
      }))
      this.setData({
        batch_id: cache.batch_id,
        items: items,
        questionSnapshot: cache.questionSnapshot || null
      })
      app.globalData.recommendCache = null  // 用完清除
    } else {
      // 兜底：从URL参数读取（保持向后兼容）
      const batch_id = options.batch_id || ''
      let items = []
      try { items = JSON.parse(decodeURIComponent(options.items || '[]')) } catch (e) {}
      items = items.map(it => ({
        ...it,
        score_pct: Math.min(100, Math.max(0, Math.round((it.score || 0) * 100)))
      }))
      this.setData({ batch_id, items })
    }
  },

  async confirmDish(e) {
    const idx = e.currentTarget.dataset.index
    const dish = this.data.items[idx]
    wx.showModal({
      title: '就决定是你了！',
      content: `确认选择「${dish.dish_name}」？`,
      success: async (res) => {
        if (!res.confirm) return
        try {
          // 记录正样本（确认选择）
          await api.confirmSelection({
            batch_id: this.data.batch_id,
            selected_dish_id: dish.dish_id,
            question_snapshot: this.data.questionSnapshot
          })

          // 为其他未选菜品记录负样本
          this._logNegativeSamples(dish.dish_id)

          wx.showToast({ title: '已记录选择', icon: 'success' })
          setTimeout(() => {
            wx.switchTab({ url: '/pages/home/home' })
          }, 1500)
        } catch (err) {
          wx.showToast({ title: err.message || '记录失败', icon: 'none' })
        }
      }
    })
  },

  // 异步记录负样本，不阻塞主流程
  _logNegativeSamples(selectedId) {
    const batch_id = this.data.batch_id
    this.data.items.forEach(item => {
      if (item.dish_id !== selectedId) {
        api.logInteraction({
          recommendation_batch_id: batch_id,
          clicked_dish_id: item.dish_id,
          result: false
        }).catch(() => {}) // 静默失败
      }
    })
  },

  selectDish(e) {
    // 可扩展：跳转菜品详情
  },

  goBack() {
    wx.navigateBack()
  }
})
