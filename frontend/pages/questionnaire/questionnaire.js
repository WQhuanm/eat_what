const api = require('../../utils/api')
const app = getApp()

// 动态追问规则：根据已有回答生成追加问题
const FOLLOW_UP_RULES = [
  {
    condition: (map) => map.taste_preference && map.taste_preference.indexOf('清爽解腻') >= 0,
    question: {
      question_key: 'want_soup',
      question_text: '要不要推荐汤类？',
      options: ['好呀，来碗汤', '不用了'],
      multi_select: false
    }
  },
  {
    condition: (map) => map.budget && map.budget[0] === '20元以下',
    question: {
      question_key: 'quick_meal',
      question_text: '预算有限，偏好哪种快餐？',
      options: ['面食', '盖饭', '小吃', '都行'],
      multi_select: false
    }
  },
  {
    condition: (map) => map.special_state && map.special_state[0] === '需要解压',
    question: {
      question_key: 'comfort_food',
      question_text: '想来点什么解压美食？',
      options: ['甜品蛋糕', '炸鸡炸物', '火锅烧烤', '随便来点'],
      multi_select: false
    }
  },
  {
    condition: (map) => map.special_state && map.special_state[0] === '胃不舒服',
    question: {
      question_key: 'stomach_care',
      question_text: '想吃点什么养胃的？',
      options: ['粥类', '面条汤面', '蒸菜', '都可以'],
      multi_select: false
    }
  },
  {
    condition: (map) => map.dining_scene && map.dining_scene[0] === '双人约会',
    question: {
      question_key: 'date_style',
      question_text: '约会想要什么氛围？',
      options: ['浪漫西餐', '日式料理', '特色小店', '不挑'],
      multi_select: false
    }
  }
]

