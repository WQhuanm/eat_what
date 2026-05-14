const api = require('../../utils/api')

Page({
  data: {
    isNew: true,
    saving: false,
    form: {
      age: null, gender: null, height: null, weight: null,
      activity_factor: null, health_goal: '',
      taste_preferences: {},
      cuisine_preferences: [], avoid_foods: []
    },
    activityIndex: 0,
    activityOptions: ['久坐 (1.2)', '轻度活动 (1.375)', '中度活动 (1.55)', '高强度 (1.725)'],
    activityValues: [1.2, 1.375, 1.55, 1.725],
    goalOptions: ['减脂', '增肌', '维持现状'],
    tasteKeys: ['酸', '甜', '苦', '辣', '咸'],
    cuisineOptions: ['烧烤烤肉', '奶茶果汁', '炸鸡炸串', '鸭脖卤味', '特色小吃', '米粉面条', '快餐便当', '汉堡薯条', '粥食点心', '地方菜系', '麻辣烫冒菜', '饺子馄饨'],
    avoidOptions: ['清真（不吃猪肉）', '素食', '花生过敏', '海鲜过敏', '乳糖不耐', '不吃香菜', '不吃葱/蒜', '不吃辣', '不吃油腻']
  },

  async onLoad() {
    try {
      const profile = await api.getProfile()
      const ai = this.data.activityValues.indexOf(profile.activity_factor)
      this.setData({
        isNew: false,
        form: {
          age: profile.age,
          gender: profile.gender,
          height: profile.height,
          weight: profile.weight,
          activity_factor: profile.activity_factor,
          health_goal: profile.health_goal || '',
          taste_preferences: profile.taste_preferences || {},
          cuisine_preferences: profile.cuisine_preferences || [],
          avoid_foods: profile.avoid_foods || []
        },
        activityIndex: ai >= 0 ? ai : 0
      })
    } catch (e) {
      // 404 = 尚未创建
      this.setData({ isNew: true })
    }
  },

  onInput(e) {
    const field = e.currentTarget.dataset.field
    const val = e.detail.value
    this.setData({ [`form.${field}`]: val })
  },

  setGender(e) {
    this.setData({ 'form.gender': Number(e.currentTarget.dataset.val) })
  },

  onActivityChange(e) {
    const idx = e.detail.value
    this.setData({
      activityIndex: idx,
      'form.activity_factor': this.data.activityValues[idx]
    })
  },

  setGoal(e) {
    this.setData({ 'form.health_goal': e.currentTarget.dataset.val })
  },

  onTasteChange(e) {
    const key = e.currentTarget.dataset.key
    this.setData({ [`form.taste_preferences.${key}`]: e.detail.value })
  },

  toggleCuisine(e) {
    const val = e.currentTarget.dataset.val
    let arr = [...this.data.form.cuisine_preferences]
    const idx = arr.indexOf(val)
    idx >= 0 ? arr.splice(idx, 1) : arr.push(val)
    this.setData({ 'form.cuisine_preferences': arr })
  },

  toggleAvoid(e) {
    const val = e.currentTarget.dataset.val
    let arr = [...this.data.form.avoid_foods]
    const idx = arr.indexOf(val)
    idx >= 0 ? arr.splice(idx, 1) : arr.push(val)
    this.setData({ 'form.avoid_foods': arr })
  },

  async saveProfile() {
    const f = this.data.form
    const payload = {
      age: f.age ? Number(f.age) : null,
      gender: f.gender,
      height: f.height ? Number(f.height) : null,
      weight: f.weight ? Number(f.weight) : null,
      activity_factor: f.activity_factor,
      health_goal: f.health_goal || null,
      taste_preferences: f.taste_preferences,
      cuisine_preferences: f.cuisine_preferences,
      avoid_foods: f.avoid_foods
    }
    this.setData({ saving: true })
    try {
      if (this.data.isNew) {
        await api.createProfile(payload)
      } else {
        await api.updateProfile(payload)
      }
      wx.showToast({ title: '保存成功', icon: 'success' })
      this.setData({ isNew: false })
    } catch (e) {
      wx.showToast({ title: e.message || '保存失败', icon: 'none' })
    }
    this.setData({ saving: false })
  }
})
