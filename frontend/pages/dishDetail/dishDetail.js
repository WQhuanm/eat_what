const api = require('../../utils/api')

Page({
  data: {
    dish: null,
  },

  normalizeDish(dish) {
    const list = Array.isArray(dish.taste_tags) ? dish.taste_tags : []
    const clean = list
      .map(x => (x == null ? '' : String(x)).trim())
      .filter(x => x && x !== '##')

    const desc = (dish.description == null ? '' : String(dish.description)).trim()
    const hasRepeatedTaste = clean.length > 0 && clean.some(t => desc.includes(t))
    const descDisplay = hasRepeatedTaste ? '' : desc

    return {
      ...dish,
      taste_display: clean.join(' / '),
      desc_display: descDisplay,
    }
  },

  onLoad(options) {
    if (options.payload) {
      try {
        const dish = JSON.parse(decodeURIComponent(options.payload))
        this.setData({ dish: this.normalizeDish(dish) })
        return
      } catch (e) {}
    }

    const id = Number(options.id || 0)
    if (id > 0) {
      this.loadDish(id)
    }
  },

  async loadDish(id) {
    try {
      const dish = await api.getDish(id)
      this.setData({ dish: this.normalizeDish(dish) })
    } catch (e) {
      wx.showToast({ title: e.message || '加载失败', icon: 'none' })
    }
  }
})