Page({
  data: {
    questions: [],
    currentIndex: 0,
    selectedMap: {},
    progress: 0,
    submitting: false,
    latitude: 0,
    longitude: 0,
    baseQuestionCount: 0, // 初始问题数量
    dynamicInserted: false
  },

  async onLoad() {
    try {
      const questions = await api.getQuestions()
      this.setData({
        questions,
        baseQuestionCount: questions.length,
        progress: (1 / questions.length) * 100
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
          // 已授权，直接获取位置
          wx.getLocation({
            type: 'gcj02',
            success: (res) => {
              this.setData({ latitude: res.latitude, longitude: res.longitude })
            },
            fail: () => {
              wx.showToast({ title: '定位失败，请稍后重试', icon: 'none' })
            }
          })
        } else {
          // 未授权，提示用户授权
          wx.showModal({
            title: '提示',
            content: '需要获取您的地理位置，请前往设置中授权',
            success: (res) => {
              if (res.confirm) {
                wx.openSetting({
                  success: (res) => {
                    if (res.authSetting['scope.userLocation']) {
                      this.getLocation()
                    } else {
                      wx.showToast({ title: '请授权后重试', icon: 'none' })
                    }
                  }
                })
              }
            }
          })
        }
      }
    })
  },

  selectOption(e) {
    const { key, value, multi } = e.currentTarget.dataset
    let map = { ...this.data.selectedMap }
    if (!map[key]) map[key] = []

    if (Number(multi) === 1) {
      const idx = map[key].indexOf(value)
      if (idx >= 0) {
        map[key].splice(idx, 1) // 取消选择
      } else {
        map[key].push(value) // 添加选择
      }
    } else {
      map[key] = [value] // 单选直接覆盖
    }
    this.setData({ selectedMap: map })
  },

  nextQuestion() {
    const q = this.data.questions[this.data.currentIndex]
    const key = q.question_key
    // 可选题允许跳过（special_state 及动态追问题）
    const isOptional = key === 'special_state' || this.data.currentIndex >= this.data.baseQuestionCount
    if (!isOptional && (!this.data.selectedMap[key] || this.data.selectedMap[key].length === 0)) {
      wx.showToast({ title: '请先选择一个选项', icon: 'none' })
      return
    }

    const nextIdx = this.data.currentIndex + 1

    // 检查动态追问
    if (nextIdx >= this.data.baseQuestionCount && !this.data.dynamicInserted) {
      this._insertDynamicQuestions()
    }

    const total = this.data.questions.length
    this.setData({
      currentIndex: nextIdx,
      progress: ((nextIdx + 1) / total) * 100
    })
  },

  prevQuestion() {
    const prev = this.data.currentIndex - 1
    this.setData({
      currentIndex: prev,
      progress: ((prev + 1) / this.data.questions.length) * 100
    })
  },

  // 根据已有回答动态插入追问
  _insertDynamicQuestions() {
    const map = this.data.selectedMap
    const extras = []
    for (const rule of FOLLOW_UP_RULES) {
      if (rule.condition(map)) {
        // 避免重复插入
        const exists = this.data.questions.some(q => q.question_key === rule.question.question_key)
        if (!exists) {
          extras.push(rule.question)
        }
      }
    }
    if (extras.length > 0) {
      this.setData({
        questions: [...this.data.questions, ...extras],
        dynamicInserted: true
      })
    } else {
      this.setData({ dynamicInserted: true })
    }
  },

  // 即时画像权重积累
  _buildInstantWeights() {
    const map = this.data.selectedMap
    const weights = {}

    // 口味偏好权重
    const TASTE_W = {
      '清爽解腻': { '清淡': 0.8, '酸': 0.4, '辣': -0.5 },
      '麻辣刺激': { '辣': 0.9, '咸': 0.3 },
      '酸甜开胃': { '酸': 0.7, '甜': 0.6 },
      '浓郁咸香': { '咸': 0.8, '甜': -0.2 },
    }
    if (map.taste_preference) {
      map.taste_preference.forEach(pref => {
        const w = TASTE_W[pref] || {}
        Object.keys(w).forEach(k => {
          weights[k] = (weights[k] || 0) + w[k]
        })
      })
    }

    // 特殊状态权重
    const state = (map.special_state || [])[0]
    if (state === '需要解压') {
      weights['高热量'] = (weights['高热量'] || 0) + 0.8
      weights['甜'] = (weights['甜'] || 0) + 0.6
    } else if (state === '正在减脂') {
      weights['低卡'] = (weights['低卡'] || 0) + 0.9
      weights['清淡'] = (weights['清淡'] || 0) + 0.7
    } else if (state === '胃不舒服') {
      weights['流食'] = (weights['流食'] || 0) + 0.8
      weights['清淡'] = (weights['清淡'] || 0) + 0.6
    }

    // 动态追问权重
    if (map.want_soup && map.want_soup[0] === '好呀，来碗汤') {
      weights['汤类'] = (weights['汤类'] || 0) + 0.6
    }
    if (map.comfort_food) {
      const cf = map.comfort_food[0]
      if (cf === '甜品蛋糕') weights['甜'] = (weights['甜'] || 0) + 0.7
      if (cf === '炸鸡炸物') weights['高热量'] = (weights['高热量'] || 0) + 0.7
    }

    return weights
  },

  async submitAnswers() {
    const map = this.data.selectedMap

    // 提交前检查定位是否成功
    if (!this.data.latitude || !this.data.longitude) {
      wx.showToast({ title: '定位失败，请检查权限后重试', icon: 'none' })
      return
    }

    // 提交前最后检查：如果还没插入动态追问，先插入
    if (!this.data.dynamicInserted) {
      this._insertDynamicQuestions()
      if (this.data.questions.length > this.data.currentIndex + 1) {
        const nextIdx = this.data.currentIndex + 1
        this.setData({
          currentIndex: nextIdx,
          progress: ((nextIdx + 1) / this.data.questions.length) * 100
        })
        return
      }
    }

    // 收集基础回答
    const payload = {
      meal_time: (map.meal_time || [])[0] || '',
      taste_preference: map.taste_preference || [],
      dining_scene: (map.dining_scene || [])[0] || '',
      dining_form: (map.dining_form || [])[0] || '',
      budget: (map.budget || [])[0] || '',
      special_state: (map.special_state || ['无'])[0],
    }
    if (!payload.meal_time || !payload.dining_scene || !payload.dining_form || !payload.budget) {
      wx.showToast({ title: '请完成所有必选题', icon: 'none' })
      return
    }

    // 收集动态追问
    const followUp = {}
    this.data.questions.forEach(q => {
      if (
        q.question_key.indexOf('want_') === 0 ||
        q.question_key.indexOf('comfort_') === 0 ||
        q.question_key.indexOf('stomach_') === 0 ||
        q.question_key.indexOf('quick_') === 0 ||
        q.question_key.indexOf('date_') === 0
      ) {
        if (map[q.question_key]) {
          followUp[q.question_key] = map[q.question_key][0]
        }
      }
    })
    payload.follow_up_answers = Object.keys(followUp).length > 0 ? followUp : null

    // 构建即时画像权重并加入payload
    const instantWeights = this._buildInstantWeights()
    payload.instant_weights = instantWeights

    this.setData({ submitting: true })
    try {
      const res = await api.submitQuestionnaire(payload, this.data.latitude, this.data.longitude)
      const app = getApp()
      app.globalData.recommendCache = {
        batch_id: res.batch_id,
        items: res.items,
        instantWeights,
        questionSnapshot: { ...payload, instant_weights: instantWeights },
      }
      wx.navigateTo({
        url: '/pages/recommendation/recommendation',
      })
    } catch (e) {
      wx.showToast({ title: e.message || '提交失败', icon: 'none' })
    } finally {
      this.setData({ submitting: false })
    }
  }
})
