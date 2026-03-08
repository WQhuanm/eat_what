const api = require('../../utils/api')
const app = getApp()

Page({
  data: {
    submitting: false,
    form: {
      name: '', shop_id: null, cuisine: '', taste_tags: [], price: null,
      calories: null, protein: null, fat: null, carbohydrate: null,
      ingredients: [], description: '', dining_forms: [],
      city: '', latitude: null, longitude: null, image_urls: []
    },
    ingredientsText: '',
    cuisineIndex: -1,
    cuisineOptions: ['川湘菜', '江浙菜', '粤菜', '日韩料理', '西餐', '快餐便当', '东北菜', '其他'],
    tasteOptions: ['酸', '甜', '辣', '咸', '清淡', '苦'],
    diningFormOptions: ['外卖配送', '到店堂食', '打包带走'],
    shops: [],
    shopNames: [],
    shopIndex: -1,
    previewImages: []
  },

  onShow() {
    this.loadShops()
  },

  async loadShops() {
    try {
      const shops = await api.getShops()
      this.setData({
        shops,
        shopNames: ['不选择店铺', ...shops.map(s => s.name)]
      })
    } catch (e) {}
  },

  onInput(e) {
    const field = e.currentTarget.dataset.field
    this.setData({ [`form.${field}`]: e.detail.value })
  },

  onShopChange(e) {
    const idx = Number(e.detail.value)
    if (idx === 0) {
      this.setData({ shopIndex: 0, 'form.shop_id': null })
    } else {
      const shop = this.data.shops[idx - 1]
      this.setData({
        shopIndex: idx,
        'form.shop_id': shop.id,
        'form.city': shop.city || this.data.form.city,
        'form.latitude': shop.latitude || this.data.form.latitude,
        'form.longitude': shop.longitude || this.data.form.longitude
      })
    }
  },

  goAddShop() {
    wx.navigateTo({ url: '/pages/addShop/addShop' })
  },

  onCuisineChange(e) {
    const idx = e.detail.value
    this.setData({ cuisineIndex: idx, 'form.cuisine': this.data.cuisineOptions[idx] })
  },

  toggleTaste(e) {
    const val = e.currentTarget.dataset.val
    let arr = [...this.data.form.taste_tags]
    const idx = arr.indexOf(val)
    idx >= 0 ? arr.splice(idx, 1) : arr.push(val)
    this.setData({ 'form.taste_tags': arr })
  },

  toggleDiningForm(e) {
    const val = e.currentTarget.dataset.val
    let arr = [...this.data.form.dining_forms]
    const idx = arr.indexOf(val)
    idx >= 0 ? arr.splice(idx, 1) : arr.push(val)
    this.setData({ 'form.dining_forms': arr })
  },

  onIngredientsInput(e) {
    const text = e.detail.value
    this.setData({
      ingredientsText: text,
      'form.ingredients': text.split(/[,，]/).map(s => s.trim()).filter(Boolean)
    })
  },

  chooseImage() {
    wx.chooseMedia({
      count: 3 - this.data.previewImages.length,
      mediaType: ['image'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const newPaths = res.tempFiles.map(f => f.tempFilePath)
        this.setData({
          previewImages: [...this.data.previewImages, ...newPaths]
        })
        // TODO: 上传图片到后端获取URL，暂用本地路径占位
        this.setData({
          'form.image_urls': [...this.data.form.image_urls, ...newPaths]
        })
      }
    })
  },

  removeImage(e) {
    const idx = e.currentTarget.dataset.index
    let imgs = [...this.data.previewImages]
    let urls = [...this.data.form.image_urls]
    imgs.splice(idx, 1)
    urls.splice(idx, 1)
    this.setData({ previewImages: imgs, 'form.image_urls': urls })
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

  async submitDish() {
    const f = this.data.form
    if (!f.name) {
      wx.showToast({ title: '请输入菜品名称', icon: 'none' }); return
    }
    const payload = {
      name: f.name,
      shop_id: f.shop_id || null,
      cuisine: f.cuisine || null,
      taste_tags: f.taste_tags.length ? f.taste_tags : null,
      price: f.price ? Number(f.price) : null,
      calories: f.calories ? Number(f.calories) : null,
      protein: f.protein ? Number(f.protein) : null,
      fat: f.fat ? Number(f.fat) : null,
      carbohydrate: f.carbohydrate ? Number(f.carbohydrate) : null,
      ingredients: f.ingredients.length ? f.ingredients : null,
      description: f.description || null,
      dining_forms: f.dining_forms.length ? f.dining_forms : null,
      city: f.city || null,
      latitude: f.latitude,
      longitude: f.longitude,
      image_urls: f.image_urls.length ? f.image_urls : null
    }
    this.setData({ submitting: true })
    try {
      await api.createDish(payload)
      wx.showToast({ title: '提交成功', icon: 'success' })
      setTimeout(() => wx.navigateBack(), 1500)
    } catch (e) {
      wx.showToast({ title: e.message || '提交失败', icon: 'none' })
    }
    this.setData({ submitting: false })
  }
})
