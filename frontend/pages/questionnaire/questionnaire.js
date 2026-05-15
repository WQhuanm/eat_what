const api = require('../../utils/api')
const app = getApp()

Page({
  data: {
    questions: [],
    currentIndex: 0,
    selectedMap: {},
    progress: 0,
    submitting: false,
    loadingQuestions: false,
    loadError: '',
    latitude: 0,
    longitude: 0,
  },

  async onLoad() {
    await this._loadQuestions()
    this.getLocation()
  },

  async onShow() {
    if (this.data.loadingQuestions) return

    // 页面栈返回后，若题库丢失则自动重载，避免白屏
    if (!this.data.questions.length) {
      await this._loadQuestions()
      return
    }

    this._resetRoundState()
  },

  _resetRoundState() {
    this.setData({
      currentIndex: 0,
      selectedMap: {},
      progress: this.data.questions.length ? (1 / this.data.questions.length) * 100 : 0,
      submitting: false,
    })
  },

  retryLoadQuestions() {
    this._loadQuestions()
  },

  async _loadQuestions() {
    if (this.data.loadingQuestions) return

    this.setData({
      loadingQuestions: true,
      loadError: '',
    })

    try {
      const questions = await api.getQuestions()
      if (!Array.isArray(questions) || questions.length === 0) {
        throw new Error('题目数据异常')
      }
      this.setData({
        questions,
        currentIndex: 0,
        selectedMap: {},
        progress: (1 / questions.length) * 100,
        submitting: false,
        loadingQuestions: false,
        loadError: '',
      })
    } catch (e) {
      this.setData({
        questions: [],
        currentIndex: 0,
        selectedMap: {},
        progress: 0,
        submitting: false,
        loadingQuestions: false,
        loadError: e.message || '无法加载问卷题目，请检查网络后重试',
      })
    }
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
    if (!this.data.questions.length) return

    const q = this.data.questions[this.data.currentIndex]
    const key = q.question_key
    const optional = q.required === false
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
    if (!this.data.questions.length) return

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
    if (payload.spicy_level != null) w['辣'] = (payload.spicy_level / 5) * 0.8
    if (payload.numbing_level != null) w['麻'] = (payload.numbing_level / 5) * 0.8
    if (payload.sour_level != null) w['酸'] = (payload.sour_level / 5) * 0.7
    if (payload.sweet_level != null) w['甜'] = (payload.sweet_level / 5) * 0.7
    if (payload.salty_level != null) w['咸'] = (payload.salty_level / 5) * 0.7
    if (payload.oily_level != null) w['清淡'] = (1 - payload.oily_level / 5) * 0.5
    return w
  },

  async submitAnswers() {
    if (!this.data.questions.length) {
      wx.showToast({ title: '题目未加载完成，请稍后重试', icon: 'none' })
      return
    }

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
      budget: this._readMulti('budget'),
      cuisine_preference: this._readMulti('cuisine_preference'),
      spicy_level: this.data.selectedMap['spicy_level'] ? Number(this.data.selectedMap['spicy_level'][0]) : null,
      numbing_level: this.data.selectedMap['numbing_level'] ? Number(this.data.selectedMap['numbing_level'][0]) : null,
      sour_level: this.data.selectedMap['sour_level'] ? Number(this.data.selectedMap['sour_level'][0]) : null,
      sweet_level: this.data.selectedMap['sweet_level'] ? Number(this.data.selectedMap['sweet_level'][0]) : null,
      salty_level: this.data.selectedMap['salty_level'] ? Number(this.data.selectedMap['salty_level'][0]) : null,
      oily_level: this.data.selectedMap['oily_level'] ? Number(this.data.selectedMap['oily_level'][0]) : null,
      follow_up_answers: null,
    }

    const required = ['meal_time', 'dining_scene', 'dining_goal', 
      'decision_style', 'dining_form', 'budget']

    for (let i = 0; i < required.length; i++) {
    const key = required[i]
    if (!payload[key]) {
    // 从 questions 数组中匹配当前 key 对应的中文题目
    const question = this.data.questions.find(q => q.question_key === key)
    // 适配常见字段名：title / question_text / text / label，找不到就回退显示 key
    const name = question 
    ? (question.question_text || question.text || question.label || key) 
    : key

    wx.showToast({ title: `请完成：${name}`, icon: 'none' })
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
