const api = require('../../utils/api')
const app = getApp()

Page({
  data: {
    questions: [],
    currentIndex: 0,
    selectedMap: {},
    progress: 0,
    submitting: false,
    latitude: 0,
    longitude: 0,
  },

  async onLoad() {
    try {
      const questions = await api.getQuestions()
      this.setData({
        questions,
        progress: questions.length ? (1 / questions.length) * 100 : 0,
      })
    } catch (e) {
      wx.showToast({ title: '加载问题失败', icon: 'none' })
    }
    this.getLocation()
  },

  getLocation() {
    wx.getSetting({
      success: (res) => {
        if (res.authSetting['scope.userLocation']) {
          this._fetchLocation()
        } else {
          wx.authorize({
            scope: 'scope.userLocation',
            success: () => this._fetchLocation(),
            fail: () => {
              wx.showToast({ title: '请授权定位', icon: 'none' })
            },
          })
        }
      },
    })
  },

  _fetchLocation() {
    wx.getLocation({
      type: 'gcj02',
      success: (res) => {
        this.setData({ latitude: res.latitude, longitude: res.longitude })
      },
      fail: () => {
        wx.showToast({ title: '定位失败，请稍后重试', icon: 'none' })
      },
    })
  },

  selectOption(e) {
    const { key, value, multi } = e.currentTarget.dataset
    const map = { ...this.data.selectedMap }
    if (!map[key]) map[key] = []

    if (Number(multi) === 1) {
      const idx = map[key].indexOf(value)
      if (idx >= 0) map[key].splice(idx, 1)
      else map[key].push(value)
    } else {
      map[key] = [value]
    }
    this.setData({ selectedMap: map })
  },

  onScaleChange(e) {
    const key = e.currentTarget.dataset.key
    const map = { ...this.data.selectedMap }
    map[key] = [Number(e.detail.value)]
    this.setData({ selectedMap: map })
  },

  onTextInput(e) {
    const key = e.currentTarget.dataset.key
    const map = { ...this.data.selectedMap }
    map[key] = [e.detail.value || '']
    this.setData({ selectedMap: map })
  },

  nextQuestion() {
    const q = this.data.questions[this.data.currentIndex]
    const key = q.question_key
    const optional = ['special_requirements', 'special_state'].includes(key)
    if (!optional && (!this.data.selectedMap[key] || this.data.selectedMap[key].length === 0)) {
      wx.showToast({ title: '请先完成当前题目', icon: 'none' })
      return
    }
    const nextIdx = this.data.currentIndex + 1
    this.setData({
      currentIndex: nextIdx,
      progress: ((nextIdx + 1) / this.data.questions.length) * 100,
    })
  },

  prevQuestion() {
    const prev = this.data.currentIndex - 1
    this.setData({
      currentIndex: prev,
      progress: ((prev + 1) / this.data.questions.length) * 100,
    })
  },

  _readSingle(key, fallback = '') {
    const arr = this.data.selectedMap[key] || []
    return arr.length ? arr[0] : fallback
  },

  _readMulti(key) {
    return this.data.selectedMap[key] || []
  },

  _buildInstantWeights(payload) {
    const w = {}
    const tp = payload.taste_preference
    if (tp === '重口过瘾') {
      w['辣'] = 0.9; w['咸'] = 0.6
    } else if (tp === '清淡本味') {
      w['清淡'] = 0.9
    } else if (tp === '酸甜开胃') {
      w['酸'] = 0.7; w['甜'] = 0.6
    } else if (tp === '奶甜香腻') {
      w['甜'] = 0.8
    } else if (tp === '酱香卤香') {
      w['咸'] = 0.8
    } else if (tp === '孜然烧烤') {
      w['咸'] = 0.6; w['辣'] = 0.4
    }

    w['辣'] = (w['辣'] || 0) + (payload.spicy_level / 5) * 0.8
    w['酸'] = (w['酸'] || 0) + (payload.sour_level / 5) * 0.7
    w['甜'] = (w['甜'] || 0) + (payload.sweet_level / 5) * 0.7
    w['咸'] = (w['咸'] || 0) + (payload.salty_level / 5) * 0.7
    w['清淡'] = (w['清淡'] || 0) + (1 - payload.oily_level / 5) * 0.5
    return w
  },

  async submitAnswers() {
    if (!this.data.latitude || !this.data.longitude) {
      wx.showToast({ title: '定位失败，请检查权限后重试', icon: 'none' })
      return
    }

    const payload = {
      meal_time: this._readSingle('meal_time', ''),
      dining_scene: this._readSingle('dining_scene', ''),
      dining_goal: this._readSingle('dining_goal', ''),
      decision_style: this._readSingle('decision_style', ''),
      dining_form: this._readSingle('dining_form', ''),
      budget: this._readSingle('budget', ''),
      taste_preference: this._readSingle('taste_preference', ''),
      cuisine_preference: this._readMulti('cuisine_preference').slice(0, 2),
      ingredient_preference: this._readSingle('ingredient_preference', ''),
      avoid_foods: this._readMulti('avoid_foods'),
      spicy_level: Number(this._readSingle('spicy_level', 0) || 0),
      numbing_level: Number(this._readSingle('numbing_level', 0) || 0),
      sour_level: Number(this._readSingle('sour_level', 0) || 0),
      sweet_level: Number(this._readSingle('sweet_level', 0) || 0),
      salty_level: Number(this._readSingle('salty_level', 0) || 0),
      oily_level: Number(this._readSingle('oily_level', 0) || 0),
      texture_preference: this._readSingle('texture_preference', ''),
      temperature_preference: this._readSingle('temperature_preference', ''),
      special_requirements: this._readSingle('special_requirements', ''),
      special_state: this._readSingle('special_state', '无'),
      follow_up_answers: null,
    }

    const required = ['meal_time', 'dining_scene', 'dining_goal', 'decision_style', 'dining_form', 'budget', 'taste_preference', 'ingredient_preference']
    for (let i = 0; i < required.length; i++) {
      if (!payload[required[i]]) {
        wx.showToast({ title: '请完成必填题', icon: 'none' })
        return
      }
    }

    payload.instant_weights = this._buildInstantWeights(payload)

    this.setData({ submitting: true })
    try {
      const res = await api.submitQuestionnaire(payload, this.data.latitude, this.data.longitude)
      app.globalData.recommendCache = {
        batch_id: res.batch_id,
        items: res.items,
        instantWeights: payload.instant_weights,
        questionSnapshot: payload,
      }
      wx.navigateTo({ url: '/pages/recommendation/recommendation' })
    } catch (e) {
      wx.showToast({ title: e.message || '提交失败', icon: 'none' })
    } finally {
      this.setData({ submitting: false })
    }
  },
})
